"""
Collector principal de SnapMirror con recolección en cascada
Consulta 1400 instancias ONTAP Select cada 5 minutos de forma escalonada
"""

import asyncio
import logging
import yaml
import csv
import time
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from ontap_client import ONTAPClient
from database import SnapMirrorDB
from mock_data import MockDataGenerator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/collector.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SnapMirrorCollector:
    """Recolector de datos SnapMirror con polling en cascada"""
    
    def __init__(self, config_path: str = 'config/config.yaml'):
        """
        Inicializa el collector
        
        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.config = self._load_config(config_path)
        self.db = None
        self.instances = []
        self.mock_generator = None
        
        # Configuración de umbrales
        self.warning_threshold = self.config['thresholds']['warning']
        self.critical_threshold = self.config['thresholds']['critical']
        
        # Configuración de cascada
        self.stagger_delay = self.config['collector']['stagger_delay_seconds']
        
        # Modo de operación
        self.mode = self.config['collector']['mode']
        
        logger.info(f"Collector inicializado en modo: {self.mode}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Carga configuración desde YAML"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_instances_from_csv(self, csv_path: str = 'config/ontap_instances.csv') -> List[Dict]:
        """
        Carga instancias desde CSV
        
        Returns:
            Lista de diccionarios con datos de instancias
        """
        instances = []
        
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Saltar líneas de comentario
                    if row['name'].startswith('#'):
                        continue
                    
                    instances.append({
                        'name': row['name'],
                        'ip_address': row['ip_address'],
                        'latitude': float(row['latitude']),
                        'longitude': float(row['longitude']),
                        'location_name': row['location_name'],
                        'username': row['username'],
                        'password': row['password']
                    })
            
            logger.info(f"Cargadas {len(instances)} instancias desde {csv_path}")
            
        except FileNotFoundError:
            logger.warning(f"Archivo {csv_path} no encontrado, usando modo mock")
        
        return instances
    
    def setup(self):
        """Configura conexiones y carga datos iniciales"""
        # Conectar a MySQL
        db_config = self.config['database']
        self.db = SnapMirrorDB(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        self.db.connect()
        
        # Cargar instancias
        if self.mode == 'mock':
            # Generar instancias simuladas
            mock_config = self.config['mock']
            self.mock_generator = MockDataGenerator(
                num_instances=mock_config['num_instances'],
                relationships_per_instance=mock_config['num_relationships_per_instance']
            )
            self.instances = self.mock_generator.generate_instances()
            logger.info(f"Modo MOCK: {len(self.instances)} instancias simuladas")
        else:
            # Cargar desde CSV
            self.instances = self._load_instances_from_csv()
            logger.info(f"Modo REAL: {len(self.instances)} instancias cargadas")
        
        # Registrar instancias en BD
        self._register_instances()
    
    def _register_instances(self):
        """Registra todas las instancias en la base de datos"""
        logger.info("Registrando instancias en base de datos...")
        
        for inst in self.instances:
            try:
                self.db.upsert_instance(
                    name=inst['name'],
                    ip=inst['ip_address'],
                    latitude=inst['latitude'],
                    longitude=inst['longitude'],
                    location=inst['location_name']
                )
            except Exception as e:
                logger.error(f"Error registrando instancia {inst['name']}: {e}")
        
        logger.info("Instancias registradas")
    
    def _collect_from_instance_mock(self, instance: Dict) -> Dict:
        """
        Recolecta datos de una instancia en modo MOCK
        
        Returns:
            Diccionario con cluster_info y relationships
        """
        return self.mock_generator.generate_mock_response(instance['name'])
    
    def _collect_from_instance_real(self, instance: Dict) -> Dict:
        """
        Recolecta datos de una instancia real via REST API
        
        Returns:
            Diccionario con cluster_info y relationships
        """
        try:
            client = ONTAPClient(
                host=instance['ip_address'],
                username=instance['username'],
                password=instance['password']
            )
            
            # Obtener info del cluster
            cluster_info = client.get_cluster_info()
            
            # Obtener relaciones SnapMirror
            relationships = client.get_snapmirror_relationships()
            
            return {
                'cluster_info': cluster_info,
                'relationships': relationships,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recolectando de {instance['name']}: {e}")
            return {
                'cluster_info': {'error': str(e)},
                'relationships': [],
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_instance_data(self, instance: Dict, data: Dict):
        """
        Procesa y almacena los datos recolectados de una instancia
        
        Args:
            instance: Diccionario con info de la instancia
            data: Datos recolectados (cluster_info, relationships)
        """
        try:
            # Obtener ID de la instancia
            db_instance = self.db.get_instance_by_name(instance['name'])
            if not db_instance:
                logger.error(f"Instancia {instance['name']} no encontrada en BD")
                return
            
            instance_id = db_instance['id']
            
            # Actualizar cluster UUID si está disponible
            cluster_uuid = data['cluster_info'].get('uuid')
            if cluster_uuid:
                self.db.upsert_instance(
                    name=instance['name'],
                    ip=instance['ip_address'],
                    latitude=instance['latitude'],
                    longitude=instance['longitude'],
                    location=instance['location_name'],
                    cluster_uuid=cluster_uuid
                )
            
            # Procesar cada relación SnapMirror
            for rel in data['relationships']:
                # Registrar relación
                rel_id = self.db.upsert_relationship(
                    instance_id=instance_id,
                    uuid=rel['uuid'],
                    source_path=rel['source_path'],
                    dest_path=rel['destination_path'],
                    policy=rel['policy'],
                    rel_type='async'
                )
                
                # Calcular nivel de alerta
                lag_seconds = rel['lag_seconds']
                healthy = rel['healthy']
                
                if not healthy:
                    alert_level = 'error'
                    error_msg = f"Relación en estado: {rel['state']}"
                elif lag_seconds >= self.critical_threshold:
                    alert_level = 'critical'
                    error_msg = f"Lag crítico: {lag_seconds // 60} minutos"
                elif lag_seconds >= self.warning_threshold:
                    alert_level = 'warning'
                    error_msg = f"Lag elevado: {lag_seconds // 60} minutos"
                else:
                    alert_level = 'ok'
                    error_msg = None
                
                # Convertir last_transfer_end_time de ISO 8601 a datetime MySQL
                last_transfer_time = rel.get('last_transfer_end_time')
                if last_transfer_time:
                    try:
                        # Convertir "2026-01-20T12:00:08+00:00" a datetime sin timezone
                        dt = datetime.fromisoformat(last_transfer_time.replace('Z', '+00:00'))
                        last_transfer_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.warning(f"Error parseando timestamp {last_transfer_time}: {e}")
                        last_transfer_time = None
                
                # Actualizar estado actual
                self.db.update_current_status(
                    relationship_id=rel_id,
                    instance_id=instance_id,
                    lag_seconds=lag_seconds,
                    state=rel['state'],
                    health=healthy,
                    transfer_state=rel['transfer_state'],
                    last_transfer_time=last_transfer_time,
                    alert_level=alert_level,
                    error_msg=error_msg
                )
                
                # Insertar en histórico
                health_status = 'healthy' if healthy else 'unhealthy'
                self.db.insert_history(
                    relationship_id=rel_id,
                    instance_id=instance_id,
                    lag_seconds=lag_seconds,
                    state=rel['state'],
                    health=health_status,
                    alert_level=alert_level
                )
            
            logger.info(f"✓ {instance['name']}: {len(data['relationships'])} relaciones procesadas")
            
        except Exception as e:
            logger.error(f"Error procesando datos de {instance['name']}: {e}")
    
    async def collect_single_instance(self, instance: Dict, index: int, total: int):
        """
        Recolecta datos de una única instancia (asíncrono)
        
        Args:
            instance: Datos de la instancia
            index: Índice de la instancia (para logging)
            total: Total de instancias
        """
        logger.info(f"[{index + 1}/{total}] Recolectando {instance['name']}...")
        
        # Recolectar datos según modo
        if self.mode == 'mock':
            data = self._collect_from_instance_mock(instance)
        else:
            # En modo real, ejecutar en executor para no bloquear
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                self._collect_from_instance_real, 
                instance
            )
        
        # Procesar y almacenar
        self._process_instance_data(instance, data)
    
    async def collect_all_staggered(self):
        """
        Recolecta datos de todas las instancias en cascada
        
        Distribuye las consultas a lo largo del intervalo para evitar picos
        """
        total_instances = len(self.instances)
        logger.info(f"\n{'='*60}")
        logger.info(f"Iniciando recolección en cascada: {total_instances} instancias")
        logger.info(f"Delay entre instancias: {self.stagger_delay}s")
        logger.info(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Procesar instancias una por una con delay
        for idx, instance in enumerate(self.instances):
            # Recolectar instancia
            await self.collect_single_instance(instance, idx, total_instances)
            
            # Delay antes de la siguiente (excepto en la última)
            if idx < total_instances - 1:
                await asyncio.sleep(self.stagger_delay)
        
        elapsed = time.time() - start_time
        
        # Mostrar estadísticas
        stats = self.db.get_statistics()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Recolección completada en {elapsed:.2f} segundos")
        logger.info(f"Estadísticas:")
        logger.info(f"  - Total instancias: {stats.get('total_instances', 0)}")
        logger.info(f"  - Total relaciones: {stats.get('total_relationships', 0)}")
        logger.info(f"  - OK: {stats.get('ok_count', 0)}")
        logger.info(f"  - WARNING: {stats.get('warning_count', 0)}")
        logger.info(f"  - CRITICAL: {stats.get('critical_count', 0)}")
        logger.info(f"  - ERROR: {stats.get('error_count', 0)}")
        logger.info(f"{'='*60}\n")
    
    async def run_continuous(self):
        """
        Ejecuta recolección continua cada X minutos
        """
        interval = self.config['collector']['interval_seconds']
        
        logger.info(f"Iniciando modo continuo (cada {interval}s)")
        
        while True:
            try:
                await self.collect_all_staggered()
                
                # Esperar hasta el siguiente ciclo
                logger.info(f"Esperando {interval}s hasta próxima recolección...")
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Deteniendo collector...")
                break
            except Exception as e:
                logger.error(f"Error en ciclo de recolección: {e}")
                await asyncio.sleep(60)  # Esperar 1 min en caso de error
    
    def cleanup(self):
        """Limpieza de recursos"""
        if self.db:
            self.db.disconnect()
        logger.info("Collector finalizado")


async def main():
    """Función principal"""
    # Crear directorio de logs si no existe
    Path('logs').mkdir(exist_ok=True)
    
    collector = SnapMirrorCollector()
    
    try:
        collector.setup()
        
        # Ejecutar una sola vez o en modo continuo
        import sys
        if '--once' in sys.argv:
            await collector.collect_all_staggered()
        else:
            await collector.run_continuous()
            
    except KeyboardInterrupt:
        logger.info("\nInterrumpido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
    finally:
        collector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
