# Project Details

Customer: CORPME
SO#: <SO_NUMBER>
ProjectName: ps_corpme_snapmirror_grafana_monitor_python

## Table of Contents

1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Usage](#usage)
4. [License](#license)
5. [Authors & Contributors](#authors--contributors)

## Introduction

Automated monitoring solution for SnapMirror relationships across 1400+ geographically distributed ONTAP Select instances. A Python collector queries each cluster via REST API on a configurable schedule, stores the results in MySQL, and feeds a pre-built Grafana dashboard with an interactive map and automatic alert levels.

**Scope:**

- Staggered REST API collection from ONTAP clusters (configurable delay to avoid saturation)
- MySQL storage: current status + historical data for trend analysis
- Grafana dashboard with geo-map (color-coded markers), relationship table, and lag graphs
- Alert levels: OK (lag < 15 min), Warning (15-60 min), Critical (> 1 h), Error (unhealthy/paused)
- Mock mode for testing without real ONTAP connectivity
- Instance management via CSV or interactive discovery script

## Requirements

- Python 3.9+
- MySQL 8.0+
- Grafana 10.0+
- RHEL 8+, Ubuntu 20.04+, or Windows Server 2019+
- Network access to ONTAP cluster management LIFs (port 443)

Python dependencies (see `requirements.txt`):

```
netapp-ontap>=9.12.0
requests>=2.31.0
PyMySQL>=1.1.0
PyYAML>=6.0
asyncio>=3.4.3
aiohttp>=3.9.0
python-dotenv>=1.0.0
tabulate>=0.9.0
```

## Usage

**1. Install dependencies:**

```bash
pip3 install -r requirements.txt
```

**2. Initialize database:**

```bash
mysql -u root -p < config/mysql_schema.sql
```

**3. Configure ONTAP instances:**

Edit `config/ontap_instances.csv` or use the interactive discovery:

```bash
python3 discover_ontap_clusters.py
```

**4. Run the collector:**

```bash
# Single run with mock data (testing)
python3 run_collector.py --mode mock --once

# Single run with real clusters
python3 run_collector.py --mode real --once

# Continuous mode (production) - every 5 minutes
python3 run_collector.py --mode real
```

**5. Import Grafana dashboard:**

Add a MySQL datasource in Grafana pointing to the database, then import `grafana/snapmirror_dashboard.json`.

**6. (Optional) Deploy as a systemd service:**

```bash
sudo cp collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now collector
```

```yaml
---
# config/config.yaml - main configuration
database:
  host: localhost
  port: 3306
  user: snapmirror_user
  password: <password>
  database: snapmirror_monitoring

collector:
  mode: real        # real | mock
  interval_seconds: 300
  stagger_delay_seconds: 0.2

thresholds:
  warning: 900      # 15 minutes
  critical: 3600    # 1 hour
```

## License



## Authors & Contributors

- Carlos Alzaga Rodriguez - NetApp Professional Services
