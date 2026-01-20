# NetApp ONTAP Select - SnapMirror Monitor

Monitoring system for SnapMirror relationships across 1400+ geographically distributed ONTAP Select instances. Grafana dashboard with map visualization and automatic alerts.

## Description

Complete solution that collects SnapMirror relationship status from multiple ONTAP Select instances via REST API, stores data in MySQL, and presents an interactive Grafana dashboard featuring:

- **Geographic map** with color-coded status markers
- **Automatic alerts** (Warning: >15min lag, Critical: >1h lag, Error: unhealthy)
- **Cascade collection** to distribute load (every 5 minutes)
- **Simulation mode** for testing without real ONTAP access
- **Historical data** for trend analysis
- **Complete view** of all relationships (not just problematic ones)

## Architecture

```
+---------------------------------------------+
|   1400 ONTAP Select Instances              |
|   (Geographically distributed)              |
+----------------------+----------------------+
                       | REST API (GET only)
                       | Cascade collection
                       v
+----------------------------------------------+
|   Python Collector (asyncio)                |
|   - Polling every 5 min                      |
|   - 0.2s delay between instances             |
|   - Mock/real mode                           |
+----------------------+-----------------------+
                       |
                       v
+----------------------------------------------+
|   MySQL Database                             |
|   - ontap_instances                          |
|   - snapmirror_relationships                 |
|   - snapmirror_status_current                |
|   - snapmirror_status_history                |
+----------------------+-----------------------+
                       |
                       v
+----------------------------------------------+
|   Grafana Dashboard                          |
|   - Geomap with colored markers              |
|   - Table with ALL relationships             |
|   - Trend graphs                             |
+----------------------------------------------+
```

## Project Structure

```
CORME/
+-- config/
|   +-- config.yaml                 # Main configuration
|   +-- mysql_schema.sql            # Database schema
|   +-- ontap_instances.csv         # ONTAP instances list
|
+-- src/
|   +-- collector.py                # Main collector
|   +-- ontap_client.py             # ONTAP REST API client
|   +-- database.py                 # MySQL operations
|   +-- mock_data.py                # Mock data generator
|
+-- grafana/
|   +-- snapmirror_dashboard.json   # Pre-configured dashboard
|
+-- logs/                           # Execution logs
|
+-- run_collector.py                # Main script
+-- init_database.py                # Database initialization
+-- generate_mock_csv.py            # Mock CSV generator
+-- discover_ontap_clusters.py      # Interactive discovery
+-- collector.service               # systemd service
+-- setup_lab.sh                    # Automated setup for Lab on Demand
+-- requirements.txt                # Python dependencies
+-- README.md                       # This file
```

## Customer Deployment - Quick Guide

This section describes the complete process to deploy the system in a customer environment.

### Estimated time: 30-45 minutes

### Step 1: Initial Infrastructure Setup (one-time)

On the customer's Linux server where the monitor will be installed:

```bash
# Clone the project
cd /root  # or your preferred directory
git clone <repository-url> corme
cd corme

# Automated setup for RHEL 8/9
chmod +x setup_lab.sh
./setup_lab.sh
```

The script will automatically install:
- MySQL 8.0.40 with configured database
- Grafana 10.2.3 with enabled service
- Python 3.12 and all dependencies
- Initialized database schema

### Step 2: Discover Customer's ONTAP Clusters (interactive)

```bash
python3 discover_ontap_clusters.py
```

This interactive script will guide you to:
1. Enter IP address and credentials for each ONTAP cluster
2. Automatically test REST API connection
3. Enter geographic coordinates for the map
4. Auto-discover all SnapMirror relationships
5. Save configuration to config/ontap_instances.csv

**Note:** You can run this script multiple times. It operates in incremental mode (adds without deleting existing clusters).

### Step 3: Verify Manual Collection

```bash
# Run a single collection to verify
python3 run_collector.py --mode real --once
```

Expected output:
- Successful connection to all clusters
- SnapMirror relationships discovered and stored in MySQL
- No connection errors

### Step 4: Configure Grafana Dashboard

1. **Access Grafana:**
   - URL: http://<server>:3000
   - Initial user: admin
   - Initial password: admin (will prompt to change)

