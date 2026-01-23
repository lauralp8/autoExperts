"""
Main script to run the SnapMirror collector
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import asyncio
from src.collector import SnapMirrorCollector
import logging

def main():
    parser = argparse.ArgumentParser(
        description='SnapMirror Monitor - Collector for ONTAP Select',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once in mock mode
  python run_collector.py --once --mode mock
  
  # Run continuously in real mode
  python run_collector.py --mode real
  
  # Run with custom configuration
  python run_collector.py --config my_config.yaml --once
        """
    )
    
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (instead of continuous mode)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['mock', 'real'],
        help='Force operation mode (overrides configuration)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
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
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("SnapMirror Monitor - Collector")
    logger.info("="*60)
    
    try:
        # Initialize collector
        collector = SnapMirrorCollector(config_path=args.config)
        
        # Override mode if specified
        if args.mode:
            collector.mode = args.mode
            logger.info(f"Mode forced to: {args.mode}")
        
        # Setup
        collector.setup()
        
        # Execute
        if args.once:
            logger.info("Mode: Single execution")
            asyncio.run(collector.collect_all_staggered())
        else:
            logger.info("Mode: Continuous execution")
            asyncio.run(collector.run_continuous())
        
    except KeyboardInterrupt:
        logger.info("\nStopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if 'collector' in locals():
            collector.cleanup()
    
    logger.info("Collector finished successfully")


if __name__ == "__main__":
    main()
