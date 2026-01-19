"""
Script principal para ejecutar el collector de SnapMirror
"""

import sys
import argparse
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import asyncio
from src.collector import SnapMirrorCollector
import logging

def main():
    parser = argparse.ArgumentParser(
        description='SnapMirror Monitor - Collector para ONTAP Select',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Ejecutar una vez en modo mock
  python run_collector.py --once --mode mock
  
  # Ejecutar continuamente en modo real
  python run_collector.py --mode real
  
  # Ejecutar con configuración personalizada
  python run_collector.py --config mi_config.yaml --once
        """
    )
    
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Ruta al archivo de configuración (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Ejecutar una sola vez y salir (en lugar de modo continuo)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['mock', 'real'],
        help='Forzar modo de operación (sobrescribe configuración)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Nivel de logging (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configurar logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/collector.log'),
            logging.StreamHandler()
        ]
    )
    
    # Crear directorio de logs
    Path('logs').mkdir(exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("SnapMirror Monitor - Collector")
    logger.info("="*60)
    
    try:
        # Inicializar collector
        collector = SnapMirrorCollector(config_path=args.config)
        
        # Sobrescribir modo si se especificó
        if args.mode:
            collector.mode = args.mode
            logger.info(f"Modo forzado a: {args.mode}")
        
        # Setup
        collector.setup()
        
        # Ejecutar
        if args.once:
            logger.info("Modo: Ejecución única")
            asyncio.run(collector.collect_all_staggered())
        else:
            logger.info("Modo: Ejecución continua")
            asyncio.run(collector.run_continuous())
        
    except KeyboardInterrupt:
        logger.info("\nDetenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if 'collector' in locals():
            collector.cleanup()
    
    logger.info("Collector finalizado correctamente")


if __name__ == "__main__":
    main()
