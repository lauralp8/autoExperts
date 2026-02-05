#!/usr/bin/env python3
"""
Script para gestionar instancias ONTAP (alta/baja/eliminación)
Permite dar de baja lógica o eliminar completamente una instancia
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import yaml
import pymysql
from tabulate import tabulate


def load_config(config_path: str = 'config/config.yaml') -> dict:
    """Cargar configuración"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_connection(config: dict):
    """Obtener conexión a MySQL"""
    db_config = config['database']
    return pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def list_instances(conn, show_inactive: bool = False):
    """Listar todas las instancias"""
    with conn.cursor() as cursor:
        if show_inactive:
            query = """
                SELECT 
                    oi.id,
                    oi.name,
                    oi.ip_address,
                    oi.location_name,
                    oi.is_active,
                    COUNT(sr.id) as relationships,
                    MAX(ssc.collected_at) as last_collection
                FROM ontap_instances oi
                LEFT JOIN snapmirror_relationships sr ON oi.id = sr.instance_id
                LEFT JOIN snapmirror_status_current ssc ON sr.id = ssc.relationship_id
                GROUP BY oi.id, oi.name, oi.ip_address, oi.location_name, oi.is_active
                ORDER BY oi.is_active DESC, oi.name
            """
        else:
            query = """
                SELECT 
                    oi.id,
                    oi.name,
                    oi.ip_address,
                    oi.location_name,
                    oi.is_active,
                    COUNT(sr.id) as relationships,
                    MAX(ssc.collected_at) as last_collection
                FROM ontap_instances oi
                LEFT JOIN snapmirror_relationships sr ON oi.id = sr.instance_id
                LEFT JOIN snapmirror_status_current ssc ON sr.id = ssc.relationship_id
                WHERE oi.is_active = TRUE
                GROUP BY oi.id, oi.name, oi.ip_address, oi.location_name, oi.is_active
                ORDER BY oi.name
            """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("No se encontraron instancias.")
            return
        
        # Formatear para mostrar
        headers = ['ID', 'Nombre', 'IP', 'Ubicación', 'Activa', 'Relaciones', 'Última recolección']
        rows = []
        for r in results:
            rows.append([
                r['id'],
                r['name'],
                r['ip_address'],
                r['location_name'][:30] if r['location_name'] else '-',
                '✓' if r['is_active'] else '✗',
                r['relationships'],
                r['last_collection'] or 'Nunca'
            ])
        
        print(f"\n{'='*80}")
        print(f"  INSTANCIAS ONTAP {'(incluyendo inactivas)' if show_inactive else '(solo activas)'}")
        print(f"{'='*80}\n")
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        print(f"\nTotal: {len(results)} instancias\n")


def find_instance(conn, name: str = None, ip: str = None) -> dict:
    """Buscar instancia por nombre o IP"""
    with conn.cursor() as cursor:
        if name:
            cursor.execute("SELECT * FROM ontap_instances WHERE name = %s", (name,))
        elif ip:
            cursor.execute("SELECT * FROM ontap_instances WHERE ip_address = %s", (ip,))
        else:
            return None
        
        return cursor.fetchone()


def disable_instance(conn, instance: dict):
    """Desactivar instancia (baja lógica)"""
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE ontap_instances SET is_active = FALSE WHERE id = %s",
            (instance['id'],)
        )
        conn.commit()
    
    print(f"\n✓ Instancia '{instance['name']}' desactivada (is_active = FALSE)")
    print("  - Los datos históricos se mantienen")
    print("  - Ya no aparecerá en Grafana")
    print("  - Para reactivar: UPDATE ontap_instances SET is_active = TRUE WHERE name = '...'\n")


def enable_instance(conn, instance: dict):
    """Reactivar instancia"""
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE ontap_instances SET is_active = TRUE WHERE id = %s",
            (instance['id'],)
        )
        conn.commit()
    
    print(f"\n✓ Instancia '{instance['name']}' reactivada (is_active = TRUE)")
    print("  - Volverá a aparecer en Grafana")
    print("  - Se recolectará en el próximo ciclo (si está en el CSV)\n")


