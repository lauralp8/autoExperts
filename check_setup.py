#!/usr/bin/env python3
"""
Script de verificación de configuración
Comprueba que todos los componentes estén correctamente configurados
"""

import sys
import os
from pathlib import Path
import yaml

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{RESET}\n")


def check_mark(success):
    return f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"


def check_files():
    """Verificar archivos requeridos"""
    print_header("Verificando archivos requeridos")
    
    required_files = [
        ('config/config.yaml', 'Archivo de configuración'),
        ('config/mysql_schema.sql', 'Schema de MySQL'),
        ('src/collector.py', 'Collector principal'),
        ('src/database.py', 'Módulo de base de datos'),
        ('src/ontap_client.py', 'Cliente ONTAP'),
        ('run_collector.py', 'Script principal'),
        ('grafana/snapmirror_dashboard.json', 'Dashboard de Grafana'),
    ]
    
    all_ok = True
    for filepath, description in required_files:
        exists = Path(filepath).exists()
        print(f"{check_mark(exists)} {description}: {filepath}")
        if not exists:
            all_ok = False
    
    # Check CSV (puede ser mock o real)
    csv_files = list(Path('config').glob('ontap_instances*.csv'))
    if csv_files:
        print(f"{GREEN}✓{RESET} CSV de instancias encontrado: {csv_files[0]}")
    else:
        print(f"{YELLOW}⚠{RESET} CSV de instancias no encontrado")
        print(f"  Ejecuta: python3 generate_mock_csv.py --num-instances 50")
        all_ok = False
    
    return all_ok


def check_config():
    """Verificar configuración"""
    print_header("Verificando configuración (config/config.yaml)")
    
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"{GREEN}✓{RESET} Archivo config.yaml válido\n")
        
        # Mostrar configuración de base de datos
        db_config = config.get('database', {})
        print("Configuración MySQL:")
        print(f"  Host:     {db_config.get('host', 'N/A')}")
        print(f"  Port:     {db_config.get('port', 'N/A')}")
        print(f"  Database: {YELLOW}{db_config.get('database', 'N/A')}{RESET}")
        print(f"  User:     {db_config.get('user', 'N/A')}")
        print(f"  Password: {'*' * len(db_config.get('password', ''))}")
        
        # Configuración del collector
        print("\nConfiguración Collector:")
        collector_config = config.get('collector', {})
        print(f"  Mode:     {collector_config.get('mode', 'N/A')}")
        print(f"  Interval: {collector_config.get('interval_seconds', 'N/A')}s")
        print(f"  Delay:    {collector_config.get('stagger_delay_seconds', 'N/A')}s")
        
        # Thresholds
        print("\nThresholds:")
        thresholds = config.get('thresholds', {})
        print(f"  Warning:  {thresholds.get('warning', 'N/A')}s ({thresholds.get('warning', 0)//60} min)")
        print(f"  Critical: {thresholds.get('critical', 'N/A')}s ({thresholds.get('critical', 0)//60} min)")
        
        return True, config
        
    except Exception as e:
        print(f"{RED}✗{RESET} Error leyendo config.yaml: {e}")
        return False, None


def check_database(config):
    """Verificar conexión a base de datos"""
    print_header("Verificando MySQL")
    
    try:
        import pymysql
        
        db_config = config.get('database', {})
        
        # Intentar conexión
        conn = pymysql.connect(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 3306),
            user=db_config.get('user', 'snapmirror_user'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'snapmirror_monitoring'),
            charset='utf8mb4'
        )
        
        print(f"{GREEN}✓{RESET} Conexión a MySQL exitosa")
        
        # Verificar tablas
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'ontap_instances',
            'snapmirror_relationships',
            'snapmirror_status_current',
            'snapmirror_status_history'
        ]
        
        print(f"\nTablas encontradas ({len(tables)}):")
        all_tables_ok = True
        for table in required_tables:
            exists = table in tables
            print(f"{check_mark(exists)} {table}")
            if not exists:
                all_tables_ok = False
        
        if not all_tables_ok:
            print(f"\n{YELLOW}⚠{RESET} Faltan tablas. Ejecuta:")
            print(f"  mysql -u {db_config.get('user')} -p{db_config.get('password')} {db_config.get('database')} < config/mysql_schema.sql")
        
        # Contar registros
        if all_tables_ok:
            cursor.execute("SELECT COUNT(*) FROM ontap_instances")
            instance_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM snapmirror_relationships")
            rel_count = cursor.fetchone()[0]
            
            print(f"\nDatos actuales:")
            print(f"  Instancias ONTAP: {instance_count}")
            print(f"  Relaciones SnapMirror: {rel_count}")
        
        conn.close()
        return True
        
    except ImportError:
        print(f"{RED}✗{RESET} PyMySQL no instalado")
        print(f"  Ejecuta: pip3 install pymysql")
        return False
    except Exception as e:
        print(f"{RED}✗{RESET} Error conectando a MySQL: {e}")
        print(f"\n{YELLOW}Solución:{RESET}")
        print(f"  1. Verificar que MySQL esté corriendo: sudo systemctl status mysqld")
        print(f"  2. Verificar credenciales en config/config.yaml")
        print(f"  3. Crear base de datos si no existe:")
        print(f"     mysql -u root -p")
        print(f"     CREATE DATABASE {db_config.get('database', 'snapmirror_monitoring')};")
        return False