2. **Configure MySQL Datasource:**
   - Menu: Configuration > Data sources > Add data source
   - Select: MySQL
   - Configuration:
     - Host: `localhost:3306`
     - Database: `snapmirror_monitoring`
     - User: `snapmirror_user`
     - Password: `SnapMirror123!` (change in production)
   - Click: **Save & Test** (must show "Database Connection OK")

3. **Import Dashboard:**
   - Menu: Dashboards > Import > Upload JSON file
   - Select: `grafana/snapmirror_dashboard.json`
   - In "Select a MySQL data source": choose the created datasource
   - Click: **Import**

4. **Verify Dashboard:**
   - Must show map with discovered clusters
   - Table with all SnapMirror relationships
   - Updated counters (Total Instances, Relations, Warnings, Critical, Errors)

### Step 5: Enable Systemd Service (continuous execution)

```bash
# 1. Verify Python path on your system
which python3.12  # or python3.9, depending on what you have installed

# 2. Edit service if path is different
vi collector.service
# Ensure ExecStart points to the correct path:
# ExecStart=/usr/bin/python3 /root/corme/run_collector.py --mode real

# 3. Install and enable service
sudo cp collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable collector
sudo systemctl start collector

# 4. Verify it's running
sudo systemctl status collector
```

### Step 6: Final Verification

After 5-10 minutes, verify everything is working:

```bash
# View service logs in real-time
sudo journalctl -u collector -f

# Verify data in MySQL
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e \
  "SELECT COUNT(*) as total_relationships, 
          SUM(CASE WHEN alert_level='ok' THEN 1 ELSE 0 END) as ok,
          SUM(CASE WHEN alert_level='warning' THEN 1 ELSE 0 END) as warning,
          SUM(CASE WHEN alert_level='critical' THEN 1 ELSE 0 END) as critical
   FROM snapmirror_status_current;"

# Verify Dashboard in Grafana
# Open browser and confirm data updates every 30 seconds
```

**The system is ready!** The collector will gather data every 5 minutes automatically.

---

## Installation and Setup (Detailed)

### Prerequisites

- **Python 3.9+** (tested with Python 3.12)
- **MySQL 8.0+** (compatible with 8.0.40)
- **Grafana 10.0+** (tested with 10.2.3)
- Access to ONTAP Select instances (real mode)
- Operating system: RHEL 8/9, Ubuntu 20.04+, or Windows 10+

### Option 1: Automated Setup (Lab on Demand - RHEL)

For NetApp Lab on Demand environments with RHEL 8.x or 9.x:

```bash
# Download and run setup script
cd /root
git clone <your-repo> corme
cd corme
chmod +x setup_lab.sh
./setup_lab.sh
```

The script will automatically install:
- MySQL 8.0.40 (correct version for RHEL 8 or 9)
- Grafana 10.2.3
- Python 3.12 with all dependencies
- Initialized database
- Configured systemd service

### Option 2: Manual Installation

#### 1. Install Python Dependencies

```bash
# Linux/Mac
cd /path/to/project
pip3 install -r requirements.txt

# Windows
cd C:\Users\...\CORME
pip install -r requirements.txt
```

Key dependencies:
- `aiohttp` - Asynchronous HTTP for REST API
- `PyMySQL` - MySQL connector
- `PyYAML` - Configuration reading
- `requests` - Synchronous HTTP

#### 2. Configure MySQL

Edit credentials in `config/config.yaml`:

```yaml
database:
  host: localhost
  port: 3306
  user: snapmirror_user
  password: SnapMirror123!  # Change in production
  database: snapmirror_monitoring
```

Initialize database:

```bash
# Create user and database
mysql -u root -p < config/mysql_schema.sql

# Or use Python script
python3 init_database.py
```

#### 3. Configure ONTAP Instances

**Option A: Interactive Discovery (RECOMMENDED)**

Use the discovery script to add real clusters:

```bash
python3 discover_ontap_clusters.py
```

The script will guide you to:
1. Connect to each ONTAP cluster
2. Test REST API connection
3. Enter geographic coordinates
4. Auto-discover SnapMirror relationships
5. Incrementally update CSV

**Option B: MOCK Mode (for testing)**

Generate sample CSV with 100 instances:

```bash
python3 generate_mock_csv.py --num-instances 100 --output config/ontap_instances.csv
```

**Option C: REAL Mode (manual)**

