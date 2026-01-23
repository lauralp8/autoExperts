"""
Script to generate CSV of mock instances
Useful for testing and development
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.mock_data import generate_csv_instances
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Generate CSV with simulated ONTAP Select instances'
    )
    
    parser.add_argument(
        '--num-instances',
        type=int,
        default=100,
        help='Number of instances to generate (default: 100)'
    )
    
    parser.add_argument(
        '--output',
        default='config/ontap_instances_mock.csv',
        help='Output file (default: config/ontap_instances_mock.csv)'
    )
    
    args = parser.parse_args()
    
    print(f"Generating {args.num_instances} instances...")
    csv_content = generate_csv_instances(
        num_instances=args.num_instances,
        output_file=args.output
    )
    
    print(f"✓ CSV generated in: {args.output}")
    print(f"✓ Total instances: {args.num_instances}")
    
    # Show preview
    lines = csv_content.split('\n')
    print("\nPreview (first 5 lines):")
    print('-' * 80)
    for line in lines[:6]:
        print(line)
    print('-' * 80)


if __name__ == "__main__":
    main()
