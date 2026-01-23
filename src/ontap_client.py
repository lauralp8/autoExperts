"""
REST API client for NetApp ONTAP 9.12+
Read-only operations (GET) for SnapMirror relationships
"""

import requests
import logging
from typing import Dict, List, Optional
from requests.auth import HTTPBasicAuth
import urllib3

# Disable SSL warnings (only for development/test environments)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ONTAPClient:
    """Client to interact with ONTAP REST API"""
    
    def __init__(self, host: str, username: str, password: str, verify_ssl: bool = False):
        """
        Initialize the ONTAP client
        
        Args:
            host: IP or hostname of the ONTAP cluster
            username: User with read permissions
            password: Password
            verify_ssl: Verify SSL certificates (False for dev)
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
        Execute a GET request to the ONTAP API
        
        Args:
            endpoint: API endpoint (e.g.: /snapmirror/relationships)
            params: Optional query parameters
            
        Returns:
            Dictionary with JSON response
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
            logger.error(f"Timeout connecting to {self.host}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {self.host}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error on {self.host}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error on {self.host}: {e}")
            raise
    
    def get_cluster_info(self) -> Dict:
        """
        Get basic cluster information
        
        Returns:
            Dictionary with cluster info (uuid, name, version)
        """
        try:
            data = self._get("/cluster")
            return {
                'uuid': data.get('uuid'),
                'name': data.get('name'),
                'version': data.get('version', {}).get('full', 'unknown')
            }
        except Exception as e:
            logger.error(f"Error getting cluster info from {self.host}: {e}")
            return {'uuid': None, 'name': None, 'version': None, 'error': str(e)}
    
    def get_snapmirror_relationships(self) -> List[Dict]:
        """
        Get all SnapMirror relationships from the cluster
        
        Returns:
            List of dictionaries with information for each relationship
        """
        try:
            # Query with specific fields to get lag_time
            params = {
                'fields': 'uuid,source.path,destination.path,policy.name,state,healthy,lag_time,transfer.state,transfer.end_time',
                'return_records': 'true',
                'return_timeout': 15
            }
            
            data = self._get("/snapmirror/relationships", params=params)
            
            relationships = []
            for record in data.get('records', []):
                # Parse lag_time (comes in ISO 8601 duration format: PT1H30M)
                lag_time_str = record.get('lag_time', 'PT0S')
                lag_seconds = self._parse_iso_duration(lag_time_str) if lag_time_str else 0
                
                # Extract data with robust handling of optional fields
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
            
            logger.info(f"Obtained {len(relationships)} relationships from {self.host}")
            return relationships
            
        except Exception as e:
            logger.error(f"Error getting SnapMirror relationships from {self.host}: {e}")
            return []
    
    @staticmethod
    def _parse_iso_duration(duration_str: str) -> int:
        """
        Convert ISO 8601 duration to seconds
        Example: PT1H30M45S -> 5445 seconds
        
        Args:
            duration_str: String in ISO 8601 format (PT...)
            
        Returns:
            Total seconds
        """
        if not duration_str or duration_str == 'PT0S':
            return 0
        
        try:
            # Remove 'PT' from the beginning
            duration_str = duration_str.replace('PT', '')
            
            hours = 0
            minutes = 0
            seconds = 0
            
            # Parse hours
            if 'H' in duration_str:
                parts = duration_str.split('H')
                hours = int(parts[0])
                duration_str = parts[1] if len(parts) > 1 else ''
            
            # Parse minutes
            if 'M' in duration_str:
                parts = duration_str.split('M')
                minutes = int(parts[0]) if parts[0] else 0
                duration_str = parts[1] if len(parts) > 1 else ''
            
            # Parse seconds
            if 'S' in duration_str:
                seconds = int(duration_str.replace('S', ''))
            
            total_seconds = (hours * 3600) + (minutes * 60) + seconds
            return total_seconds
            
        except Exception as e:
            logger.warning(f"Error parsing duration {duration_str}: {e}")
            return 0
    
    def test_connection(self) -> bool:
        """
        Test the connection to the ONTAP cluster
        
        Returns:
            True if connection is successful
        """
        try:
            info = self.get_cluster_info()
            if info.get('uuid'):
                logger.info(f"Successful connection to {self.host} - Cluster: {info.get('name')}")
                return True
            return False
        except Exception:
            return False
