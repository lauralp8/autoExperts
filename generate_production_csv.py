#!/usr/bin/env python3
"""
Script interactivo para generar CSV de instancias ONTAP de producción
Solicita credenciales, IPs y coordenadas geográficas
"""

import csv
import sys
from pathlib import Path


def get_input(prompt, default=None):
    """Obtiene input del usuario con valor por defecto opcional"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def get_float(prompt):
    """Obtiene un número float del usuario"""
    while True:
        try:
            value = input(f"{prompt}: ").strip()
            return float(value)
        except ValueError:
            print("❌ Error: Introduce un número válido")


def get_int(prompt, default=None):
    """Obtiene un número entero del usuario"""
    while True:
        try:
            value = get_input(prompt, str(default) if default else None)
            return int(value)
        except ValueError:
            print("❌ Error: Introduce un número entero válido")


def get_yes_no(prompt):
    """Obtiene respuesta sí/no del usuario"""
    while True:
        response = input(f"{prompt} (s/n): ").strip().lower()
        if response in ['s', 'si', 'y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print("❌ Responde 's' o 'n'")


def main():
    print("=" * 70)
    print("GENERADOR DE CSV PARA INSTANCIAS ONTAP DE PRODUCCIÓN")
    print("=" * 70)
    print()
    
    # Configuración global
    print("📋 CONFIGURACIÓN GLOBAL")
    print("-" * 70)
    
    default_username = get_input("Usuario ONTAP (para todas las instancias)", "admin")
    default_password = get_input("Contraseña ONTAP (para todas las instancias)", "NetApp123")
    
    print()
    num_instances = get_int("¿Cuántas instancias ONTAP quieres configurar?", 300)
    
    print()
    print(f"✓ Se configurarán {num_instances} instancias con usuario '{default_username}'")
    print()
    
    # Opción de configuración
    print("📍 MÉTODO DE INGRESO DE DATOS")
    print("-" * 70)
    print("1. Manual - Ingresar cada instancia individualmente")
    print("2. Por rangos IP - Para redes consecutivas (ej: 10.0.1.1 - 10.0.1.254)")
    print("3. Mixto - Combinar ambos métodos")
    print()
    
    method = get_int("Selecciona método", 2)
    
    instances = []
    
    if method == 1:
        # Método manual
        print()
        print("📝 INGRESO MANUAL DE INSTANCIAS")
        print("-" * 70)
        
        for i in range(num_instances):
            print(f"\n--- Instancia {i+1}/{num_instances} ---")
            
            name = get_input(f"Nombre", f"ontap-select-{i+1:04d}")
            ip = get_input("Dirección IP")
            location = get_input("Ubicación (ciudad/datacenter)")
            
            print(f"Coordenadas de {location}:")
            latitude = get_float("  Latitud (ej: 40.4168)")
            longitude = get_float("  Longitud (ej: -3.7038)")
            
            use_custom_creds = get_yes_no("¿Usar credenciales diferentes?")
            if use_custom_creds:
                username = get_input("  Usuario", default_username)
                password = get_input("  Contraseña", default_password)
            else:
                username = default_username
                password = default_password
            
            instances.append({
                'name': name,
                'ip_address': ip,
                'latitude': latitude,
                'longitude': longitude,
                'location_name': location,
                'username': username,
                'password': password
            })
    
    elif method == 2:
        # Método por rangos
        print()
        print("📊 INGRESO POR RANGOS DE IP")
        print("-" * 70)
        print("Se asignará la misma ubicación geográfica a un rango de IPs")
        print()
        
        remaining = num_instances
        instance_counter = 1
        
        while remaining > 0:
            print(f"\n--- Rango de instancias (quedan {remaining}) ---")
            
            location = get_input("Ubicación/Datacenter para este rango")
            print(f"Coordenadas de {location}:")
            latitude = get_float("  Latitud")
            longitude = get_float("  Longitud")
            
            base_ip = get_input("IP base (ej: 10.0.1.1)")
            count = get_int(f"¿Cuántas instancias en este rango? (máx: {remaining})", min(50, remaining))
            
            # Parsear IP base
            ip_parts = base_ip.split('.')
            if len(ip_parts) != 4:
                print("❌ IP inválida, usando 10.0.0.1")
                ip_parts = ['10', '0', '0', '1']
            
            for i in range(count):
                # Incrementar último octeto
                last_octet = int(ip_parts[3]) + i
                
                # Manejar overflow de octetos
                if last_octet > 254:
                    ip_parts[2] = str(int(ip_parts[2]) + 1)
                    last_octet = 1
                
                current_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{last_octet}"
                
                instances.append({
                    'name': f"ontap-{location.lower().replace(' ', '-')}-{instance_counter:04d}",
                    'ip_address': current_ip,
                    'latitude': latitude,
                    'longitude': longitude,
                    'location_name': location,
                    'username': default_username,
                    'password': default_password
                })
                
                instance_counter += 1
            
            remaining -= count
    
    else:
        print("❌ Método no implementado todavía. Usa método 1 o 2")
        return
    
    # Guardar CSV
    output_file = 'config/ontap_instances.csv'
    
    print()
    print("=" * 70)
    print(f"💾 GUARDANDO ARCHIVO: {output_file}")
    print("=" * 70)
    
    Path('config').mkdir(exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'ip_address', 'latitude', 'longitude', 'location_name', 'username', 'password']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(instances)
    
    print(f"✓ CSV generado: {output_file}")
    print(f"✓ Total instancias: {len(instances)}")
    print()
    print("Preview (primeras 5 líneas):")
    print("-" * 70)
    
    with open(output_file, 'r') as f:
        for i, line in enumerate(f):
            if i < 6:  # Header + 5 lines
                print(line.strip())
    
    print("-" * 70)
    print()
    print("📊 CONFIGURACIÓN DE BASE DE DATOS")
    print("-" * 70)
    
    update_db_config = get_yes_no("¿Actualizar configuración de base de datos en config.yaml?")
    
    if update_db_config:
        print()
        db_host = get_input("Host MySQL", "localhost")
        db_port = get_int("Puerto MySQL", 3306)
        db_name = get_input("Nombre de base de datos", "snapmirror_monitoring")
        db_user = get_input("Usuario MySQL", "snapmirror_user")
        db_pass = get_input("Contraseña MySQL", "SnapMirror123!")
        
        # Leer config.yaml actual
        config_file = 'config/config.yaml'
        try:
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Actualizar valores
            import re
            config_content = re.sub(r'host:\s*\S+', f'host: {db_host}', config_content)
            config_content = re.sub(r'port:\s*\d+', f'port: {db_port}', config_content)
            config_content = re.sub(r'database:\s*\S+', f'database: {db_name}', config_content)
            config_content = re.sub(r'user:\s*\S+', f'user: {db_user}', config_content)
            config_content = re.sub(r'password:\s*\S+', f'password: {db_pass}', config_content)
            
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            print(f"✓ Configuración actualizada en {config_file}")
        
        except Exception as e:
            print(f"⚠ Error actualizando config.yaml: {e}")
    
    print()
    print("=" * 70)
    print("✅ PROCESO COMPLETADO")
    print("=" * 70)
    print()
    print("Próximos pasos:")
    print(f"  1. Revisar el archivo: {output_file}")
    print("  2. Ejecutar: python3.12 run_collector.py --mode real --once")
    print("  3. Verificar datos en Grafana")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Proceso cancelado por el usuario")
        sys.exit(1)
