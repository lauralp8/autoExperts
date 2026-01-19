"""
Módulo de base de datos MySQL para SnapMirror Monitoring
"""

import pymysql
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SnapMirrorDB:
    """Gestión de base de datos MySQL para monitorización SnapMirror"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        Inicializa la conexión a MySQL
        
        Args:
            host: Host de MySQL
            port: Puerto (generalmente 3306)
            user: Usuario de MySQL
            password: Contraseña
            database: Nombre de la base de datos
        """
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        self.connection = None
    
    def connect(self):
        """Establece conexión con MySQL"""
        try:
            self.connection = pymysql.connect(**self.config)
            logger.info("Conexión exitosa a MySQL")
        except Exception as e:
            logger.error(f"Error conectando a MySQL: {e}")
            raise
    
    def disconnect(self):
        """Cierra la conexión"""
        if self.connection:
            self.connection.close()
            logger.info("Conexión a MySQL cerrada")
    
    def _execute(self, query: str, params: tuple = None, fetch: bool = False):
        """
        Ejecuta una query SQL
        
        Args:
            query: Query SQL
            params: Parámetros para la query
            fetch: Si True, retorna los resultados
            
        Returns:
            Resultados si fetch=True, sino ID del último insert
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                
                if fetch:
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Error ejecutando query: {e}")
            self.connection.rollback()
            raise
    
    def upsert_instance(self, name: str, ip: str, latitude: float, longitude: float, 
                       location: str, cluster_uuid: Optional[str] = None) -> int:
        """
        Inserta o actualiza una instancia ONTAP
        
        Returns:
            ID de la instancia
        """
        query = """
        INSERT INTO ontap_instances (name, ip_address, latitude, longitude, location_name, cluster_uuid)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            ip_address = VALUES(ip_address),
            cluster_uuid = VALUES(cluster_uuid),
            updated_at = CURRENT_TIMESTAMP
        """
        
        instance_id = self._execute(query, (name, ip, latitude, longitude, location, cluster_uuid))
        
        # Si fue UPDATE, obtener el ID
        if instance_id == 0:
            query_id = "SELECT id FROM ontap_instances WHERE name = %s"
            result = self._execute(query_id, (name,), fetch=True)
            instance_id = result[0]['id'] if result else None
        
        return instance_id
    
    def upsert_relationship(self, instance_id: int, uuid: str, source_path: str,
                           dest_path: str, policy: str, rel_type: str = 'async') -> int:
        """
        Inserta o actualiza una relación SnapMirror
        
        Returns:
            ID de la relación
        """
        query = """
        INSERT INTO snapmirror_relationships 
            (instance_id, relationship_uuid, source_path, destination_path, policy, relationship_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            source_path = VALUES(source_path),
            destination_path = VALUES(destination_path),
            policy = VALUES(policy)
        """
        
        rel_id = self._execute(query, (instance_id, uuid, source_path, dest_path, policy, rel_type))
        
        # Si fue UPDATE, obtener el ID
        if rel_id == 0:
            query_id = "SELECT id FROM snapmirror_relationships WHERE instance_id = %s AND relationship_uuid = %s"
            result = self._execute(query_id, (instance_id, uuid), fetch=True)
            rel_id = result[0]['id'] if result else None
        
        return rel_id
    
    def update_current_status(self, relationship_id: int, instance_id: int, 
                             lag_seconds: int, state: str, health: bool,
                             transfer_state: str, last_transfer_time: Optional[int],
                             alert_level: str, error_msg: Optional[str] = None):
        """
        Actualiza el estado actual de una relación SnapMirror
        
        Args:
            relationship_id: ID de la relación
            instance_id: ID de la instancia
            lag_seconds: Lag en segundos
            state: Estado de la relación
            health: Estado de salud (True/False)
            transfer_state: Estado de transferencia
            last_transfer_time: Timestamp de última transferencia
            alert_level: ok, warning, critical, error
            error_msg: Mensaje de error opcional
        """
        health_status = 'healthy' if health else 'unhealthy'
        
        query = """
        INSERT INTO snapmirror_status_current 
            (relationship_id, instance_id, lag_seconds, state, health_status, 
             transfer_state, last_transfer_end_timestamp, alert_level, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            lag_seconds = VALUES(lag_seconds),
            state = VALUES(state),
            health_status = VALUES(health_status),
            transfer_state = VALUES(transfer_state),
            last_transfer_end_timestamp = VALUES(last_transfer_end_timestamp),
            alert_level = VALUES(alert_level),
            error_message = VALUES(error_message),
            collected_at = CURRENT_TIMESTAMP
        """
        
        self._execute(query, (relationship_id, instance_id, lag_seconds, state, 
                             health_status, transfer_state, last_transfer_time, 
                             alert_level, error_msg))
    
    def insert_history(self, relationship_id: int, instance_id: int,
                      lag_seconds: int, state: str, health: str, alert_level: str):
        """
        Inserta un registro en el histórico
        """
        query = """
        INSERT INTO snapmirror_status_history 
            (relationship_id, instance_id, lag_seconds, state, health_status, alert_level)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        self._execute(query, (relationship_id, instance_id, lag_seconds, state, health, alert_level))
    
    def get_instance_by_name(self, name: str) -> Optional[Dict]:
        """
        Obtiene una instancia por nombre
        
        Returns:
            Diccionario con datos de la instancia o None
        """
        query = "SELECT * FROM ontap_instances WHERE name = %s"
        result = self._execute(query, (name,), fetch=True)
        return result[0] if result else None
    
    def get_all_instances(self) -> List[Dict]:
        """
        Obtiene todas las instancias activas
        
        Returns:
            Lista de instancias
        """
        query = "SELECT * FROM ontap_instances WHERE is_active = TRUE ORDER BY name"
        return self._execute(query, fetch=True)
    
    def get_map_view(self) -> List[Dict]:
        """
        Obtiene datos para el mapa de Grafana
        
        Returns:
            Lista con datos agregados por instancia
        """
        query = "SELECT * FROM v_snapmirror_map ORDER BY overall_status DESC, instance_name"
        return self._execute(query, fetch=True)
    
    def get_detail_view(self, instance_name: Optional[str] = None) -> List[Dict]:
        """
        Obtiene vista detallada de relaciones
        
        Args:
            instance_name: Filtrar por nombre de instancia (opcional)
            
        Returns:
            Lista con detalle de relaciones
        """
        if instance_name:
            query = "SELECT * FROM v_snapmirror_detail WHERE instance_name = %s ORDER BY alert_level DESC"
            return self._execute(query, (instance_name,), fetch=True)
        else:
            query = "SELECT * FROM v_snapmirror_detail ORDER BY alert_level DESC, instance_name"
            return self._execute(query, fetch=True)
    
    def get_statistics(self) -> Dict:
        """
        Obtiene estadísticas generales
        
        Returns:
            Diccionario con contadores
        """
        query = """
        SELECT 
            COUNT(DISTINCT oi.id) as total_instances,
            COUNT(DISTINCT sr.id) as total_relationships,
            SUM(CASE WHEN ssc.alert_level = 'ok' THEN 1 ELSE 0 END) as ok_count,
            SUM(CASE WHEN ssc.alert_level = 'warning' THEN 1 ELSE 0 END) as warning_count,
            SUM(CASE WHEN ssc.alert_level = 'critical' THEN 1 ELSE 0 END) as critical_count,
            SUM(CASE WHEN ssc.alert_level = 'error' THEN 1 ELSE 0 END) as error_count,
            MAX(ssc.collected_at) as last_collection
        FROM ontap_instances oi
        LEFT JOIN snapmirror_relationships sr ON oi.id = sr.instance_id
        LEFT JOIN snapmirror_status_current ssc ON sr.id = ssc.relationship_id
        WHERE oi.is_active = TRUE
        """
        
        result = self._execute(query, fetch=True)
        return result[0] if result else {}
