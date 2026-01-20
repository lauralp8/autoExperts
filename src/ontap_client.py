"""
Cliente REST API para NetApp ONTAP 9.12+
Solo operaciones de lectura (GET) para SnapMirror relationships
"""

import requests
import logging
from typing import Dict, List, Optional
from requests.auth import HTTPBasicAuth
import urllib3

# Deshabilitar warnings de SSL (solo para entornos de desarrollo/prueba)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ONTAPClient:
    """Cliente para interactuar con ONTAP REST API"""
    
    def __init__(self, host: str, username: str, password: str, verify_ssl: bool = False):
        """
        Inicializa el cliente ONTAP
        
        Args:
            host: IP o hostname del cluster ONTAP
            username: Usuario con permisos de lectura
            password: Contraseña
            verify_ssl: Verificar certificados SSL (False para dev)
        """
        self.host = host
        self.base_url = f"https://{host}/api"
        self.auth = HTTPBasicAuth(username, password)
        self.verify_ssl = verify_ssl
        self.timeout = 30
        
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Ejecuta un GET request al API de ONTAP
        
        Args:
            endpoint: Endpoint del API (ej: /snapmirror/relationships)
            params: Parámetros query opcionales
            
        Returns:
            Diccionario con la respuesta JSON
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(
                url,
                auth=self.auth,
                headers=self.headers,
                params=params,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando a {self.host}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión a {self.host}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error en {self.host}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en {self.host}: {e}")
            raise
    
    def get_cluster_info(self) -> Dict:
        """
        Obtiene información básica del cluster
        
        Returns:
            Diccionario con info del cluster (uuid, nombre, versión)
        """
        try:
            data = self._get("/cluster")
            return {
                'uuid': data.get('uuid'),
                'name': data.get('name'),
                'version': data.get('version', {}).get('full', 'unknown')
            }
        except Exception as e:
            logger.error(f"Error obteniendo info de cluster {self.host}: {e}")
            return {'uuid': None, 'name': None, 'version': None, 'error': str(e)}
    
    def get_snapmirror_relationships(self) -> List[Dict]:
        """
        Obtiene todas las relaciones SnapMirror del cluster
        
        Returns:
            Lista de diccionarios con información de cada relación
        """
        try:
            # Query con campos específicos para obtener lag_time
            params = {
                'fields': 'uuid,source.path,destination.path,policy.name,state,healthy,lag_time,transfer.state,transfer.end_time',
                'return_records': 'true',
                'return_timeout': 15
            }
            
            data = self._get("/snapmirror/relationships", params=params)
            
            relationships = []
            for record in data.get('records', []):
                # Parsear lag_time (viene en formato ISO 8601 duration: PT1H30M)
                lag_time_str = record.get('lag_time', 'PT0S')
                lag_seconds = self._parse_iso_duration(lag_time_str) if lag_time_str else 0
                
                # Extraer datos con manejo robusto de campos opcionales
                source_info = record.get('source', {})
                dest_info = record.get('destination', {})
                policy_info = record.get('policy', {})
                transfer_info = record.get('transfer', {})
                
                rel_info = {
                    'uuid': record.get('uuid'),
                    'source_path': source_info.get('path') if source_info else None,
                    'destination_path': dest_info.get('path') if dest_info else None,
                    'policy': policy_info.get('name') if policy_info else None,
                    'state': record.get('state'),
                    'healthy': record.get('healthy'),
                    'transfer_state': transfer_info.get('state') if transfer_info else None,
                    'lag_seconds': lag_seconds,
                    'last_transfer_end_time': transfer_info.get('end_time') if transfer_info else None
                }
                relationships.append(rel_info)
            
            logger.info(f"Obtenidas {len(relationships)} relaciones de {self.host}")
            return relationships
            
        except Exception as e:
            logger.error(f"Error obteniendo relaciones SnapMirror de {self.host}: {e}")
            return []
    
    @staticmethod
    def _parse_iso_duration(duration_str: str) -> int:
        """
        Convierte ISO 8601 duration a segundos
        Ejemplo: PT1H30M45S -> 5445 segundos
        
        Args:
            duration_str: String en formato ISO 8601 (PT...)
            
        Returns:
            Segundos totales
        """
        if not duration_str or duration_str == 'PT0S':
            return 0
        
        try:
            # Remover 'PT' del inicio
            duration_str = duration_str.replace('PT', '')
            
            hours = 0
            minutes = 0
            seconds = 0
            
            # Parsear horas
            if 'H' in duration_str:
                parts = duration_str.split('H')
                hours = int(parts[0])
                duration_str = parts[1] if len(parts) > 1 else ''
            
            # Parsear minutos
            if 'M' in duration_str:
                parts = duration_str.split('M')
                minutes = int(parts[0]) if parts[0] else 0
                duration_str = parts[1] if len(parts) > 1 else ''
            
            # Parsear segundos
            if 'S' in duration_str:
                seconds = int(duration_str.replace('S', ''))
            
            total_seconds = (hours * 3600) + (minutes * 60) + seconds
            return total_seconds
            
        except Exception as e:
            logger.warning(f"Error parseando duration {duration_str}: {e}")
            return 0
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión al cluster ONTAP
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            info = self.get_cluster_info()
            if info.get('uuid'):
                logger.info(f"Conexión exitosa a {self.host} - Cluster: {info.get('name')}")
                return True
            return False
        except Exception:
            return False