Directly edit `config/ontap_instances.csv`:

```csv
name,ip_address,latitude,longitude,location_name,username,password
cluster1,192.168.0.101,40.4165,-3.7038,Madrid,admin,Netapp1!
cluster2,192.168.0.102,41.3888,2.159,Barcelona,admin,Netapp1!
cluster3,192.168.0.103,36.5298,6.2947,Cadiz,admin,Netapp1!
```

#### 4. Configure Grafana

**Step 1: Add MySQL Datasource**

```bash
# Access Grafana (default: http://localhost:3000)
# Initial user/password: admin/admin
```

In Grafana:
1. Configuration > Data sources > Add data source
2. Select MySQL
3. Configure:
   - **Host:** localhost:3306
   - **Database:** snapmirror_monitoring
   - **User:** snapmirror_user
   - **Password:** SnapMirror123!
4. Click "Save & Test" (must show "Database Connection OK")

**Step 2: Import Dashboard**

1. Dashboards > Import > Upload JSON file
2. Select: `grafana/snapmirror_dashboard.json`
3. In "Select a MySQL data source", choose the created datasource
4. Click "Import"

The dashboard will display:
- Geographic map with all instances
- Counters: Total Instances, Relations, Warnings, Critical, Errors
- Table with ALL relationships (ordered by severity)
- Lag trend graph (last 24h)

## Usage

### Quick Run

```bash
# Test with simulated data (single collection)
python3 run_collector.py --mode mock --once

# Real cluster collection (once)
python3 run_collector.py --mode real --once

# Continuous mode (every 5 minutes)
python3 run_collector.py --mode real
```

### MOCK Mode (Testing)

Run single collection with simulated data:

```bash
python3 run_collector.py --mode mock --once
```

Expected output:
```
============================================================
SnapMirror Monitor - Collector
============================================================
MOCK Mode: 100 simulated instances
Starting cascade collection: 100 instances
[1/100] Collecting mock-instance-001...
...
Collection completed in 23.45 seconds
Statistics:
  - Total instances: 100
  - Total relationships: 300
  - OK: 210
  - WARNING: 60
  - CRITICAL: 25
  - ERROR: 5
============================================================
```

Run in continuous mode (every 5 minutes):

```bash
python3 run_collector.py --mode mock
```

### REAL Mode (Production)

Ensure `config/ontap_instances.csv` is properly configured.

**Single execution (testing):**

```bash
python3 run_collector.py --mode real --once
```

Expected output:
```
[1/3] Collecting cluster1...
[2/3] Collecting cluster2...
[3/3] Collecting cluster3...
Collection completed in 3.49 seconds
  - Total relationships: 22
  - OK: 21
  - ERROR: 1
```

**Continuous execution (production):**

```bash
python3 run_collector.py --mode real
```

The collector will:
1. Collect data from all instances
2. Wait 5 minutes
3. Repeat the cycle indefinitely

To stop: `Ctrl+C`

### Run as Service (RECOMMENDED in production)

#### Linux (systemd)

The project includes pre-configured `collector.service`.

**Installation:**

```bash
# 1. Edit service if necessary
vi collector.service

# Ensure ExecStart uses correct Python path:
# ExecStart=/usr/local/bin/python3.12 /root/corme/run_collector.py --mode real

# 2. Copy to systemd
sudo cp collector.service /etc/systemd/system/

# 3. Grant permissions to script
chmod 644 run_collector.py

# 4. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable collector
sudo systemctl start collector

# 5. Verify status
sudo systemctl status collector

# 6. View logs in real-time
sudo journalctl -u collector -f
```

**Service management:**

```bash
# Stop
sudo systemctl stop collector

# Restart
sudo systemctl restart collector

# View recent logs
sudo journalctl -u collector -n 100

# Disable auto-start
sudo systemctl disable collector
```

### Advanced Options

```bash
# View complete help
python3 run_collector.py --help

# Use custom configuration
python3 run_collector.py --config my_config.yaml --mode real

# Change logging level
python3 run_collector.py --log-level DEBUG --mode real --once
```

## Grafana Dashboard

The dashboard includes:

### 1. General Metrics (top row)

