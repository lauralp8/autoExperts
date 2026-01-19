"""
Generador de datos simulados (MOCK) para pruebas
Simula 1400 instancias ONTAP Select con relaciones SnapMirror
"""

import random
import logging
from typing import List, Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MockDataGenerator:
    """Genera datos simulados de ONTAP Select y SnapMirror"""
    
    # Coordenadas de ciudades españolas para distribución realista
    SPANISH_CITIES = [
        ("Madrid", 40.4168, -3.7038),
        ("Barcelona", 41.3851, 2.1734),
        ("Valencia", 39.4699, -0.3763),
        ("Sevilla", 37.3891, -5.9845),
        ("Zaragoza", 41.6488, -0.8891),
        ("Málaga", 36.7213, -4.4214),
        ("Murcia", 37.9922, -1.1307),
        ("Palma", 39.5696, 2.6502),
        ("Las Palmas", 28.1248, -15.4300),
        ("Bilbao", 43.2630, -2.9350),
        ("Alicante", 38.3452, -0.4810),
        ("Córdoba", 37.8882, -4.7794),
        ("Valladolid", 41.6528, -4.7245),
        ("Vigo", 42.2406, -8.7207),
        ("Gijón", 43.5322, -5.6611),
        ("Granada", 37.1773, -3.5986),
        ("Vitoria", 42.8467, -2.6716),
        ("Santander", 43.4623, -3.8099),
        ("Pamplona", 42.8125, -1.6458),
        ("Salamanca", 40.9701, -5.6635),
    ]
    
    POLICIES = ["MirrorAllSnapshots", "MirrorAndVault", "MirrorLatest", "DailyBackup"]
    STATES = ["snapmirrored", "broken-off", "uninitialized"]
    TRANSFER_STATES = ["success", "transferring", "idle", "failed"]
    
    def __init__(self, num_instances: int = 100, relationships_per_instance: int = 3):
        """
        Inicializa el generador
        
        Args:
            num_instances: Número de instancias ONTAP Select a simular
            relationships_per_instance: Número promedio de relaciones por instancia
        """
        self.num_instances = num_instances
        self.relationships_per_instance = relationships_per_instance
        random.seed(42)  # Para reproducibilidad
    
    def generate_instances(self) -> List[Dict]:
        """
        Genera instancias ONTAP Select simuladas
        
        Returns:
            Lista de diccionarios con datos de instancias
        """
        instances = []
        
        for i in range(1, self.num_instances + 1):
            # Seleccionar ciudad aleatoria
            city, lat, lon = random.choice(self.SPANISH_CITIES)
            
            # Añadir variación a las coordenadas (simular múltiples sitios por ciudad)
            lat_offset = random.uniform(-0.5, 0.5)
            lon_offset = random.uniform(-0.5, 0.5)
            
            instance = {
                'name': f'ontap-select-{city.lower()}-{i:04d}',
                'ip_address': f'10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}',
                'latitude': round(lat + lat_offset, 6),
                'longitude': round(lon + lon_offset, 6),
                'location_name': f'{city} - Sitio {i % 10 + 1}',
                'cluster_uuid': f'uuid-{i:04d}-{random.randint(1000, 9999)}',
                'username': 'admin',
                'password': 'NetApp123'  # En producción, usar vault
            }
            
            instances.append(instance)
        
        logger.info(f"Generadas {len(instances)} instancias simuladas")
        return instances
    
    def generate_snapmirror_relationships(self, simulate_lag: float = 0.3, 
                                         simulate_errors: float = 0.05) -> List[Dict]:
        """
        Genera relaciones SnapMirror simuladas con lag realista
        
        Args:
            simulate_lag: Probabilidad de que una relación tenga lag (0.0-1.0)
            simulate_errors: Probabilidad de errores (0.0-1.0)
            
        Returns:
            Lista de diccionarios con relaciones SnapMirror
        """
        relationships = []
        
        for i in range(self.relationships_per_instance):
            # Determinar estado
            has_lag = random.random() < simulate_lag
            has_error = random.random() < simulate_errors
            
            # Generar lag realista
            if has_error:
                lag_seconds = random.randint(7200, 86400)  # 2-24 horas (error grave)
                state = random.choice(["broken-off", "uninitialized"])
                healthy = False
                transfer_state = "failed"
            elif has_lag:
                # Distribución realista de lags
                lag_type = random.random()
                if lag_type < 0.5:
                    lag_seconds = random.randint(900, 3600)  # 15min - 1h (warning)
                elif lag_type < 0.8:
                    lag_seconds = random.randint(3600, 7200)  # 1-2h (critical)
                else:
                    lag_seconds = random.randint(7200, 14400)  # 2-4h (muy critical)
                
                state = "snapmirrored"
                healthy = True
                transfer_state = random.choice(["idle", "transferring"])
            else:
                lag_seconds = random.randint(0, 600)  # 0-10 minutos (OK)
                state = "snapmirrored"
                healthy = True
                transfer_state = "success"
            
            # Crear relación
            relationship = {
                'uuid': f'rel-uuid-{i}-{random.randint(10000, 99999)}',
                'source_path': f'svm{random.randint(1, 10)}:vol_source_{random.randint(1, 100)}',
                'destination_path': f'svm{random.randint(1, 10)}:vol_dest_{random.randint(1, 100)}',
                'policy': random.choice(self.POLICIES),
                'state': state,
                'healthy': healthy,
                'transfer_state': transfer_state,
                'lag_seconds': lag_seconds,
                'last_transfer_end_time': int((datetime.now() - timedelta(seconds=lag_seconds)).timestamp())
            }
            
            relationships.append(relationship)
        
        return relationships
    
    def calculate_alert_level(self, lag_seconds: int, healthy: bool, 
                             warning_threshold: int = 900, 
                             critical_threshold: int = 3600) -> Tuple[str, str]:
        """
        Calcula el nivel de alerta basado en lag y salud
        
        Args:
            lag_seconds: Lag en segundos
            healthy: Estado de salud
            warning_threshold: Umbral de warning en segundos
            critical_threshold: Umbral de critical en segundos
            
        Returns:
            Tupla (alert_level, error_message)
        """
        if not healthy:
            return ('error', 'Relación SnapMirror no saludable')
        
        if lag_seconds >= critical_threshold:
            return ('critical', f'Lag crítico: {lag_seconds // 60} minutos')
        elif lag_seconds >= warning_threshold:
            return ('warning', f'Lag elevado: {lag_seconds // 60} minutos')
        else:
            return ('ok', None)
    
    def generate_mock_response(self, instance_name: str) -> Dict:
        """
        Genera una respuesta completa simulada para una instancia
        
        Args:
            instance_name: Nombre de la instancia
            
        Returns:
            Diccionario con cluster_info y relationships
        """
        cluster_info = {
            'uuid': f'cluster-{random.randint(1000, 9999)}',
            'name': instance_name,
            'version': '9.12.1'
        }
        
        relationships = self.generate_snapmirror_relationships()
        
        return {
            'cluster_info': cluster_info,
            'relationships': relationships,
            'timestamp': datetime.now().isoformat()
        }


