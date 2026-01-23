"""
Main SnapMirror Collector with cascade collection
Queries 1400 ONTAP Select instances every 5 minutes in staggered fashion
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

# Configure logging
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
    """SnapMirror data collector with cascade polling"""
    
    def __init__(self, config_path: str = 'config/config.yaml'):
        """
        Initialize the collector
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.db = None
        self.instances = []
        self.mock_generator = None
        
        # Threshold configuration
        self.warning_threshold = self.config['thresholds']['warning']
        self.critical_threshold = self.config['thresholds']['critical']
        
        # Cascade configuration
        self.stagger_delay = self.config['collector']['stagger_delay_seconds']
        
        # Operation mode
        self.mode = self.config['collector']['mode']
        
        logger.info(f"Collector initialized in mode: {self.mode}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_instances_from_csv(self, csv_path: str = 'config/ontap_instances.csv') -> List[Dict]:
        """
        Load instances from CSV
        
        Returns:
            List of dictionaries with instance data
        """
        instances = []
        
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip comment lines
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
            
            logger.info(f"Loaded {len(instances)} instances from {csv_path}")
            
        except FileNotFoundError:
            logger.warning(f"File {csv_path} not found, using mock mode")
        
        return instances
    
    def setup(self):
        """Configure connections and load initial data"""
        # Connect to MySQL
        db_config = self.config['database']
        self.db = SnapMirrorDB(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        self.db.connect()
        
        # Load instances
        if self.mode == 'mock':
            # Generate mock instances
            mock_config = self.config['mock']
            self.mock_generator = MockDataGenerator(
                num_instances=mock_config['num_instances'],
                relationships_per_instance=mock_config['num_relationships_per_instance']
            )
            self.instances = self.mock_generator.generate_instances()
            logger.info(f"MOCK mode: {len(self.instances)} simulated instances")
        else:
            # Load from CSV
            self.instances = self._load_instances_from_csv()
            logger.info(f"REAL mode: {len(self.instances)} instances loaded")
        
        # Register instances in database
        self._register_instances()
    
    def _register_instances(self):
        """Register all instances in the database"""
        logger.info("Registering instances in database...")
        
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
                logger.error(f"Error registering instance {inst['name']}: {e}")
        
        logger.info("Instances registered")
    
    def _collect_from_instance_mock(self, instance: Dict) -> Dict:
        """
        Collect data from an instance in MOCK mode
        
        Returns:
            Dictionary with cluster_info and relationships
        """
        return self.mock_generator.generate_mock_response(instance['name'])
    
    def _collect_from_instance_real(self, instance: Dict) -> Dict:
        """
        Collect data from a real instance via REST API
        
        Returns:
            Dictionary with cluster_info and relationships
        """
        try:
            client = ONTAPClient(
                host=instance['ip_address'],
                username=instance['username'],
                password=instance['password']
            )
            
            # Get cluster info
            cluster_info = client.get_cluster_info()
            
            # Get SnapMirror relationships
            relationships = client.get_snapmirror_relationships()
            
            return {
                'cluster_info': cluster_info,
                'relationships': relationships,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error collecting from {instance['name']}: {e}")
            return {
                'cluster_info': {'error': str(e)},
                'relationships': [],
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_instance_data(self, instance: Dict, data: Dict):
        """
        Process and store collected data from an instance
        
        Args:
            instance: Dictionary with instance info
            data: Collected data (cluster_info, relationships)
        """
        try:
            # Get instance ID
            db_instance = self.db.get_instance_by_name(instance['name'])
            if not db_instance:
                logger.error(f"Instance {instance['name']} not found in database")
                return
            
            instance_id = db_instance['id']
            
            # Update cluster UUID if available
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
            
            # Process each SnapMirror relationship
            for rel in data['relationships']:
                # Register relationship
                rel_id = self.db.upsert_relationship(
                    instance_id=instance_id,
                    uuid=rel['uuid'],
                    source_path=rel['source_path'],
                    dest_path=rel['destination_path'],
                    policy=rel['policy'],
                    rel_type='async'
                )
                
                # Calculate alert level
                lag_seconds = rel['lag_seconds']
                healthy = rel['healthy']
                
                if not healthy:
                    alert_level = 'error'
                    error_msg = f"Relationship in state: {rel['state']}"
                elif lag_seconds >= self.critical_threshold:
                    alert_level = 'critical'
                    error_msg = f"Critical lag: {lag_seconds // 60} minutes"
                elif lag_seconds >= self.warning_threshold:
                    alert_level = 'warning'
                    error_msg = f"High lag: {lag_seconds // 60} minutes"
                else:
                    alert_level = 'ok'
                    error_msg = None
                
                # Convert last_transfer_end_time from ISO 8601 to Unix timestamp (BIGINT)
                last_transfer_time = rel.get('last_transfer_end_time')
                if last_transfer_time:
                    try:
                        # Convert "2026-01-20T12:00:08+00:00" to Unix timestamp
                        dt = datetime.fromisoformat(last_transfer_time.replace('Z', '+00:00'))
                        last_transfer_time = int(dt.timestamp())
                    except Exception as e:
                        logger.warning(f"Error parsing timestamp {last_transfer_time}: {e}")
                        last_transfer_time = None
                
                # Update current status
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
                
                # Insert into history
                health_status = 'healthy' if healthy else 'unhealthy'
                self.db.insert_history(
                    relationship_id=rel_id,
                    instance_id=instance_id,
                    lag_seconds=lag_seconds,
                    state=rel['state'],
                    health=health_status,
                    alert_level=alert_level
                )
            
            logger.info(f"✓ {instance['name']}: {len(data['relationships'])} relationships processed")
            
        except Exception as e:
            logger.error(f"Error processing data from {instance['name']}: {e}")
    
    async def collect_single_instance(self, instance: Dict, index: int, total: int):
        """
        Collect data from a single instance (asynchronous)
        
        Args:
            instance: Instance data
            index: Instance index (for logging)
            total: Total number of instances
        """
        logger.info(f"[{index + 1}/{total}] Collecting {instance['name']}...")
        
        # Collect data according to mode
        if self.mode == 'mock':
            data = self._collect_from_instance_mock(instance)
        else:
            # In real mode, execute in executor to avoid blocking
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                self._collect_from_instance_real, 
                instance
            )
        
        # Process and store
        self._process_instance_data(instance, data)
    
    async def collect_all_staggered(self):
        """
        Collect data from all instances in cascade
        
        Distributes queries over the interval to avoid peaks
        """
        total_instances = len(self.instances)
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting cascade collection: {total_instances} instances")
        logger.info(f"Delay between instances: {self.stagger_delay}s")
        logger.info(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Process instances one by one with delay
        for idx, instance in enumerate(self.instances):
            # Collect instance
            await self.collect_single_instance(instance, idx, total_instances)
            
            # Delay before next (except for last one)
            if idx < total_instances - 1:
                await asyncio.sleep(self.stagger_delay)
        
        elapsed = time.time() - start_time
        
        # Show statistics
        stats = self.db.get_statistics()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Collection completed in {elapsed:.2f} seconds")
        logger.info(f"Statistics:")
        logger.info(f"  - Total instances: {stats.get('total_instances', 0)}")
        logger.info(f"  - Total relationships: {stats.get('total_relationships', 0)}")
        logger.info(f"  - OK: {stats.get('ok_count', 0)}")
        logger.info(f"  - WARNING: {stats.get('warning_count', 0)}")
        logger.info(f"  - CRITICAL: {stats.get('critical_count', 0)}")
        logger.info(f"  - ERROR: {stats.get('error_count', 0)}")
        logger.info(f"{'='*60}\n")
    
    async def run_continuous(self):
        """
        Execute continuous collection every X minutes
        """
        interval = self.config['collector']['interval_seconds']
        
        logger.info(f"Starting continuous mode (every {interval}s)")
        
        while True:
            try:
                await self.collect_all_staggered()
                
                # Wait until next cycle
                logger.info(f"Waiting {interval}s until next collection...")
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Stopping collector...")
                break
            except Exception as e:
                logger.error(f"Error in collection cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 min in case of error
    
    def cleanup(self):
        """Resource cleanup"""
        if self.db:
            self.db.disconnect()
        logger.info("Collector finished")


async def main():
    """Main function"""
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    collector = SnapMirrorCollector()
    
    try:
        collector.setup()
        
        # Execute once or in continuous mode
        import sys
        if '--once' in sys.argv:
            await collector.collect_all_staggered()
        else:
            await collector.run_continuous()
            
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        collector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