- **Total ONTAP Instances** - Total number of monitored clusters
- **Total SnapMirror Relations** - Total number of relationships
- **Warnings** - Relationships with lag between 15-60 minutes (orange background)
- **Critical** - Relationships with lag > 60 minutes (red background)
- **Errors** - Unhealthy or paused relationships (purple background)

### 2. Geographic Map

Interactive visualization with:
- **Markers** at each cluster's coordinates
- **Color coding:**
  - Green: OK (lag < 15 min)
  - Yellow: Warning (lag 15-60 min)
  - Red: Critical (lag > 60 min)
  - Purple: Error (unhealthy/paused)
- **Marker size** proportional to number of relationships
- **Tooltip** with details on hover:
  - Cluster name
  - Location
  - Total relationships
  - Overall status

### 3. Table: All SnapMirror Relationships - Status Overview

Shows **ALL** relationships (not just problematic ones):
- Ordered by severity (Critical > Error > Warning > OK)
- Columns:
  - instance_name - Cluster name
  - location_name - Geographic location
  - source_path - Source SVM:volume
  - destination_path - Destination SVM:volume
  - policy - SnapMirror policy
  - state - State (snapmirrored, paused, uninitialized, etc.)
  - health_status - healthy / unhealthy
  - lag_minutes - Lag in minutes with 2 decimals
  - alert_level - OK, warning, critical, error (with background color)
  - last_check - Last collection timestamp

Limit: 500 relationships (configurable in JSON)

### 4. Graph: Lag Trend - Last 24 Hours (All Relations)

Lag evolution in the last 24 hours:
- Shows ALL relationships
- Colored lines per relationship
- Useful for:
  - Identifying patterns
  - Detecting trends
  - Viewing resolved issue history
  - Analyzing gradual degradation

### Refresh Rate

- Dashboard: 30 seconds (configurable top right)
- Collector: 5 minutes (configurable in config.yaml)
- Historical data: Indefinite (history table without retention limit)

## Detailed Configuration

### config.yaml File

```yaml
# MySQL Database
database:
  host: localhost
  port: 3306
  user: snapmirror_user
  password: SnapMirror123!
  database: snapmirror_monitoring

# Collection Configuration
collector:
  mode: mock  # mock or real
  interval_seconds: 300  # 5 minutes between collections
  stagger_delay_seconds: 0.2  # 200ms between each instance
  timeout_seconds: 30  # Timeout for each REST API request
  max_concurrent: 50  # Maximum concurrent requests

# Alert Thresholds (in seconds)
thresholds:
  warning: 900   # 15 minutes
  critical: 3600 # 1 hour

# Simulation (mock mode)
mock:
  num_instances: 100
  num_relationships_per_instance: 3
  simulate_lag_probability: 0.3  # 30% will have lag
  simulate_error_probability: 0.05  # 5% with errors

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: logs/collector.log
```

### Timing Calculations

With default configuration:
- **1400 instances** x **0.2s delay** = **280 seconds** (~4.7 minutes)
- Allows completing cycle before next interval (5 min)
- Each instance takes ~1-2s (API request + DB processing)
- Total time per cycle: ~5-7 minutes

### Performance Optimization Adjustments

**To reduce collection time:**

```yaml
collector:
  stagger_delay_seconds: 0.1  # Reduce to 100ms
  max_concurrent: 100  # Increase concurrency
```

**For slow clusters or high-latency networks:**

```yaml
collector:
  timeout_seconds: 60  # Increase timeout
  stagger_delay_seconds: 0.5  # More time between requests
```

### Alert Levels

The system classifies each relationship in one of these levels:

1. **OK** (green)
   - `healthy: true`
   - `lag_seconds < 900` (< 15 min)
   - `state: snapmirrored`

2. **WARNING** (yellow)
   - `healthy: true`
   - `900 <= lag_seconds < 3600` (15 min - 1 hour)

3. **CRITICAL** (red)
   - `healthy: true`
   - `lag_seconds >= 3600` (>= 1 hour)

4. **ERROR** (purple)
   - `healthy: false` (regardless of lag)
   - Problematic states: paused, uninitialized, broken-off, etc.

### Database

**Main tables:**

- `ontap_instances` - ONTAP clusters
- `snapmirror_relationships` - SnapMirror relationships
- `snapmirror_status_current` - Current status (1 row per relationship)
- `snapmirror_status_history` - Collection history