# Funciones de utilidad
def generate_csv_instances(num_instances: int = 100, output_file: str = None) -> str:
    """
    Genera un CSV con instancias para configuración
    
    Args:
        num_instances: Número de instancias
        output_file: Ruta del archivo de salida (opcional)
        
    Returns:
        String con contenido CSV
    """
    generator = MockDataGenerator(num_instances)
    instances = generator.generate_instances()
    
    lines = ["name,ip_address,latitude,longitude,location_name,username,password"]
    
    for inst in instances:
        line = (f"{inst['name']},{inst['ip_address']},{inst['latitude']},"
               f"{inst['longitude']},{inst['location_name']},{inst['username']},{inst['password']}")
        lines.append(line)
    
    csv_content = '\n'.join(lines)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(csv_content)
        logger.info(f"CSV generado en {output_file}")
    
    return csv_content


if __name__ == "__main__":
    # Test del generador
    logging.basicConfig(level=logging.INFO)
    
    gen = MockDataGenerator(num_instances=10)
    instances = gen.generate_instances()
    
    print(f"\n=== {len(instances)} Instancias Generadas ===")
    for inst in instances[:3]:
        print(f"{inst['name']} - {inst['location_name']} ({inst['latitude']}, {inst['longitude']})")
    
    print(f"\n=== Relaciones SnapMirror de Ejemplo ===")
    rels = gen.generate_snapmirror_relationships()
    for rel in rels:
        alert, msg = gen.calculate_alert_level(rel['lag_seconds'], rel['healthy'])
        print(f"{rel['source_path']} -> {rel['destination_path']}")
        print(f"  Lag: {rel['lag_seconds']}s, Estado: {rel['state']}, Alerta: {alert}")
