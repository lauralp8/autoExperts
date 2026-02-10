"""
MySQL database module for SnapMirror Monitoring
"""

import pymysql
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SnapMirrorDB:
    """MySQL database management for SnapMirror monitoring"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        Initialize MySQL connection
        
        Args:
            host: MySQL host
            port: Port (typically 3306)
            user: MySQL user
            password: Password
            database: Database name
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
        """Establish connection to MySQL"""
        try:
            self.connection = pymysql.connect(**self.config)
            logger.info("Successful connection to MySQL")
        except Exception as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise
    
    def disconnect(self):
        """Close the connection"""
        if self.connection:
            self.connection.close()
            logger.info("MySQL connection closed")
    
    def _execute(self, query: str, params: tuple = None, fetch: bool = False):
        """
        Execute an SQL query
        
        Args:
            query: SQL query
            params: Query parameters
            fetch: If True, return the results
            
        Returns:
            Results if fetch=True, otherwise last insert ID
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
            logger.error(f"Error executing query: {e}")
            self.connection.rollback()
            raise
    
    def upsert_instance(self, name: str, ip: str, latitude: float, longitude: float, 
                       location: str, cluster_uuid: Optional[str] = None) -> int:
        """
        Insert or update an ONTAP instance
        
        Returns:
            Instance ID
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
        
        # If it was an UPDATE, get the ID
        if instance_id == 0:
            query_id = "SELECT id FROM ontap_instances WHERE name = %s"
            result = self._execute(query_id, (name,), fetch=True)
            instance_id = result[0]['id'] if result else None
        
        return instance_id
    
    def upsert_relationship(self, instance_id: int, uuid: str, source_path: str,
                           dest_path: str, policy: str, rel_type: str = 'async') -> int:
        """
        Insert or update a SnapMirror relationship
        
        Returns:
            Relationship ID
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
        
        # If it was an UPDATE, get the ID
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
        Update the current status of a SnapMirror relationship
        
        Args:
            relationship_id: Relationship ID
            instance_id: Instance ID
            lag_seconds: Lag in seconds
            state: Relationship state
            health: Health status (True/False)
            transfer_state: Transfer state
            last_transfer_time: Last transfer timestamp
            alert_level: ok, warning, critical, error
            error_msg: Optional error message
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
        Insert a record in the history
        """
        query = """
        INSERT INTO snapmirror_status_history 
            (relationship_id, instance_id, lag_seconds, state, health_status, alert_level)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        self._execute(query, (relationship_id, instance_id, lag_seconds, state, health, alert_level))
    
    def get_instance_by_name(self, name: str) -> Optional[Dict]:
        """
        Get an instance by name
        
        Returns:
            Dictionary with instance data or None
        """
        query = "SELECT * FROM ontap_instances WHERE name = %s"
        result = self._execute(query, (name,), fetch=True)
        return result[0] if result else None
    
    def get_all_instances(self) -> List[Dict]:
        """
        Get all active instances
        
        Returns:
            List of instances
        """
        query = "SELECT * FROM ontap_instances WHERE is_active = TRUE ORDER BY name"
        return self._execute(query, fetch=True)
    
    def get_map_view(self) -> List[Dict]:
        """
        Get data for the Grafana map
        
        Returns:
            List with aggregated data per instance
        """
        query = "SELECT * FROM v_snapmirror_map ORDER BY overall_status DESC, instance_name"
        return self._execute(query, fetch=True)
    
    def get_detail_view(self, instance_name: Optional[str] = None) -> List[Dict]:
        """
        Get detailed view of relationships
        
        Args:
            instance_name: Filter by instance name (optional)
            
        Returns:
            List with relationship details
        """
        if instance_name:
            query = "SELECT * FROM v_snapmirror_detail WHERE instance_name = %s ORDER BY alert_level DESC"
            return self._execute(query, (instance_name,), fetch=True)
        else:
            query = "SELECT * FROM v_snapmirror_detail ORDER BY alert_level DESC, instance_name"
            return self._execute(query, fetch=True)
    
    def get_statistics(self) -> Dict:
        """
        Get general statistics
        
        Returns:
            Dictionary with counters
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
    
    def cleanup_old_history(self, days: int = 30) -> int:
        """
        Delete history records older than the specified number of days
        
        Args:
            days: Number of days to keep (default 30)
            
        Returns:
            Number of deleted records
        """
        query = """
        DELETE FROM snapmirror_status_history 
        WHERE collected_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        
        # First count how many will be deleted
        count_query = """
        SELECT COUNT(*) as count FROM snapmirror_status_history 
        WHERE collected_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        result = self._execute(count_query, (days,), fetch=True)
        count = result[0]['count'] if result else 0
        
        if count > 0:
            self._execute(query, (days,))
            logger.info(f"Deleted {count} history records older than {days} days")
        
        return count
    
    def get_history_stats(self) -> Dict:
        """
        Get statistics about the history table
        
        Returns:
            Dictionary with history statistics
        """
        query = """
        SELECT 
            COUNT(*) as total_records,
            MIN(collected_at) as oldest_record,
            MAX(collected_at) as newest_record,
            COUNT(*) / GREATEST(DATEDIFF(MAX(collected_at), MIN(collected_at)), 1) as avg_records_per_day
        FROM snapmirror_status_history
        """
        
        result = self._execute(query, fetch=True)
        return result[0] if result else {}
