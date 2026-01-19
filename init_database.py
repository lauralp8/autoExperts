"""
Script para inicializar la base de datos MySQL
Crea las tablas y vistas necesarias
"""

import pymysql
import argparse
import yaml
from pathlib import Path


def load_config(config_path: str = 'config/config.yaml'):
    """Carga configuración YAML"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def init_database(host: str, port: int, user: str, password: str, database: str, schema_file: str):
    """
    Inicializa la base de datos ejecutando el schema SQL
    
    Args:
        host, port, user, password: Credenciales MySQL
        database: Nombre de la base de datos
        schema_file: Ruta al archivo schema.sql
    """
    print(f"Conectando a MySQL en {host}:{port}...")
    
    # Conectar sin especificar database (para poder crearlo)
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Leer schema SQL
            with open(schema_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Ejecutar cada statement
            statements = sql_script.split(';')
            
            for i, statement in enumerate(statements):
                statement = statement.strip()
                if statement:
                    print(f"Ejecutando statement {i + 1}/{len(statements)}...")
                    cursor.execute(statement)
            
            connection.commit()
            print("\n✓ Base de datos inicializada correctamente")
            
            # Verificar tablas creadas
            cursor.execute(f"USE {database}")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"\nTablas creadas ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
            
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description='Inicializa la base de datos MySQL para SnapMirror Monitor'
    )
    
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Archivo de configuración (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--schema',
        default='config/mysql_schema.sql',
        help='Archivo schema SQL (default: config/mysql_schema.sql)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Forzar recreación (DROP DATABASE si existe)'
    )
    
    args = parser.parse_args()
    
    # Cargar configuración
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
        confirm = input("\n⚠️  ADVERTENCIA: Se eliminará la base de datos existente. ¿Continuar? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelado.")
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
