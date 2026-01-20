#!/usr/bin/env python3
"""
Script de descubrimiento automático de clusters ONTAP
Conecta vía API REST, descubre relaciones SnapMirror y genera/actualiza el CSV
Modo incremental: permite añadir nuevos clusters sin borrar los existentes
"""

import csv
import sys
import requests
import urllib3
from pathlib import Path
from requests.auth import HTTPBasicAuth

# Deshabilitar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_section(text):
    """Imprime una sección formateada"""
    print("\n" + "-" * 70)
    print(text)
    print("-" * 70)


def get_input(prompt, default=None):
    """Obtiene input del usuario con valor por defecto"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def get_float(prompt, default=None):
    """Obtiene un número float del usuario"""
    while True:
        try:
            if default is not None:
                value = get_input(prompt, str(default))
            else:
                value = input(f"{prompt}: ").strip()
            return float(value)
        except ValueError:
            print("❌ Error: Introduce un número válido")


def get_yes_no(prompt, default=True):
    """Obtiene respuesta sí/no del usuario"""
    default_text = "S/n" if default else "s/N"
    while True:
        response = input(f"{prompt} ({default_text}): ").strip().lower()
        if not response:
            return default
        if response in ['s', 'si', 'y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print("❌ Responde 's' o 'n'")


def test_ontap_connection(host, username, password):
    """
    Prueba la conexión al cluster ONTAP
    
    Returns:
        dict con cluster info o None si falla
    """
    url = f"https://{host}/api/cluster"
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(username, password),
            headers={'Accept': 'application/json'},
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'uuid': data.get('uuid'),
                'name': data.get('name'),
                'version': data.get('version', {}).get('full', 'unknown')
            }
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None
    
    except requests.exceptions.ConnectionError:
        print(f"❌ No se pudo conectar a {host} - verifica IP y red")
        return None
    except requests.exceptions.Timeout:
        print(f"❌ Timeout conectando a {host}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_snapmirror_relationships(host, username, password):
    """
    Obtiene todas las relaciones SnapMirror del cluster
    
    Returns:
        Lista de relaciones SnapMirror
    """
    url = f"https://{host}/api/snapmirror/relationships"
    
    params = {
        'fields': 'uuid,source.path,destination.path,policy.name,state,healthy',
        'return_records': 'true'
    }
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(username, password),
            headers={'Accept': 'application/json'},
            params=params,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('records', [])
        else:
            print(f"⚠ Error obteniendo relaciones: HTTP {response.status_code}")
            return []
    
    except Exception as e:
        print(f"⚠ Error obteniendo relaciones SnapMirror: {e}")
        return []


def load_existing_csv(csv_path):
    """Carga el CSV existente si existe"""
    if not Path(csv_path).exists():
        return []
    
    instances = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            instances.append(row)
    
    return instances


def save_csv(csv_path, instances):
    """Guarda el CSV con las instancias"""
    Path('config').mkdir(exist_ok=True)
    
    fieldnames = ['name', 'ip_address', 'latitude', 'longitude', 'location_name', 'username', 'password']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(instances)


def main():
    print_header("DESCUBRIMIENTO AUTOMÁTICO DE CLUSTERS ONTAP")
    print("Este script se conecta a clusters ONTAP vía API REST y descubre")
    print("las relaciones SnapMirror automáticamente.")
    print()
    
    csv_path = 'config/ontap_instances.csv'
    
    # Verificar si existe CSV previo
    existing_instances = load_existing_csv(csv_path)
    
    if existing_instances:
        print(f"📁 Se encontró archivo existente con {len(existing_instances)} instancias")
        print()
        print("Modo de operación:")
        print("  1. AÑADIR - Agregar nuevos clusters (mantiene los existentes)")
        print("  2. REEMPLAZAR - Crear desde cero (borra los existentes)")
        print()
        
        mode = input("Selecciona modo (1/2) [1]: ").strip()
        
        if mode == '2':
            if get_yes_no("⚠ ¿Confirmas eliminar todos los datos existentes?", False):
                instances = []
                print("✓ Modo REEMPLAZAR activado")
            else:
                print("Cancelado. Usando modo AÑADIR")
                instances = existing_instances
        else:
            instances = existing_instances
            print("✓ Modo AÑADIR activado")
    else:
        instances = []
        print("📝 No hay archivo previo. Creando desde cero...")
    
    # Bucle para añadir clusters
    cluster_count = 0
    
    while True:
        print_section(f"CLUSTER #{cluster_count + 1}")
        
        # Datos del cluster
        cluster_name = get_input("Nombre del cluster/instancia", f"ontap-cluster-{cluster_count + 1:02d}")
        cluster_ip = get_input("Dirección IP del cluster")
        
        if not cluster_ip:
            print("❌ IP requerida")
            continue
        
        # Credenciales
        username = get_input("Usuario admin", "admin")
        password = get_input("Contraseña")
        
        # Probar conexión
        print(f"\n🔍 Conectando a {cluster_ip}...")
        cluster_info = test_ontap_connection(cluster_ip, username, password)
        
        if not cluster_info:
            print("❌ No se pudo conectar al cluster")
            retry = get_yes_no("¿Reintentar con otras credenciales?", True)
            if retry:
                continue
            else:
                break
        
        print(f"✓ Conectado exitosamente a: {cluster_info['name']}")
        print(f"  UUID: {cluster_info['uuid']}")
        print(f"  Versión: {cluster_info['version']}")
        
        # Ubicación geográfica
        print()
        location_name = get_input("Ubicación/Datacenter", cluster_info['name'])
        print(f"Coordenadas geográficas de {location_name}:")
        print("  (Puedes buscarlas en Google Maps → Click derecho → Coordenadas)")
        latitude = get_float("  Latitud (ej: 40.4168)", 40.4168)
        longitude = get_float("  Longitud (ej: -3.7038)", -3.7038)
        
        # Descubrir relaciones SnapMirror
        print(f"\n🔍 Descubriendo relaciones SnapMirror en {cluster_ip}...")
        relationships = get_snapmirror_relationships(cluster_ip, username, password)
        
        if relationships:
            print(f"✓ Se encontraron {len(relationships)} relaciones SnapMirror:")
            for i, rel in enumerate(relationships[:5], 1):
                src = rel.get('source', {}).get('path', 'N/A')
                dst = rel.get('destination', {}).get('path', 'N/A')
                state = rel.get('state', 'N/A')
                print(f"  {i}. {src} → {dst} ({state})")
            
            if len(relationships) > 5:
                print(f"  ... y {len(relationships) - 5} más")
        else:
            print("⚠ No se encontraron relaciones SnapMirror en este cluster")
            print("  El cluster se añadirá igualmente al inventario")
        
        # Añadir al inventario
        instance = {
            'name': cluster_name,
            'ip_address': cluster_ip,
            'latitude': latitude,
            'longitude': longitude,
            'location_name': location_name,
            'username': username,
            'password': password
        }
        
        instances.append(instance)
        cluster_count += 1
        
        print(f"\n✓ Cluster añadido al inventario ({cluster_count} total)")
        
        # Preguntar si quiere añadir más
        print()
        if not get_yes_no("¿Añadir otro cluster?", False):
            break
    
    # Guardar CSV
    if cluster_count == 0:
        print("\n⚠ No se añadió ningún cluster. No se modificó el archivo")
        return
    
    print_header("GUARDANDO CONFIGURACIÓN")
    
    save_csv(csv_path, instances)
    
    print(f"✓ CSV guardado: {csv_path}")
    print(f"✓ Total instancias: {len(instances)}")
    
    # Mostrar preview
    print()
    print("Preview del archivo:")
    print_section("")
    
    with open(csv_path, 'r') as f:
        for i, line in enumerate(f):
            if i < 6:  # Header + 5 lines
                print(line.rstrip())
    
    print("-" * 70)
    
    # Actualizar config.yaml
    print()
    if get_yes_no("¿Actualizar config.yaml para usar modo 'real'?", True):
        config_file = 'config/config.yaml'
        
        try:
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Cambiar modo a real
            import re
            config_content = re.sub(r'mode:\s*mock', 'mode: real', config_content)
            
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            print(f"✓ config.yaml actualizado a modo 'real'")
        
        except Exception as e:
            print(f"⚠ No se pudo actualizar config.yaml: {e}")
            print(f"  Cambia manualmente 'mode: mock' a 'mode: real'")
    
    # Instrucciones finales
    print_header("✅ CONFIGURACIÓN COMPLETADA")
    print()
    print("Próximos pasos:")
    print(f"  1. Revisar archivo: {csv_path}")
    print("  2. Ejecutar collector:")
    print("     python3.12 run_collector.py --mode real --once")
    print("  3. Verificar datos en Grafana")
    print("  4. Para añadir más clusters, ejecuta este script nuevamente")
    print()
    print("El collector se conectará a cada cluster y monitoreará")
    print("todas las relaciones SnapMirror automáticamente.")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Proceso cancelado por el usuario")
        sys.exit(1)
