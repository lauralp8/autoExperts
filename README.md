# Project Details

> **Branch: `justmap`** — SnapMirror map monitoring via **Napp Console API**.  
> Scope: geo-map dashboard and relationship table only. No capacity panels, no auto-resize.

Customer: CORPME
SO#: <SO_NUMBER>
ProjectName: ps_corpme_snapmirror_grafana_monitor_nappconsole

## Table of Contents

1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Usage](#usage)
4. [Napp Console API adaptation](#napp-console-api-adaptation)
5. [License](#license)
6. [Authors & Contributors](#authors--contributors)

## Introduction

Automated monitoring solution for SnapMirror relationships across 1400+ geographically distributed instances managed by **Napp Console**. A Python collector queries Napp Console's REST API on a configurable schedule, stores the results in MySQL, and feeds a pre-built Grafana dashboard with an interactive geo-map and automatic alert levels.

**Scope (this branch):**

- Staggered REST API collection from Napp Console (configurable delay to avoid saturation)
- MySQL storage: current status + historical data for trend analysis
- Grafana dashboard with **geo-map** (color-coded markers), relationship table, and lag graphs
- Alert levels: OK (lag < 15 min), Warning (15–60 min), Critical (> 1 h), Error (unhealthy/paused)
- Mock mode for testing without real connectivity
- Instance management via CSV

**Out of scope in this branch:**

- Capacity / volume space monitoring dashboards
- Auto-resize / volume auto-grow logic
- Webhook server for resize events

## Requirements

- Python 3.9+
- MySQL 8.0+
- Grafana 10.0+ (with Geomap panel plugin)
- RHEL 8+, Ubuntu 20.04+, or Windows Server 2019+
- Network access to **Napp Console API** endpoint (port 443)

Python dependencies (see `requirements.txt`):

```
requests>=2.31.0
PyMySQL>=1.1.0
PyYAML>=6.0
asyncio>=3.4.3
aiohttp>=3.9.0
python-dotenv>=1.0.0
tabulate>=0.9.0
```

> Note: `netapp-ontap` SDK dependency removed — communication goes exclusively through Napp Console REST API.

## Usage

**1. Install dependencies:**

```bash
pip3 install -r requirements.txt
```

**2. Initialize database:**

```bash
mysql -u root -p < config/mysql_schema.sql
```

**3. Configure instances:**

Edit `config/ontap_instances.csv` with the list of Napp Console managed instances (name, napp_console_url, latitude, longitude).

**4. Run the collector:**

```bash
# Single run with mock data (testing)
python3 run_collector.py --mode mock --once

# Single run with real Napp Console
python3 run_collector.py --mode real --once

# Continuous mode (production) - every 5 minutes
python3 run_collector.py --mode real
```

**5. Import Grafana dashboard:**

Add a MySQL datasource in Grafana pointing to the database, then import `grafana/snapmirror_dashboard.json` (geo-map + relationship table).

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
  password: <change_me>
  database: snapmirror_monitoring

napp_console:
  base_url: https://<napp-console-host>
  api_token: <change_me>    # Bearer token for Napp Console API
  verify_ssl: true

collector:
  mode: real        # real | mock
  interval_seconds: 300
  stagger_delay_seconds: 0.2

thresholds:
  warning: 900      # 15 minutes
  critical: 3600    # 1 hour
```

## Napp Console API adaptation

The module `src/ontap_client.py` must be replaced (or wrapped) by a `src/napp_client.py` that calls **Napp Console REST API** instead of per-cluster ONTAP API.

The collector expects the new client to expose the **same interface**:

| Method | Expected return | Notes |
|--------|----------------|-------|
| `get_snapmirror_relationships(instance_id)` | `List[Dict]` | Fields: `uuid`, `source_path`, `destination_path`, `policy`, `state`, `healthy`, `lag_seconds`, `transfer_state` |
| `test_connection()` | `bool` | Used by `check_setup.py` |

See `REQUIREMENTS.md` for the full API specification and pending work items.

## License



## Authors & Contributors

- Carlos Alzaga Rodriguez - NetApp Professional Services
