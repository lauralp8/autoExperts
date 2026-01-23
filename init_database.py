"""
Script to initialize MySQL database
Creates necessary tables and views
"""

import pymysql
import argparse
import yaml
from pathlib import Path


def load_config(config_path: str = 'config/config.yaml'):
    """Load YAML configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def init_database(host: str, port: int, user: str, password: str, database: str, schema_file: str):
    """
    Initialize database by executing the schema SQL
    
    Args:
        host, port, user, password: MySQL credentials
        database: Database name
        schema_file: Path to schema.sql file
    """
    print(f"Connecting to MySQL on {host}:{port}...")
    
    # Connect without specifying database (to be able to create it)
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Read SQL schema
            with open(schema_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Execute each statement
            statements = sql_script.split(';')
            
            for i, statement in enumerate(statements):
                statement = statement.strip()
                if statement:
                    print(f"Executing statement {i + 1}/{len(statements)}...")
                    cursor.execute(statement)
            
            connection.commit()
            print("\n✓ Database initialized successfully")
            
            # Verify created tables
            cursor.execute(f"USE {database}")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"\nTables created ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
            
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description='Initialize MySQL database for SnapMirror Monitor'
    )
    
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--schema',
        default='config/mysql_schema.sql',
        help='SQL schema file (default: config/mysql_schema.sql)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recreation (DROP DATABASE if exists)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    db_config = config['database']
    
    print("="*60)
    print("SnapMirror Monitor - Inicialización de Base de Datos")
    print("="*60)
    print(f"Host: {db_config['host']}")
    print(f"Database: {db_config['database']}")
    print(f"Schema: {args.schema}")
    print("="*60)
    
    if args.force:
        confirm = input("\n⚠️  WARNING: Existing database will be deleted. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
    
    try:
        init_database(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            schema_file=args.schema
        )
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
