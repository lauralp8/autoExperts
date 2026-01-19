"""
Script para generar CSV de instancias mock
Útil para testing y desarrollo
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.mock_data import generate_csv_instances
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Genera CSV con instancias ONTAP Select simuladas'
    )
    
    parser.add_argument(
        '--num-instances',
        type=int,
        default=100,
        help='Número de instancias a generar (default: 100)'
    )
    
    parser.add_argument(
        '--output',
        default='config/ontap_instances_mock.csv',
        help='Archivo de salida (default: config/ontap_instances_mock.csv)'
    )
    
    args = parser.parse_args()
    
    print(f"Generando {args.num_instances} instancias...")
    csv_content = generate_csv_instances(
        num_instances=args.num_instances,
        output_file=args.output
    )
    
    print(f"✓ CSV generado en: {args.output}")
    print(f"✓ Total instancias: {args.num_instances}")
    
    # Mostrar preview
    lines = csv_content.split('\n')
    print("\nPreview (primeras 5 líneas):")
    print('-' * 80)
    for line in lines[:6]:
        print(line)
    print('-' * 80)


if __name__ == "__main__":
    main()
