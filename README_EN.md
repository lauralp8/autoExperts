# NetApp SnapMirror Monitor

Monitoring for SnapMirror relationships across 1400+ geographically distributed ONTAP Select instances. Grafana dashboard with interactive map and automatic alerts.

## What this does

This project collects SnapMirror relationship status from multiple ONTAP clusters and displays it in a visual Grafana dashboard. Basically:

- Queries each ONTAP cluster via REST API every 5 minutes
- Stores status in MySQL
- Shows everything on a Grafana map with color-coded status

**Alerts:**
- Green: All OK (lag < 15 min)
- Yellow: Warning (lag 15-60 min)
- Red: Critical (lag > 1 hour)
- Purple: Error (unhealthy or paused)

## Components

\\\
ONTAP Clusters  Python Collector  MySQL  Grafana Dashboard
\\\

**The collector** makes staggered queries with 0.2s delay between each cluster to avoid overwhelming anything.

**The database** has 4 main tables:
- \ontap_instances\ - The clusters
- \snapmirror_relationships\ - Configured relationships
- \snapmirror_status_current\ - Current status
- \snapmirror_status_history\ - Historical data

**The dashboard** shows:
- Map with color-coded markers for each cluster
- Table with all relationships (not just problematic ones)
- Lag trend graphs

## Important Files

\\\
config/
  config.yaml                 # Main configuration
  mysql_schema.sql            # Database schema
  ontap_instances.csv         # ONTAP instances list

src/
  collector.py                # Main collector
  ontap_client.py             # ONTAP REST API client
  database.py                 # MySQL operations
  mock_data.py                # Mock data generator

grafana/
  snapmirror_dashboard.json   # Pre-configured dashboard

run_collector.py              # Main script
init_database.py              # Database initialization
discover_ontap_clusters.py    # Interactive discovery
collector.service             # systemd service
setup_lab.sh                  # Automated setup
\\\

## Installation

### Requirements
- Python 3.9+
- MySQL 8.0+
- Grafana 10.0+
- RHEL/Ubuntu/Windows

### Quick setup (RHEL)

\\\ash
cd /root
git clone <repo> corme
cd corme
chmod +x setup_lab.sh
./setup_lab.sh
\\\

The script installs everything automatically.

### Manual setup

**1. Install Python dependencies:**
\\\ash
pip3 install -r requirements.txt
\\\

**2. Configure MySQL:**

Edit credentials in \config/config.yaml\ and run:
\\\ash
mysql -u root -p < config/mysql_schema.sql
\\\

**3. Configure ONTAP clusters:**

Option A - Interactive discovery (recommended):
\\\ash
python3 discover_ontap_clusters.py
\\\
Guides you step-by-step to add clusters, test connections, and discover relationships.

Option B - Mock mode (for testing):
\\\ash
python3 generate_mock_csv.py --num-instances 100
\\\

Option C - Edit CSV manually:
\\\csv
name,ip_address,latitude,longitude,location_name,username,password
cluster1,192.168.0.101,40.4165,-3.7038,Madrid,admin,Netapp1!
\\\

**4. Configure Grafana:**

- Add MySQL datasource pointing to the DB
- Import \grafana/snapmirror_dashboard.json\

## Usage

**Quick test with mock data:**
\\\ash
python3 run_collector.py --mode mock --once
\\\

**Real collection (once):**
\\\ash
python3 run_collector.py --mode real --once
\\\

**Continuous mode (every 5 min):**
\\\ash
python3 run_collector.py --mode real
\\\

### As a service (production)

**Linux:**
\\\ash
sudo cp collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable collector
sudo systemctl start collector
sudo systemctl status collector
\\\

**View logs:**
\\\ash
sudo journalctl -u collector -f
\\\

## Configuration

The \config/config.yaml\ file has everything:

\\\yaml
database:
  host: localhost
  user: snapmirror_user
  password: SnapMirror123!
  database: snapmirror_monitoring

collector:
  mode: real  # real or mock
  interval_seconds: 300  # 5 minutes
  stagger_delay_seconds: 0.2  # delay between clusters
  timeout_seconds: 30

thresholds:
  warning: 900   # 15 min
  critical: 3600 # 1 hour
\\\

## Dashboard

The dashboard has:

**Top metrics:**
- Total instances
- Total relations
- Warnings / Critical / Errors

**Map:**
- Marker for each cluster at its location
- Color by worst status
- Size by number of relationships
- Tooltip with details

**Table:**
- All relationships (not just problems)
- Sorted by severity
- Columns: cluster, location, source, destination, lag, status

**Graph:**
- Lag evolution last 24h
- All relationships

Auto-refresh every 30 seconds.

## Timings

With 1400 instances and 0.2s delay:
- Time per cycle: ~5-7 minutes
- Completes before next interval (5 min)

If you have few clusters, you can reduce delay to 0.1s.

## Notes

- The collector uses asyncio for concurrent queries
- There's staggered delay to avoid network saturation
- SSL verification is disabled (\erify_ssl=False\) - careful in production
- History grows indefinitely - consider periodic cleanup
- Mock mode is useful for testing without real clusters

## Questions?

If you need more info, help with deployment, or have any issues, contact me directly.

---

**Author:** NetApp Professional Services  
**Version:** 1.0.0