**Views for Grafana:**

- `v_snapmirror_map` - Aggregated data per cluster for map
- `v_snapmirror_detail` - Detailed data for tables

**Useful queries:**

```sql
-- View problematic relationships
SELECT * FROM v_snapmirror_detail 
WHERE alert_level IN ('warning', 'critical', 'error');

-- Average lag per cluster
SELECT instance_name, AVG(lag_minutes) as avg_lag
FROM v_snapmirror_detail
GROUP BY instance_name;

-- History of specific relationship
SELECT collected_at, lag_seconds/60 as lag_min, alert_level
FROM snapmirror_status_history
WHERE relationship_id = 123
ORDER BY collected_at DESC
LIMIT 100;
```

## Troubleshooting

### Error: Cannot connect to MySQL

```
Error connecting to MySQL: (2003, "Can't connect to MySQL server...")
```

**Solution:**
1. Verify MySQL is running:
   ```bash
   sudo systemctl status mysqld  # RHEL/CentOS
   sudo systemctl status mysql   # Ubuntu
   ```
2. Check credentials in `config/config.yaml`
3. Verify user exists and has permissions:
   ```sql
   SHOW GRANTS FOR 'snapmirror_user'@'localhost';
   ```
4. Verify firewall/ports (3306)

### Error: ONTAP Timeout

```
Timeout connecting to 192.168.0.101
```

**Solution:**
1. Verify network connectivity:
   ```bash
   ping 192.168.0.101
   curl -k https://192.168.0.101/api/cluster
   ```
2. Increase timeout in `config.yaml`:
   ```yaml
   collector:
     timeout_seconds: 60  # Increase from 30 to 60
   ```
3. Verify credentials in `ontap_instances.csv`

### Error: 400 Bad Request from ONTAP API

```
Error getting SnapMirror relationships: 400 Bad Request
```

**Solution:**
This error occurs when requesting fields not supported by ONTAP version.

The code is already optimized with minimal field list:
```
uuid,source.path,destination.path,policy.name,state,healthy,lag_time,transfer.state,transfer.end_time
```

If it persists, verify ONTAP version (must be 9.6+).

### Error: Data truncated for column 'last_transfer_end_timestamp'

```
(1265, "Data truncated for column 'last_transfer_end_timestamp' at row 1")
```

**Solution:**
This error is already resolved in current version. Code converts ISO 8601 timestamps to Unix timestamp (BIGINT).

If it appears, verify you have latest version of `src/collector.py`.

### Grafana Dashboard Empty

**Solution:**
1. Verify collector has run at least once:
   ```bash
   python3 run_collector.py --mode real --once
   ```

2. Check data exists in MySQL:
   ```sql
   USE snapmirror_monitoring;
   SELECT COUNT(*) FROM snapmirror_status_current;
   SELECT COUNT(*) FROM ontap_instances;
   ```

3. Verify datasource in Grafana:
   - Configuration > Data sources
   - Click on MySQL datasource
   - Click "Save & Test"
   - Must show "Database Connection OK"

4. Verify manual query in Grafana Explore:
   ```sql
   SELECT * FROM v_snapmirror_map LIMIT 10;
   ```

### systemd Service Fails with "exit code 203"

```
Main PID: 79903 (code=exited, status=203/EXEC)
```

**Solution:**
Error 203 indicates systemd cannot execute the binary.

1. Verify Python path:
   ```bash
   which python3.12
   # Output should be: /usr/local/bin/python3.12
   ```

2. Edit `/etc/systemd/system/collector.service`:
   ```ini
   ExecStart=/usr/local/bin/python3.12 /root/corme/run_collector.py --mode real
   ```
   (use exact path from step 1)

3. Grant permissions to script:
   ```bash
   chmod 644 /root/corme/run_collector.py
   ```

4. Reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart collector
   sudo systemctl status collector
   ```

### Lag Always Shows 0

**Solution:**
Problem was in old versions that didn't request `lag_time` field from API.

Verify `src/ontap_client.py` includes `lag_time` in request:
```python
params = {
    'fields': 'uuid,source.path,destination.path,policy.name,state,healthy,lag_time,transfer.state,transfer.end_time',
    ...
}
```

If missing, update to latest code version.

### Slow Performance with 1400 Instances

**Solution:**

1. Adjust maximum concurrency in `config.yaml`:
   ```yaml
   collector:
     max_concurrent: 100  # Increase if network allows
   ```

2. Reduce delay between instances:
   ```yaml
   stagger_delay_seconds: 0.1  # Reduce from 0.2 to 0.1
   ```

3. Verify server resources:
   ```bash
   top
   htop
   free -h
   ```

4. Consider running multiple collectors in parallel (split CSV)

## Production Optimizations

### 1. Historical Data Retention

By default, `snapmirror_status_history` table grows indefinitely. For production, implement periodic cleanup:

```sql
-- Create event to clean data older than 90 days
CREATE EVENT cleanup_old_history
ON SCHEDULE EVERY 1 DAY
DO
  DELETE FROM snapmirror_status_history 
  WHERE collected_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### 2. Additional Indexes (optional)

If you have thousands of relationships, these indexes can help:

```sql
-- Index for searches by cluster
CREATE INDEX idx_instance_alert ON snapmirror_status_current(instance_id, alert_level);

-- Index for historical queries by date
CREATE INDEX idx_history_date ON snapmirror_status_history(collected_at, alert_level);
```

### 3. Database Backup

Automated backup script:

```bash
#!/bin/bash
# backup_db.sh

BACKUP_DIR=/var/backups/snapmirror
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE=$BACKUP_DIR/snapmirror_$DATE.sql.gz

mkdir -p $BACKUP_DIR

mysqldump -u snapmirror_user -pSnapMirror123! \
  snapmirror_monitoring | gzip > $BACKUP_FILE

# Keep only last 30 days
find $BACKUP_DIR -name "snapmirror_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

Add to cron:
```bash
# Daily backup at 2 AM
0 2 * * * /root/scripts/backup_db.sh
```

### 4. Alerting in Grafana

Configure automatic alerts:

1. **Email Notifications:**
   - Alerting > Notification channels > Add channel
   - Type: Email
   - Addresses: your-team@netapp.com

2. **Critical Alert:**
   - In Dashboard > Panel "Critical"
   - Edit > Alert
   - Condition: `WHEN last() OF query(A) IS ABOVE 0`
   - For: 5m (wait 5 min before alerting)
   - Send to: Email

3. **Collector Stopped Alert:**
   - Create new panel with query:
     ```sql
     SELECT TIMESTAMPDIFF(MINUTE, MAX(collected_at), NOW()) as minutes_since_last
     FROM snapmirror_status_current;
     ```
   - Alert when `minutes_since_last > 10`

### 5. Collector Monitoring

Healthcheck script:

```bash
#!/bin/bash
# healthcheck.sh

# Verify service is running
if ! systemctl is-active --quiet collector; then
    echo "ERROR: Collector service stopped"
    systemctl start collector
    exit 1
fi

# Verify last collection (must be < 10 minutes)
LAST_COLLECTION=$(mysql -u snapmirror_user -pSnapMirror123! \
  -D snapmirror_monitoring -N -e \
  "SELECT TIMESTAMPDIFF(MINUTE, MAX(collected_at), NOW()) FROM snapmirror_status_current;")

if [ "$LAST_COLLECTION" -gt 10 ]; then
    echo "ERROR: Last collection $LAST_COLLECTION minutes ago"
    systemctl restart collector
    exit 1
fi

