# NetApp SnapMirror Monitor

Monitorización de relaciones SnapMirror en 1400+ instancias ONTAP Select distribuidas geográficamente. Dashboard en Grafana con mapa interactivo y alertas automáticas.

## Qué hace esto

Este proyecto recolecta el estado de las relaciones SnapMirror de múltiples clusters ONTAP y lo presenta en un dashboard visual de Grafana. Básicamente:

- Consulta cada cluster ONTAP via REST API cada 5 minutos
- Guarda el estado en MySQL
- Muestra todo en un mapa de Grafana con colores según el estado

**Alertas:**
- Verde: Todo OK (lag < 15 min)
- Amarillo: Warning (lag 15-60 min)
- Rojo: Critical (lag > 1 hora)
- Morado: Error (unhealthy o pausado)

## Componentes

```
Clusters ONTAP → Python Collector → MySQL → Grafana Dashboard
```

**El collector** hace consultas escalonadas con 0.2s de delay entre cada cluster para no saturar nada.

**La base de datos** tiene 4 tablas principales:
- `ontap_instances` - Los clusters
- `snapmirror_relationships` - Las relaciones configuradas
- `snapmirror_status_current` - Estado actual
- `snapmirror_status_history` - Histórico

**El dashboard** muestra:
- Mapa con marcadores de colores por cada cluster
- Tabla con todas las relaciones (no solo las problemáticas)
- Gráficas de tendencia de lag

## Archivos del Proyecto

## Archivos del Proyecto

```
config/
  config.yaml                 # Configuración principal
  mysql_schema.sql            # Schema de base de datos
  ontap_instances.csv         # Lista de instancias ONTAP

src/
  collector.py                # Recolector principal
  ontap_client.py             # Cliente REST API ONTAP
  database.py                 # Operaciones MySQL
  mock_data.py                # Generador de datos simulados

grafana/
  snapmirror_dashboard.json   # Dashboard pre-configurado

run_collector.py              # Script principal
init_database.py              # Inicialización de BD
discover_ontap_clusters.py    # Descubrimiento interactivo
collector.service             # Servicio systemd
setup_lab.sh                  # Setup automatizado
```

## Instalación

### Requisitos
- Python 3.9+
- MySQL 8.0+
- Grafana 10.0+
- RHEL/Ubuntu/Windows

### Setup rápido (RHEL)

### Setup rápido (RHEL)

```bash
cd /root
git clone <repo> corme
cd corme
chmod +x setup_lab.sh
./setup_lab.sh
```

El script instala todo automáticamente.

### Setup manual

**1. Instalar dependencias Python:**
```bash
pip3 install -r requirements.txt
```

**2. Configurar MySQL:**

Editar credenciales en `config/config.yaml` y ejecutar:
```bash
mysql -u root -p < config/mysql_schema.sql
```

**3. Configurar clusters ONTAP:**

Opción A - Descubrimiento interactivo (recomendado):
```bash
python3 discover_ontap_clusters.py
```
Te guía paso a paso para añadir clusters, probar conexión, y descubrir relaciones.

Opción B - Modo mock (para testing):
```bash
python3 generate_mock_csv.py --num-instances 100
```

Opción C - Editar CSV manualmente:
```csv
name,ip_address,latitude,longitude,location_name,username,password
cluster1,192.168.0.101,40.4165,-3.7038,Madrid,admin,Netapp1!
```

**4. Configurar Grafana:**

- Añadir datasource MySQL apuntando a la BD
- Importar `grafana/snapmirror_dashboard.json`

## Uso

**Test rápido con datos simulados:**
```bash
python3 run_collector.py --mode mock --once
```

**Recolección real (una vez):**
```bash
python3 run_collector.py --mode real --once
```

**Modo continuo (cada 5 min):**
**Modo continuo (cada 5 min):**
```bash
python3 run_collector.py --mode real
```

### Como servicio (producción)

**Linux:**
```bash
sudo cp collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable collector
sudo systemctl start collector
sudo systemctl status collector
```

**Ver logs:**
```bash
sudo journalctl -u collector -f
```

## Configuración

El archivo `config/config.yaml` tiene todo:

```yaml
database:
  host: localhost
  user: snapmirror_user
  password: SnapMirror123!
  database: snapmirror_monitoring

collector:
  mode: real  # real o mock
  interval_seconds: 300  # 5 minutos
  stagger_delay_seconds: 0.2  # delay entre clusters
  timeout_seconds: 30

thresholds:
  warning: 900   # 15 min
  critical: 3600 # 1 hora
```

## Dashboard de Grafana

El dashboard tiene:

**Métricas superiores:**
- Total instances
- Total relations
- Warnings / Critical / Errors

**Mapa:**
- Marcador por cada cluster en su ubicación
- Color según peor estado
- Tamaño según número de relaciones
- Tooltip con detalles

**Tabla:**
- Todas las relaciones (no solo problemas)
- Ordenada por severidad
- Columnas: cluster, ubicación, source, destination, lag, estado

**Gráfica:**
- Evolución del lag últimas 24h
- Todas las relaciones

Refresh automático cada 30 segundos.

## Tiempos

Con 1400 instancias y 0.2s de delay:
- Tiempo por ciclo: ~5-7 minutos
- Se completa antes del siguiente intervalo (5 min)

Si tienes pocos clusters, puedes reducir el delay a 0.1s.

## Notas

- El collector usa asyncio para consultas concurrentes
- Hay delay escalonado para no saturar la red
- SSL verification está deshabilitado (`verify_ssl=False`) - cuidado en producción
- El histórico crece indefinidamente - considera limpieza periódica
- Modo mock es útil para testing sin clusters reales

## ¿Preguntas?

Si necesitas más info, ayuda con el deployment, o tienes algún problema, contáctame directamente.

---

**Autor:** NetApp Professional Services  
**Versión:** 1.0.0

