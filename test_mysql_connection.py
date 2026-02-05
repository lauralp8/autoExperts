#!/usr/bin/env python3
"""
Script rápido para probar la conexión a MySQL
Útil para diagnosticar problemas de configuración del datasource de Grafana
"""

import sys
import yaml
from pathlib import Path

def test_connection():
    """Probar conexión a MySQL con las credenciales de config.yaml"""
    
    print("="*60)
    print("  Test de Conexión MySQL para Grafana")
    print("="*60)
    
    # Cargar configuración
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        db_config = config['database']
    except Exception as e:
        print(f"\n❌ Error leyendo config/config.yaml: {e}")
        return False
    
    print(f"\nIntentando conectar con:")
    print(f"  Host:     {db_config.get('host', 'N/A')}:{db_config.get('port', 'N/A')}")
    print(f"  Database: {db_config.get('database', 'N/A')}")
    print(f"  User:     {db_config.get('user', 'N/A')}")
    print(f"  Password: {'*' * len(db_config.get('password', ''))}")
    
    # Verificar pymysql
    try:
        import pymysql
    except ImportError:
        print("\n❌ PyMySQL no instalado")
        print("   Ejecuta: pip3 install pymysql")
        return False
    
    # Probar conexión
    hosts_to_try = [
        db_config.get('host', 'localhost'),
        '127.0.0.1' if db_config.get('host') == 'localhost' else 'localhost'
    ]
    
    for host in hosts_to_try:
        print(f"\n🔄 Probando con host: {host}...")
        
        try:
            conn = pymysql.connect(
                host=host,
                port=db_config.get('port', 3306),
                user=db_config.get('user', 'snapmirror_user'),
                password=db_config.get('password', ''),
                database=db_config.get('database', 'snapmirror_monitoring'),
                charset='utf8mb4',
                connect_timeout=5
            )
            
            print(f"✅ CONEXIÓN EXITOSA con {host}!")
            
            # Probar query
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"   MySQL Version: {version}")
            
            # Verificar tablas
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"   Tablas encontradas: {len(tables)}")
            
            if len(tables) > 0:
                print(f"   • {', '.join(tables[:5])}")
                if len(tables) > 5:
                    print(f"   • ... y {len(tables) - 5} más")
            
            conn.close()
            
            print(f"\n{'='*60}")
            print(f"✅ CONFIGURACIÓN CORRECTA PARA GRAFANA:")
            print(f"{'='*60}")
            print(f"  Host: {host}:{db_config.get('port', 3306)}")
            print(f"  Database: {db_config.get('database', 'snapmirror_monitoring')}")
            print(f"  User: {db_config.get('user', 'snapmirror_user')}")
            print(f"  Password: {db_config.get('password', 'SnapMirror123!')}")
            print(f"  TLS/SSL: NO (dejar sin marcar)")
            print(f"{'='*60}\n")
            
            return True
            
        except pymysql.err.OperationalError as e:
            error_code = e.args[0]
            error_msg = e.args[1]
            
            print(f"❌ Error conectando con {host}: {error_msg}")
            
            if error_code == 1045:  # Access denied
                print("\n🔧 Solución: Credenciales incorrectas")
                print("   Verifica usuario y password en config/config.yaml")
                print("\n   O recrea el usuario:")
                print("   mysql -u root -p")
                print(f"   CREATE USER '{db_config.get('user')}'@'localhost' IDENTIFIED BY '{db_config.get('password')}';")
                print(f"   GRANT ALL PRIVILEGES ON {db_config.get('database')}.* TO '{db_config.get('user')}'@'localhost';")
                print("   FLUSH PRIVILEGES;")
                
            elif error_code == 1049:  # Unknown database
                print(f"\n🔧 Solución: Base de datos '{db_config.get('database')}' no existe")
                print("   Ejecuta:")
                print(f"   mysql -u root -p -e \"CREATE DATABASE {db_config.get('database')};\"")
                print(f"   mysql -u {db_config.get('user')} -p{db_config.get('password')} {db_config.get('database')} < config/mysql_schema.sql")
                
            elif error_code == 2003:  # Can't connect
                print(f"\n🔧 Solución: MySQL no está corriendo o no acepta conexiones en {host}")
                print("   Verifica:")
                print("   sudo systemctl status mysqld")
                print("   sudo systemctl start mysqld")
                
        except Exception as e:
            print(f"❌ Error inesperado con {host}: {e}")
    
    print("\n" + "="*60)
    print("❌ NO SE PUDO CONECTAR A MYSQL")
    print("="*60)
    print("\nPasos sugeridos:")
    print("1. Verifica que MySQL esté corriendo:")
    print("   sudo systemctl status mysqld")
    print("\n2. Verifica que la base de datos existe:")
    print("   mysql -u root -p -e 'SHOW DATABASES;'")
    print("\n3. Verifica que el usuario existe:")
    print("   mysql -u root -p -e \"SELECT User, Host FROM mysql.user WHERE User='snapmirror_user';\"")
    print("\n4. Ejecuta el script de verificación completa:")
    print("   python3 check_setup.py")
    print()
    
    return False


if __name__ == "__main__":
    # Cambiar al directorio del proyecto
    if not Path('config/config.yaml').exists():
        print("❌ Error: Ejecuta este script desde el directorio raíz del proyecto")
        print("   (donde está config/config.yaml)")
        sys.exit(1)
    
    success = test_connection()
    sys.exit(0 if success else 1)
