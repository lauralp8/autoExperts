#!/usr/bin/env python3
"""
Script para limpiar datos históricos antiguos de la tabla snapmirror_status_history

Uso:
    python3 cleanup_history.py                    # Ver estadísticas (sin borrar)
    python3 cleanup_history.py --days 30          # Borrar registros > 30 días
    python3 cleanup_history.py --days 7 --dry-run # Simular borrado (sin ejecutar)
    
El histórico crece ~288 registros/día por relación (5 min intervals).
Con 100 relaciones = 28,800 registros/día = 864,000 registros/mes

Recomendación: Ejecutar semanalmente con --days 30
"""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import yaml
from database import SnapMirrorDB


def load_config(config_path: str = 'config/config.yaml') -> dict:
    """Cargar configuración desde YAML"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def format_number(n) -> str:
    """Formatear número con separador de miles"""
    if n is None:
        return "N/A"
    return f"{n:,}".replace(",", ".")


def main():
    parser = argparse.ArgumentParser(
        description='Limpieza de histórico de SnapMirror Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s                      Ver estadísticas actuales
  %(prog)s --days 30            Borrar registros mayores a 30 días
  %(prog)s --days 7 --dry-run   Simular borrado de 7 días
  %(prog)s --days 90            Mantener 90 días de histórico
        """
    )
    
    parser.add_argument(
        '--days', 
        type=int, 
        default=None,
        help='Número de días a mantener (borra registros más antiguos)'
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Simular sin borrar realmente'
    )
    
    parser.add_argument(
        '--config', 
        type=str, 
        default='config/config.yaml',
        help='Ruta al archivo de configuración'
    )
    
    args = parser.parse_args()
    
    # Cargar configuración
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo de configuración: {args.config}")
        sys.exit(1)
    
    # Conectar a la base de datos
    db_config = config['database']
    db = SnapMirrorDB(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )
    
    try:
        db.connect()
        print("✓ Conectado a MySQL")
        print()
        
        # Obtener estadísticas del histórico
        stats = db.get_history_stats()
        
        print("=" * 60)
        print("ESTADÍSTICAS DEL HISTÓRICO")
        print("=" * 60)
        print(f"  Total registros:      {format_number(stats.get('total_records', 0))}")
        print(f"  Registro más antiguo: {stats.get('oldest_record', 'N/A')}")
        print(f"  Registro más reciente:{stats.get('newest_record', 'N/A')}")
        print(f"  Media registros/día:  {format_number(int(stats.get('avg_records_per_day', 0) or 0))}")
        print("=" * 60)
        print()
        
        # Si no se especificó --days, solo mostrar estadísticas
        if args.days is None:
            print("💡 Para limpiar histórico, usa: python3 cleanup_history.py --days 30")
            print("   Esto borrará registros con más de 30 días de antigüedad.")
            return
        
        # Calcular cuántos registros se borrarían
        count_query = """
        SELECT COUNT(*) as count FROM snapmirror_status_history 
        WHERE collected_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        
        # Ejecutar query de conteo directamente
        with db.connection.cursor() as cursor:
            cursor.execute(count_query, (args.days,))
            result = cursor.fetchone()
            records_to_delete = result['count'] if result else 0
        
        if records_to_delete == 0:
            print(f"✓ No hay registros con más de {args.days} días de antigüedad.")
            return
        
        print(f"⚠️  Registros a eliminar (>{args.days} días): {format_number(records_to_delete)}")
        print()
        
        if args.dry_run:
            print("🔍 Modo DRY-RUN: No se ha borrado nada.")
            print(f"   Para ejecutar realmente: python3 cleanup_history.py --days {args.days}")
            return
        
        # Confirmar antes de borrar
        print("¿Estás seguro de que quieres borrar estos registros?")
        response = input("Escribe 'SI' para confirmar: ")
        
        if response.upper() != 'SI':
            print("❌ Operación cancelada.")
            return
        
        # Ejecutar limpieza
        print()
        print("Borrando registros...")
        deleted = db.cleanup_old_history(days=args.days)
        
        print()
        print("=" * 60)
        print(f"✓ LIMPIEZA COMPLETADA")
        print(f"  Registros eliminados: {format_number(deleted)}")
        print("=" * 60)
        
        # Mostrar nuevas estadísticas
        new_stats = db.get_history_stats()
        print()
        print("Estadísticas después de limpieza:")
        print(f"  Total registros:      {format_number(new_stats.get('total_records', 0))}")
        print(f"  Registro más antiguo: {new_stats.get('oldest_record', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