echo "OK: Collector functioning correctly"
exit 0
```

Add to cron every 5 minutes:
```bash
*/5 * * * * /root/scripts/healthcheck.sh >> /var/log/collector-health.log 2>&1
```

### 6. Secure Credential Management

For production, DO NOT store passwords in CSV. Use environment variables:

```bash
# Create .env file (do not commit to repo)
export ONTAP_DEFAULT_USER="admin"
export ONTAP_DEFAULT_PASSWORD="SecurePassword123!"
```

Modify `discover_ontap_clusters.py` to read from .env:

```python
import os
default_user = os.getenv('ONTAP_DEFAULT_USER', 'admin')
default_password = os.getenv('ONTAP_DEFAULT_PASSWORD')
```

### 7. High Availability

For critical environments:

1. **Redundant collector:**
   - Run 2 collector instances on different servers
   - Both write to same DB (no conflict)
   - If one fails, the other continues

2. **MySQL replication:**
   - Master-Slave for automatic backup
   - Master-Master for complete HA

3. **Grafana HA:**
   - Load balancer in front of multiple Grafana instances
   - All point to same MySQL

## Security

### Recommendations

1. **Credentials:**
   - DO NOT commit `ontap_instances.csv` with real passwords to repository
   - Add `ontap_instances.csv` to `.gitignore`
   - Use vault (HashiCorp Vault, Azure Key Vault, CyberArk, etc.)
   - Rotate passwords regularly (every 90 days)

2. **MySQL:**
   - User with minimum permissions (SELECT, INSERT, UPDATE, DELETE)
   - DO NOT grant DROP, CREATE, ALTER permissions
   - SSL/TLS connection in production:
     ```yaml
     database:
       ssl_ca: /path/to/ca-cert.pem
       ssl_cert: /path/to/client-cert.pem
       ssl_key: /path/to/client-key.pem
     ```

3. **ONTAP REST API:**
   - Create read-only user in ONTAP:
     ```
     security login create -user-or-group-name snapmirror-monitor \
       -application http -authentication-method password \
       -role readonly
     ```
   - Enable `verify_ssl=True` in production (requires valid certificates)

4. **Firewall:**
   - Restrict MySQL access only from collector server
   - Limit IPs that can query ONTAP API
   - Use VPN for Grafana access from outside corporate network

5. **Logs:**
   - DO NOT log passwords (already implemented in code)
   - Rotate logs regularly
   - Protect log files (chmod 640)

## Logs and Debugging

### Log Locations

- **Collector:** `logs/collector.log`
- **Systemd:** `journalctl -u collector -f`
- **MySQL:** `/var/log/mysql/error.log`
- **Grafana:** `/var/log/grafana/grafana.log`

### Logging Levels

Change in `config.yaml`:

```yaml
logging:
  level: DEBUG  # DEBUG, INFO, WARNING, ERROR
```

- **DEBUG:** All information (API requests, SQL queries, etc.)
- **INFO:** Normal operations (collections, results)
- **WARNING:** Non-critical issues (timeouts, missing data)
- **ERROR:** Serious errors (connection failures, crashes)

### Log Examples

**Successful collection:**
```
2026-01-20 07:45:50 - src.collector - INFO - [1/3] Collecting cluster1...
2026-01-20 07:45:51 - ontap_client - INFO - Retrieved 1 relationships from 192.168.0.101
2026-01-20 07:45:51 - src.collector - INFO - OK cluster1: 1 relationships processed
```

**Connection error:**
```
2026-01-20 07:45:50 - ontap_client - ERROR - Error connecting to 192.168.0.105: Timeout
2026-01-20 07:45:50 - src.collector - ERROR - Error processing cluster5: Connection timeout
```

**DEBUG mode (very verbose):**
```
2026-01-20 07:45:50 - ontap_client - DEBUG - GET https://192.168.0.101/api/snapmirror/relationships
2026-01-20 07:45:50 - ontap_client - DEBUG - Query params: {'fields': 'uuid,source.path,...'}
2026-01-20 07:45:51 - database - DEBUG - INSERT INTO snapmirror_status_current VALUES (...)
```

### Log Rotation

**Linux (logrotate):**

Create `/etc/logrotate.d/snapmirror-collector`:

```
/root/corme/logs/collector.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 640 root root
}
```

**Windows (PowerShell):**

Script to clean old logs:

```powershell
# Keep only last 30 days
$logDir = "C:\path\to\CORME\logs"
Get-ChildItem -Path $logDir -Filter "*.log" | 
  Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | 
  Remove-Item
```

## Contributing

To add features or report bugs:

1. Create feature branch
2. Test in mock mode before deploying
3. Document changes in CHANGELOG.md
4. Create Pull Request with detailed description

## License

NetApp Internal Use - All rights reserved

## Support

For technical support or inquiries:
- Email: [your-email@netapp.com]
- Slack: #snapmirror-monitoring
- Wiki: [Internal documentation URL]

---

**Version:** 1.0.0  
**Last updated:** January 2026  
**Author:** NetApp Professional Services  
**Tested on:**
- RHEL 8.10 / RHEL 9.3
- Python 3.9 / 3.12
- MySQL 8.0.40
- Grafana 10.2.3
- ONTAP 9.6+