def check_python_deps():
    """Verificar dependencias Python"""
    print_header("Verificando dependencias Python")
    
    required_modules = [
        ('pymysql', 'PyMySQL'),
        ('yaml', 'PyYAML'),
        ('requests', 'requests'),
        ('asyncio', 'asyncio (built-in)'),
    ]
    
    all_ok = True
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
            print(f"{GREEN}✓{RESET} {package_name}")
        except ImportError:
            print(f"{RED}✗{RESET} {package_name} no instalado")
            all_ok = False
    
    if not all_ok:
        print(f"\n{YELLOW}Instalar dependencias:{RESET}")
        print(f"  pip3 install -r requirements.txt")
    
    return all_ok


def check_grafana():
    """Verificar Grafana"""
    print_header("Verificando Grafana")
    
    try:
        import requests
        response = requests.get('http://localhost:3000/api/health', timeout=5)
        
        if response.status_code == 200:
            print(f"{GREEN}✓{RESET} Grafana corriendo en http://localhost:3000")
            print(f"  Usuario por defecto: admin / admin")
            print(f"\n  {YELLOW}Configurar datasource:{RESET}")
            print(f"    1. Ir a: Configuration > Data sources > Add data source > MySQL")
            print(f"    2. Configurar:")
            print(f"       Host: localhost:3306")
            print(f"       Database: snapmirror_monitoring")
            print(f"       User: snapmirror_user")
            print(f"       Password: SnapMirror123!")
            print(f"    3. Importar dashboard: grafana/snapmirror_dashboard.json")
            return True
        else:
            print(f"{YELLOW}⚠{RESET} Grafana responde pero con código {response.status_code}")
            return False
            
    except Exception as e:
        print(f"{RED}✗{RESET} Grafana no accesible en http://localhost:3000")
        print(f"  Error: {e}")
        print(f"\n{YELLOW}Solución:{RESET}")
        print(f"  sudo systemctl start grafana-server")
        print(f"  sudo systemctl enable grafana-server")
        return False


def main():
    print(f"{BLUE}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   SnapMirror Monitor - Verificación de Configuración    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(RESET)
    
    # Cambiar al directorio del proyecto si es necesario
    if not Path('config/config.yaml').exists():
        print(f"{RED}Error:{RESET} Ejecuta este script desde el directorio raíz del proyecto")
        sys.exit(1)
    
    # Ejecutar verificaciones
    files_ok = check_files()
    config_ok, config = check_config()
    deps_ok = check_python_deps()
    
    if config:
        db_ok = check_database(config)
    else:
        db_ok = False
    
    grafana_ok = check_grafana()
    
    # Resumen final
    print_header("Resumen")
    
    checks = [
        ("Archivos requeridos", files_ok),
        ("Configuración", config_ok),
        ("Dependencias Python", deps_ok),
        ("Base de datos MySQL", db_ok),
        ("Grafana", grafana_ok),
    ]
    
    for check_name, status in checks:
        print(f"{check_mark(status)} {check_name}")
    
    all_ok = all(status for _, status in checks)
    
    if all_ok:
        print(f"\n{GREEN}✓ SISTEMA LISTO{RESET}")
        print(f"\nPróximos pasos:")
        print(f"  1. python3 run_collector.py --mode mock --once")
        print(f"  2. Verificar datos en Grafana: http://localhost:3000")
        print(f"  3. python3 run_collector.py --mode real --once")
    else:
        print(f"\n{YELLOW}⚠ CONFIGURACIÓN INCOMPLETA{RESET}")
        print(f"  Revisa los errores anteriores y corrígelos")
    
    print()


if __name__ == "__main__":
    main()