def delete_instance(conn, instance: dict, force: bool = False):
    """Eliminar instancia completamente"""
    
    # Contar relaciones y registros históricos
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM snapmirror_relationships WHERE instance_id = %s",
            (instance['id'],)
        )
        rel_count = cursor.fetchone()['cnt']
        
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM snapmirror_status_history WHERE instance_id = %s",
            (instance['id'],)
        )
        hist_count = cursor.fetchone()['cnt']
    
    print(f"\n⚠️  ATENCIÓN: Vas a eliminar la instancia '{instance['name']}'")
    print(f"   - Relaciones SnapMirror: {rel_count}")
    print(f"   - Registros históricos: {hist_count}")
    print(f"   - TODOS los datos serán eliminados permanentemente")
    
    if not force:
        confirm = input("\n¿Estás seguro? Escribe 'ELIMINAR' para confirmar: ")
        if confirm != 'ELIMINAR':
            print("\nOperación cancelada.\n")
            return
    
    # Eliminar (CASCADE eliminará relaciones y estados)
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM ontap_instances WHERE id = %s",
            (instance['id'],)
        )
        conn.commit()
    
    print(f"\n✓ Instancia '{instance['name']}' eliminada completamente")
    print(f"  - {rel_count} relaciones eliminadas")
    print(f"  - {hist_count} registros históricos eliminados\n")


def main():
    parser = argparse.ArgumentParser(
        description='Gestión de instancias ONTAP - Alta/Baja/Eliminación',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Listar instancias activas
  python remove_instance.py --list
  
  # Listar todas (incluyendo inactivas)
  python remove_instance.py --list --all
  
  # Desactivar instancia (baja lógica - RECOMENDADO)
  python remove_instance.py --name "ontap-select-madrid-01" --disable
  
  # Reactivar instancia
  python remove_instance.py --name "ontap-select-madrid-01" --enable
  
  # Eliminar instancia por nombre (con confirmación)
  python remove_instance.py --name "ontap-select-madrid-01" --delete
  
  # Eliminar por IP sin confirmación
  python remove_instance.py --ip "192.168.1.100" --delete --force
        """
    )
    
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Ruta al archivo de configuración'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='Listar todas las instancias'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Incluir instancias inactivas en el listado'
    )
    
    parser.add_argument(
        '--name',
        help='Nombre de la instancia a gestionar'
    )
    
    parser.add_argument(
        '--ip',
        help='IP de la instancia a gestionar'
    )
    
    parser.add_argument(
        '--disable',
        action='store_true',
        help='Desactivar instancia (baja lógica, mantiene datos)'
    )
    
    parser.add_argument(
        '--enable',
        action='store_true',
        help='Reactivar instancia desactivada'
    )
    
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Eliminar instancia completamente (IRREVERSIBLE)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='No pedir confirmación para eliminar'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if not args.list and not args.name and not args.ip:
        parser.print_help()
        sys.exit(1)
    
    if (args.disable or args.enable or args.delete) and not (args.name or args.ip):
        print("Error: Debes especificar --name o --ip para esta operación")
        sys.exit(1)
    
    # Cargar config y conectar
    try:
        config = load_config(args.config)
        conn = get_connection(config)
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        sys.exit(1)
    
    try:
        # Listar
        if args.list:
            list_instances(conn, show_inactive=args.all)
            return
        
        # Buscar instancia
        instance = find_instance(conn, name=args.name, ip=args.ip)
        
        if not instance:
            identifier = args.name or args.ip
            print(f"\nError: No se encontró la instancia '{identifier}'")
            print("Usa --list para ver las instancias disponibles\n")
            sys.exit(1)
        
        # Ejecutar acción
        if args.disable:
            if not instance['is_active']:
                print(f"\nLa instancia '{instance['name']}' ya está desactivada.\n")
            else:
                disable_instance(conn, instance)
        
        elif args.enable:
            if instance['is_active']:
                print(f"\nLa instancia '{instance['name']}' ya está activa.\n")
            else:
                enable_instance(conn, instance)
        
        elif args.delete:
            delete_instance(conn, instance, force=args.force)
        
        else:
            # Solo mostrar info de la instancia
            print(f"\nInstancia encontrada:")
            print(f"  ID: {instance['id']}")
            print(f"  Nombre: {instance['name']}")
            print(f"  IP: {instance['ip_address']}")
            print(f"  Ubicación: {instance['location_name']}")
            print(f"  Activa: {'Sí' if instance['is_active'] else 'No'}")
            print(f"\nUsa --disable, --enable o --delete para gestionar esta instancia.\n")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
