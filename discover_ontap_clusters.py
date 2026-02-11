#!/usr/bin/env python3
"""
Automatic discovery script for ONTAP clusters
Connects via REST API, discovers SnapMirror relationships and generates/updates the CSV
Incremental mode: allows adding new clusters without deleting existing ones
"""

import csv
import sys
import requests
import urllib3
from pathlib import Path
from requests.auth import HTTPBasicAuth

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_section(text):
    """Print a formatted section"""
    print("\n" + "-" * 70)
    print(text)
    print("-" * 70)


def get_input(prompt, default=None):
    """Get user input with default value"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def get_float(prompt, default=None):
    """Get a float number from the user"""
    while True:
        try:
            if default is not None:
                value = get_input(prompt, str(default))
            else:
                value = input(f"{prompt}: ").strip()
            return float(value)
        except ValueError:
            print("❌ Error: Enter a valid number")


def get_yes_no(prompt, default=True):
    """Get yes/no response from the user"""
    default_text = "S/n" if default else "s/N"
    while True:
        response = input(f"{prompt} ({default_text}): ").strip().lower()
        if not response:
            return default
        if response in ['s', 'si', 'y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print("❌ Answer 's' or 'n'")


def test_ontap_connection(host, username, password):
    """
    Test connection to ONTAP cluster
    
    Returns:
        dict with cluster info or None if it fails
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
        print(f"❌ Could not connect to {host} - check IP and network")
        return None
    except requests.exceptions.Timeout:
        print(f"❌ Timeout connecting to {host}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_snapmirror_relationships(host, username, password):
    """
    Get all SnapMirror relationships from the cluster
    
    Returns:
        List of SnapMirror relationships
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
            print(f"⚠ Error getting relationships: HTTP {response.status_code}")
            return []
    
    except Exception as e:
        print(f"⚠ Error getting SnapMirror relationships: {e}")
        return []


def load_existing_csv(csv_path):
    """Load existing CSV if it exists"""
    if not Path(csv_path).exists():
        return []
    
    instances = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            instances.append(row)
    
    return instances


def save_csv(csv_path, instances):
    """Save the CSV with instances"""
    Path('config').mkdir(exist_ok=True)
    
    fieldnames = ['name', 'ip_address', 'latitude', 'longitude', 'location_name', 'username', 'password']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(instances)


def main():
    print_header("AUTOMATIC DISCOVERY OF ONTAP CLUSTERS")
    print("This script connects to ONTAP clusters via REST API and discovers")
    print("SnapMirror relationships automatically.")
    print()
    
    csv_path = 'config/ontap_instances.csv'
    
    # Check if previous CSV exists
    existing_instances = load_existing_csv(csv_path)
    
    if existing_instances:
        print(f"📁 Found existing file with {len(existing_instances)} instances")
        print()
        print("Operation mode:")
        print("  1. ADD - Add new clusters (keeps existing ones)")
        print("  2. REPLACE - Create from scratch (deletes existing ones)")
        print()
        
        mode = input("Select mode (1/2) [1]: ").strip()
        
        if mode == '2':
            if get_yes_no("⚠ Confirm deletion of all existing data?", False):
                instances = []
                print("✓ REPLACE mode activated")
            else:
                print("Cancelled. Using ADD mode")
                instances = existing_instances
        else:
            instances = existing_instances
            print("✓ ADD mode activated")
    else:
        instances = []
        print("📝 No previous file. Creating from scratch...")
    
    # Loop to add clusters
    cluster_count = 0
    
    while True:
        print_section(f"CLUSTER #{cluster_count + 1}")
        
        # Cluster data
        cluster_name = get_input("Cluster/instance name", f"ontap-cluster-{cluster_count + 1:02d}")
        cluster_ip = get_input("Cluster IP address")
        
        if not cluster_ip:
            print("❌ IP required")
            continue
        
        # Credentials
        username = get_input("Admin user", "admin")
        password = get_input("Password")
        
        # Test connection
        print(f"\n🔍 Connecting to {cluster_ip}...")
        cluster_info = test_ontap_connection(cluster_ip, username, password)
        
        if not cluster_info:
            print("❌ Could not connect to cluster")
            retry = get_yes_no("Retry with other credentials?", True)
            if retry:
                continue
            else:
                break
        
        print(f"✓ Successfully connected to: {cluster_info['name']}")
        print(f"  UUID: {cluster_info['uuid']}")
        print(f"  Version: {cluster_info['version']}")
        
        # Geographic location
        print()
        location_name = get_input("Location/Datacenter", cluster_info['name'])
        print(f"Geographic coordinates of {location_name}:")
        print("  (You can find them on Google Maps → Right click → Coordinates)")
        latitude = get_float("  Latitude (e.g.: 40.4168)", 40.4168)
        longitude = get_float("  Longitude (e.g.: -3.7038)", -3.7038)
        
        # Discover SnapMirror relationships
        print(f"\n🔍 Discovering SnapMirror relationships on {cluster_ip}...")
        relationships = get_snapmirror_relationships(cluster_ip, username, password)
        
        if relationships:
            print(f"✓ Found {len(relationships)} SnapMirror relationships:")
            for i, rel in enumerate(relationships[:5], 1):
                src = rel.get('source', {}).get('path', 'N/A')
                dst = rel.get('destination', {}).get('path', 'N/A')
                state = rel.get('state', 'N/A')
                print(f"  {i}. {src} → {dst} ({state})")
            
            if len(relationships) > 5:
                print(f"  ... and {len(relationships) - 5} more")
        else:
            print("⚠ No SnapMirror relationships found on this cluster")
            print("  The cluster will be added to inventory anyway")
        
        # Add to inventory
        instance = {
            'name': cluster_name,
            'ip_address': cluster_ip,
            'latitude': latitude,
            'longitude': longitude,
            'location_name': location_name,
            'username': username,
            'password': password
        }
        
        # Check if cluster already exists (by name or IP)
        existing_idx = None
        for idx, existing in enumerate(instances):
            if existing['name'] == cluster_name or existing['ip_address'] == cluster_ip:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            # Update existing cluster
            instances[existing_idx] = instance
            print(f"\n✓ Cluster '{cluster_name}' UPDATED in inventory (was already present)")
        else:
            # Add new cluster
            instances.append(instance)
            cluster_count += 1
            print(f"\n✓ Cluster added to inventory ({len(instances)} total)")
        
        # Ask if wants to add more
        print()
        if not get_yes_no("Add another cluster?", False):
            break
    
    # Save CSV
    if cluster_count == 0:
        print("\n⚠ No cluster was added. File was not modified")
        return
    
    print_header("SAVING CONFIGURATION")
    
    save_csv(csv_path, instances)
    
    print(f"✓ CSV saved: {csv_path}")
    print(f"✓ Total instances: {len(instances)}")
    
    # Show preview
    print()
    print("File preview:")
    print_section("")
    
    with open(csv_path, 'r') as f:
        for i, line in enumerate(f):
            if i < 6:  # Header + 5 lines
                print(line.rstrip())
    
    print("-" * 70)
    
    # Update config.yaml
    print()
    if get_yes_no("Update config.yaml to use 'real' mode?", True):
        config_file = 'config/config.yaml'
        
        try:
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Change mode to real
            import re
            config_content = re.sub(r'mode:\s*mock', 'mode: real', config_content)
            
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            print(f"✓ config.yaml updated to 'real' mode")
        
        except Exception as e:
            print(f"⚠ Could not update config.yaml: {e}")
            print(f"  Manually change 'mode: mock' to 'mode: real'")
    
    # Final instructions
    print_header("✅ CONFIGURATION COMPLETED")
    print()
    print("Next steps:")
    print(f"  1. Review file: {csv_path}")
    print("  2. Run collector:")
    print("     python3.12 run_collector.py --mode real --once")
    print("  3. Verify data in Grafana")
    print("  4. To add more clusters, run this script again")
    print()
    print("The collector will connect to each cluster and monitor")
    print("all SnapMirror relationships automatically.")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Process cancelled by user")
        sys.exit(1)
