# NetApp ONTAP Select - SnapMirror Monitor

Sistema de monitorización para relaciones SnapMirror en 1400+ instancias ONTAP Select distribuidas geográficamente. Dashboard en Grafana con visualización en mapa y alertas automáticas.

## Descripción

Solución completa que recolecta el estado de relaciones SnapMirror desde múltiples instancias ONTAP Select via REST API, almacena los datos en MySQL y presenta un dashboard interactivo en Grafana con:

- **Mapa geográfico** con código de colores por estado
- **Alertas automáticas** (Warning: >15min lag, Critical: >1h lag, Error: unhealthy)
- **Recolección en cascada** para distribuir carga (cada 5 minutos)
- **Modo simulación** para testing sin acceso a ONTAP real
- **Histórico de datos** para análisis de tendencias
- **Vista completa** de todas las relaciones (no solo problemáticas)

## Arquitectura

```
+---------------------------------------------+
|   1400 ONTAP Select Instances              |
|   (Distribuidas geograficamente)            |
+----------------------+----------------------+
                       | REST API (GET only)
                       | Recoleccion en cascada
                       v
+----------------------------------------------+
|   Python Collector (asyncio)                |
|   - Polling cada 5 min                       |
|   - 0.2s delay entre instancias              |
|   - Modo mock/real                           |
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
|   - Geomap con markers coloreados            |
|   - Tabla con TODAS las relaciones           |
|   - Graficas de tendencia                    |
+----------------------------------------------+
```

## Estructura del Proyecto

```
CORME/
+-- config/
|   +-- config.yaml                 # Configuracion principal
|   +-- mysql_schema.sql            # Schema de base de datos
|   +-- ontap_instances.csv         # Lista de instancias ONTAP
|   +-- grafana-datasource.yml      # Configuracion datasource
|
+-- src/
|   +-- collector.py                # Recolector principal
|   +-- ontap_client.py             # Cliente REST API ONTAP
|   +-- database.py                 # Operaciones MySQL
|   +-- mock_data.py                # Generador de datos simulados
|
+-- grafana/
|   +-- snapmirror_dashboard.json   # Dashboard pre-configurado
|
+-- logs/                           # Logs de ejecucion
|
+-- run_collector.py                # Script principal
+-- init_database.py                # Inicializacion de BD
+-- generate_mock_csv.py            # Generador de CSV mock
+-- generate_production_csv.py      # Generador para produccion
+-- discover_ontap_clusters.py      # Descubrimiento interactivo
+-- collector.service               # Servicio systemd
+-- setup_lab.sh                    # Setup automatizado para Lab on Demand
+-- requirements.txt                # Dependencias Python
+-- README.md                       # Este archivo
```

## Despliegue en Cliente - Guia Rapida

Esta seccion describe el proceso completo para desplegar el sistema en un entorno de cliente.

### Tiempo estimado: 30-45 minutos

### Paso 1: Setup Inicial de Infraestructura (una sola vez)

En el servidor Linux del cliente donde se instalara el monitor:

```bash
# Clonar el proyecto
cd /root  # o el directorio que prefieras
git clone <url-del-repositorio> corme
cd corme

# Setup automatico para RHEL 8/9
chmod +x setup_lab.sh
./setup_lab.sh
```

El script instalara automaticamente:
- MySQL 8.0.40 con base de datos configurada
- Grafana 10.2.3 con servicio habilitado
- Python 3.12 y todas las dependencias
- Schema de base de datos inicializado

### Paso 2: Descubrir Clusters ONTAP del Cliente (interactivo)

```bash
python3 discover_ontap_clusters.py
```

Este script interactivo te guiara para:
1. Ingresar IP y credenciales de cada cluster ONTAP
2. Probar la conexion REST API automaticamente
3. Ingresar coordenadas geograficas para el mapa
4. Auto-descubrir todas las relaciones SnapMirror
5. Guardar la configuracion en config/ontap_instances.csv

**Nota:** Puedes ejecutar este script multiples veces. Opera en modo incremental (anade sin borrar clusters existentes).

### Paso 3: Verificar Recoleccion Manual

```bash
# Ejecutar una sola recoleccion para verificar
python3 run_collector.py --mode real --once
```

Salida esperada:
- Conexion exitosa a todos los clusters
- Relaciones SnapMirror descubiertas y almacenadas en MySQL
- Sin errores de conexion

### Paso 4: Configurar Dashboard de Grafana

1. **Acceder a Grafana:**
   - URL: http://<servidor>:3000
   - Usuario inicial: admin
   - Password inicial: admin (te pedira cambiarlo)

2. **Configurar MySQL Datasource:**
   - Menu: Configuration > Data sources > Add data source
   - Seleccionar: MySQL
   - Configuracion:
     - Host: `localhost:3306`
     - Database: `snapmirror_monitoring`
     - User: `snapmirror_user`
     - Password: `SnapMirror123!` (cambiar en produccion)
   - Click: **Save & Test** (debe mostrar "Database Connection OK")

3. **Importar Dashboard:**
   - Menu: Dashboards > Import > Upload JSON file
   - Seleccionar: `grafana/snapmirror_dashboard.json`
   - En "Select a MySQL data source": elegir el datasource creado
   - Click: **Import**

4. **Verificar Dashboard:**
   - Debe mostrar mapa con clusters descubiertos
   - Tabla con todas las relaciones SnapMirror
   - Contadores actualizados (Total Instances, Relations, Warnings, Critical, Errors)

### Paso 5: Habilitar Servicio Systemd (ejecucion continua)

```bash
# 1. Verificar ruta de Python en tu sistema
which python3.12  # o python3.9, segun lo que tengas instalado

# 2. Editar servicio si la ruta es diferente
vi collector.service
# Asegurar que ExecStart apunta a la ruta correcta:
# ExecStart=/usr/bin/python3 /root/corme/run_collector.py --mode real

# 3. Instalar y habilitar servicio
sudo cp collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable collector
sudo systemctl start collector

# 4. Verificar que esta corriendo
sudo systemctl status collector
```

### Paso 6: Verificacion Final

Despues de 5-10 minutos, verificar que todo funciona:

```bash
# Ver logs del servicio en tiempo real
sudo journalctl -u collector -f

# Verificar datos en MySQL
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e \
  "SELECT COUNT(*) as total_relaciones, 
          SUM(CASE WHEN alert_level='ok' THEN 1 ELSE 0 END) as ok,
          SUM(CASE WHEN alert_level='warning' THEN 1 ELSE 0 END) as warning,
          SUM(CASE WHEN alert_level='critical' THEN 1 ELSE 0 END) as critical
   FROM snapmirror_status_current;"

# Verificar Dashboard en Grafana
# Abrir navegador y confirmar que los datos se actualizan cada 30 segundos
```

**El sistema esta listo!** El collector recolectara datos cada 5 minutos automaticamente.

---

## Instalacion y Setup (Detallado)

### Requisitos Previos

- **Python 3.9+** (testeado con Python 3.12)
- **MySQL 8.0+** (compatible con 8.0.40)
- **Grafana 10.0+** (testeado con 10.2.3)
- Acceso a instancias ONTAP Select (modo real)
- Sistema operativo: RHEL 8/9, Ubuntu 20.04+, o Windows 10+

### Opcion 1: Setup Automatizado (Lab on Demand - RHEL)

Para entornos NetApp Lab on Demand con RHEL 8.x o 9.x:

```bash
# Descargar y ejecutar el script de setup
cd /root
git clone <tu-repo> corme
cd corme
chmod +x setup_lab.sh
./setup_lab.sh
```

El script instalara automaticamente:
- MySQL 8.0.40 (version correcta segun RHEL 8 o 9)
- Grafana 10.2.3
- Python 3.12 con todas las dependencias
- Base de datos inicializada
- Servicio systemd configurado

### Opcion 2: Instalacion Manual

#### 1. Instalar Dependencias Python

```bash
# Linux/Mac
cd /ruta/al/proyecto
pip3 install -r requirements.txt

# Windows
cd C:\Users\...\CORME
pip install -r requirements.txt
```

Dependencias clave:
- `aiohttp` - HTTP asíncrono para REST API
- `PyMySQL` - Conector MySQL
- `PyYAML` - Lectura de configuración
- `requests` - HTTP síncrono

#### 2. Configurar MySQL

Editar credenciales en `config/config.yaml`:

```yaml
database:
  host: localhost
  port: 3306
  user: snapmirror_user
  password: SnapMirror123!  # Cambiar en produccion
  database: snapmirror_monitoring
```

Inicializar base de datos:

```bash
# Crear usuario y base de datos
mysql -u root -p < config/mysql_schema.sql

# O usar el script Python
python3 init_database.py
```

#### 3. Configurar Instancias ONTAP

**Opcion A: Descubrimiento Interactivo (RECOMENDADO)**

Usar el script de descubrimiento para añadir clusters reales:

```bash
python3 discover_ontap_clusters.py
```

El script te guiara para:
1. Conectar a cada cluster ONTAP
2. Probar la conexion REST API
3. Ingresar coordenadas geograficas
4. Auto-descubrir relaciones SnapMirror
5. Actualizar el CSV incrementalmente

**Opcion B: Modo MOCK (para testing)**

Generar CSV de ejemplo con 100 instancias:

```bash
python3 generate_mock_csv.py --num-instances 100 --output config/ontap_instances.csv
```

**Opcion C: Modo REAL (manual)**

Editar `config/ontap_instances.csv` directamente:

```csv
name,ip_address,latitude,longitude,location_name,username,password
cluster1,192.168.0.101,40.4165,-3.7038,Madrid,admin,Netapp1!
cluster2,192.168.0.102,41.3888,2.159,Barcelona,admin,Netapp1!
cluster3,192.168.0.103,36.5298,6.2947,Cadiz,admin,Netapp1!
```

#### 4. Configurar Grafana

**Paso 1: Añadir MySQL Datasource**

```bash
# Acceder a Grafana (por defecto: http://localhost:3000)
# Usuario/password inicial: admin/admin
```

En Grafana:
1. Configuration > Data sources > Add data source
2. Seleccionar MySQL
3. Configurar:
   - **Host:** localhost:3306
   - **Database:** snapmirror_monitoring
   - **User:** snapmirror_user
   - **Password:** SnapMirror123!
4. Click "Save & Test" (debe mostrar "Database Connection OK")

**Paso 2: Importar Dashboard**

1. Dashboards > Import > Upload JSON file
2. Seleccionar: `grafana/snapmirror_dashboard.json`
3. En "Select a MySQL data source", elegir el datasource creado
4. Click "Import"

El dashboard mostrara:
- Mapa geografico con todas las instancias
- Contadores: Total Instances, Relations, Warnings, Critical, Errors
- Tabla con TODAS las relaciones (ordenadas por severidad)
- Grafica de tendencia de lag (ultimas 24h)

## Uso

### Ejecucion Rapida

```bash
# Prueba con datos simulados (una sola recoleccion)
python3 run_collector.py --mode mock --once

# Recoleccion de clusters reales (una vez)
python3 run_collector.py --mode real --once

# Modo continuo (cada 5 minutos)
python3 run_collector.py --mode real
```

### Modo MOCK (Testing)

Ejecutar una sola recoleccion con datos simulados:

```bash
python3 run_collector.py --mode mock --once
```

Salida esperada:
```
============================================================
SnapMirror Monitor - Collector
============================================================
Modo MOCK: 100 instancias simuladas
Iniciando recoleccion en cascada: 100 instancias
[1/100] Recolectando mock-instance-001...
...
Recoleccion completada en 23.45 segundos
Estadisticas:
  - Total instancias: 100
  - Total relaciones: 300
  - OK: 210
  - WARNING: 60
  - CRITICAL: 25
  - ERROR: 5
============================================================
```

Ejecutar en modo continuo (cada 5 minutos):

```bash
python3 run_collector.py --mode mock
```

### Modo REAL (Produccion)

Asegurarse de que `config/ontap_instances.csv` este configurado correctamente.

**Ejecucion unica (testing):**

```bash
python3 run_collector.py --mode real --once
```

Salida esperada:
```
[1/3] Recolectando cluster1...
[2/3] Recolectando cluster2...
[3/3] Recolectando cluster3...
Recoleccion completada en 3.49 segundos
  - Total relaciones: 22
  - OK: 21
  - ERROR: 1
```

**Ejecucion continua (produccion):**

```bash
python3 run_collector.py --mode real
```

El collector:
1. Recolecta datos de todas las instancias
2. Espera 5 minutos
3. Repite el ciclo indefinidamente

Para detener: `Ctrl+C`

### Ejecutar como Servicio (RECOMENDADO en produccion)

#### Linux (systemd)

El proyecto incluye `collector.service` pre-configurado.

**Instalacion:**

```bash
# 1. Editar el servicio si es necesario
vi collector.service

# Asegurar que ExecStart usa la ruta correcta de Python:
# ExecStart=/usr/local/bin/python3.12 /root/corme/run_collector.py --mode real

# 2. Copiar a systemd
sudo cp collector.service /etc/systemd/system/

# 3. Dar permisos al script
chmod 644 run_collector.py

# 4. Habilitar y arrancar
sudo systemctl daemon-reload
sudo systemctl enable collector
sudo systemctl start collector

# 5. Verificar estado
sudo systemctl status collector

# 6. Ver logs en tiempo real
sudo journalctl -u collector -f
```

**Gestion del servicio:**

```bash
# Detener
sudo systemctl stop collector

# Reiniciar
sudo systemctl restart collector

# Ver ultimos logs
sudo journalctl -u collector -n 100

# Deshabilitar arranque automatico
sudo systemctl disable collector
```

#### Windows (Task Scheduler)

Crear tarea programada que se ejecute al inicio:

```powershell
# PowerShell como Administrador
$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "C:\path\to\CORME\run_collector.py --mode real" `
    -WorkingDirectory "C:\path\to\CORME"

$trigger = New-ScheduledTaskTrigger -AtStartup

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "SnapMirror-Collector" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description "Recoleccion continua de SnapMirror"
```

### Opciones Avanzadas

```bash
# Ver ayuda completa
python3 run_collector.py --help

# Usar configuracion personalizada
python3 run_collector.py --config mi_config.yaml --mode real

# Cambiar nivel de logging
python3 run_collector.py --log-level DEBUG --mode real --once
```

## Dashboard de Grafana

El dashboard incluye:

### 1. Metricas Generales (fila superior)

- **Total ONTAP Instances** - Numero total de clusters monitorizados
- **Total SnapMirror Relations** - Numero total de relaciones
- **Warnings** - Relaciones con lag entre 15-60 minutos (fondo naranja)
- **Critical** - Relaciones con lag > 60 minutos (fondo rojo)
- **Errors** - Relaciones unhealthy o pausadas (fondo morado)

### 2. Mapa Geografico

Visualizacion interactiva con:
- **Marcadores** en coordenadas de cada cluster
- **Codigo de colores:**
  - Verde: OK (lag < 15 min)
  - Amarillo: Warning (lag 15-60 min)
  - Rojo: Critical (lag > 60 min)
  - Morado: Error (unhealthy/paused)
- **Tamaño del marcador** proporcional al numero de relaciones
- **Tooltip** con detalles al hacer hover:
  - Nombre del cluster
  - Ubicacion
  - Total de relaciones
  - Estado general

### 3. Tabla: All SnapMirror Relationships - Status Overview

Muestra **TODAS** las relaciones (no solo las problematicas):
- Ordenadas por severidad (Critical > Error > Warning > OK)
- Columnas:
  - instance_name - Nombre del cluster
  - location_name - Ubicacion geografica
  - source_path - SVM:volumen origen
  - destination_path - SVM:volumen destino
  - policy - Politica SnapMirror
  - state - Estado (snapmirrored, paused, uninitialized, etc.)
  - health_status - healthy / unhealthy
  - lag_minutes - Lag en minutos con 2 decimales
  - alert_level - OK, warning, critical, error (con color de fondo)
  - last_check - Timestamp de ultima recoleccion

Limite: 500 relaciones (configurable en el JSON)

### 4. Grafica: Lag Trend - Last 24 Hours (All Relations)

Evolucion del lag en las ultimas 24 horas:
- Muestra TODAS las relaciones
- Lineas de colores por cada relacion
- Util para:
  - Identificar patrones
  - Detectar tendencias
  - Ver historico de problemas resueltos
  - Analizar degradacion gradual

### Refresh Rate

- Dashboard: 30 segundos (configurable arriba a la derecha)
- Collector: 5 minutos (configurable en config.yaml)
- Datos historicos: Indefinido (tabla history sin limite de retention)

## Configuracion Detallada

### Archivo config.yaml

```yaml
# Base de Datos MySQL
database:
  host: localhost
  port: 3306
  user: snapmirror_user
  password: SnapMirror123!
  database: snapmirror_monitoring

# Configuracion de Recoleccion
collector:
  mode: mock  # mock o real
  interval_seconds: 300  # 5 minutos entre recolecciones
  stagger_delay_seconds: 0.2  # 200ms entre cada instancia
  timeout_seconds: 30  # Timeout para cada peticion REST API
  max_concurrent: 50  # Peticiones concurrentes maximas

# Umbrales de Alerta (en segundos)
thresholds:
  warning: 900   # 15 minutos
  critical: 3600 # 1 hora

# Simulacion (modo mock)
mock:
  num_instances: 100
  num_relationships_per_instance: 3
  simulate_lag_probability: 0.3  # 30% tendran lag
  simulate_error_probability: 0.05  # 5% con errores

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: logs/collector.log
```

### Calculo de Tiempos

Con la configuracion por defecto:
- **1400 instancias** x **0.2s delay** = **280 segundos** (~4.7 minutos)
- Permite completar el ciclo antes del siguiente intervalo (5 min)
- Cada instancia toma ~1-2s (peticion API + procesamiento DB)
- Tiempo total por ciclo: ~5-7 minutos

### Ajustes para Optimizar Rendimiento

**Para reducir tiempo de recoleccion:**

```yaml
collector:
  stagger_delay_seconds: 0.1  # Reducir a 100ms
  max_concurrent: 100  # Aumentar concurrencia
```

**Para clusters lentos o redes con alta latencia:**

```yaml
collector:
  timeout_seconds: 60  # Aumentar timeout
  stagger_delay_seconds: 0.5  # Mas tiempo entre peticiones
```

### Niveles de Alerta

El sistema clasifica cada relacion en uno de estos niveles:

1. **OK** (verde)
   - `healthy: true`
   - `lag_seconds < 900` (< 15 min)
   - `state: snapmirrored`

2. **WARNING** (amarillo)
   - `healthy: true`
   - `900 <= lag_seconds < 3600` (15 min - 1 hora)

3. **CRITICAL** (rojo)
   - `healthy: true`
   - `lag_seconds >= 3600` (>= 1 hora)

4. **ERROR** (morado)
   - `healthy: false` (independientemente del lag)
   - Estados problematicos: paused, uninitialized, broken-off, etc.

### Base de Datos

**Tablas principales:**

- `ontap_instances` - Clusters ONTAP
- `snapmirror_relationships` - Relaciones SnapMirror
- `snapmirror_status_current` - Estado actual (1 fila por relacion)
- `snapmirror_status_history` - Historico de recolecciones

**Vistas para Grafana:**

- `v_snapmirror_map` - Datos agregados por cluster para el mapa
- `v_snapmirror_detail` - Datos detallados para las tablas

**Consultas utiles:**

```sql
-- Ver relaciones problematicas
SELECT * FROM v_snapmirror_detail 
WHERE alert_level IN ('warning', 'critical', 'error');

-- Lag promedio por cluster
SELECT instance_name, AVG(lag_minutes) as avg_lag
FROM v_snapmirror_detail
GROUP BY instance_name;

-- Historico de una relacion especifica
SELECT collected_at, lag_seconds/60 as lag_min, alert_level
FROM snapmirror_status_history
WHERE relationship_id = 123
ORDER BY collected_at DESC
LIMIT 100;
```

## Troubleshooting

### Error: No se puede conectar a MySQL

```
Error conectando a MySQL: (2003, "Can't connect to MySQL server...")
```

**Solucion:**
1. Verificar que MySQL este corriendo:
   ```bash
   sudo systemctl status mysqld  # RHEL/CentOS
   sudo systemctl status mysql   # Ubuntu
   ```
2. Comprobar credenciales en `config/config.yaml`
3. Verificar que el usuario existe y tiene permisos:
   ```sql
   SHOW GRANTS FOR 'snapmirror_user'@'localhost';
   ```
4. Verificar firewall/puertos (3306)

### Error: Timeout en ONTAP

```
Timeout conectando a 192.168.0.101
```

**Solucion:**
1. Verificar conectividad de red:
   ```bash
   ping 192.168.0.101
   curl -k https://192.168.0.101/api/cluster
   ```
2. Aumentar timeout en `config.yaml`:
   ```yaml
   collector:
     timeout_seconds: 60  # Aumentar de 30 a 60
   ```
3. Verificar credenciales en `ontap_instances.csv`

### Error: 400 Bad Request desde ONTAP API

```
Error obteniendo relaciones SnapMirror: 400 Bad Request
```

**Solucion:**
Este error ocurre cuando se piden campos no soportados por la version de ONTAP.

El codigo ya esta optimizado con la lista minima de campos:
```
uuid,source.path,destination.path,policy.name,state,healthy,lag_time,transfer.state,transfer.end_time
```

Si persiste, verificar version de ONTAP (debe ser 9.6+).

### Error: Data truncated for column 'last_transfer_end_timestamp'

```
(1265, "Data truncated for column 'last_transfer_end_timestamp' at row 1")
```

**Solucion:**
Este error ya esta resuelto en la version actual. El codigo convierte timestamps ISO 8601 a Unix timestamp (BIGINT).

Si aparece, verificar que tienes la ultima version de `src/collector.py`.

### Dashboard de Grafana vacio

**Solucion:**
1. Verificar que el collector se haya ejecutado al menos una vez:
   ```bash
   python3 run_collector.py --mode real --once
   ```

2. Comprobar que hay datos en MySQL:
   ```sql
   USE snapmirror_monitoring;
   SELECT COUNT(*) FROM snapmirror_status_current;
   SELECT COUNT(*) FROM ontap_instances;
   ```

3. Verificar datasource en Grafana:
   - Configuration > Data sources
   - Click en MySQL datasource
   - Click "Save & Test"
   - Debe mostrar "Database Connection OK"

4. Verificar query manual en Grafana Explore:
   ```sql
   SELECT * FROM v_snapmirror_map LIMIT 10;
   ```

### Servicio systemd falla con "exit code 203"

```
Main PID: 79903 (code=exited, status=203/EXEC)
```

**Solucion:**
Error 203 indica que systemd no puede ejecutar el binario.

1. Verificar ruta de Python:
   ```bash
   which python3.12
   # Salida: /usr/local/bin/python3.12
   ```

2. Editar `/etc/systemd/system/collector.service`:
   ```ini
   ExecStart=/usr/local/bin/python3.12 /root/corme/run_collector.py --mode real
   ```
   (usar la ruta exacta del paso 1)

3. Dar permisos al script:
   ```bash
   chmod 644 /root/corme/run_collector.py
   ```

4. Recargar y reiniciar:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart collector
   sudo systemctl status collector
   ```

### Lag siempre aparece en 0

**Solucion:**
El problema estaba en versiones antiguas que no solicitaban el campo `lag_time` al API.

Verificar que `src/ontap_client.py` incluye `lag_time` en la peticion:
```python
params = {
    'fields': 'uuid,source.path,destination.path,policy.name,state,healthy,lag_time,transfer.state,transfer.end_time',
    ...
}
```

Si falta, actualizar a la ultima version del codigo.

### Rendimiento lento con 1400 instancias

**Solucion:**

1. Ajustar concurrencia maxima en `config.yaml`:
   ```yaml
   collector:
     max_concurrent: 100  # Aumentar si la red lo permite
   ```

2. Reducir delay entre instancias:
   ```yaml
   stagger_delay_seconds: 0.1  # Reducir de 0.2 a 0.1
   ```

3. Verificar recursos del servidor:
   ```bash
   top
   htop
   free -h
   ```

4. Considerar ejecutar multiples collectors en paralelo (split de CSV)

## Optimizaciones para Produccion

### 1. Retention de Datos Historicos

Por defecto, la tabla `snapmirror_status_history` crece indefinidamente. Para produccion, implementar limpieza periodica:

```sql
-- Crear evento para limpiar datos mayores a 90 dias
CREATE EVENT cleanup_old_history
ON SCHEDULE EVERY 1 DAY
DO
  DELETE FROM snapmirror_status_history 
  WHERE collected_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### 2. Indices Adicionales (opcional)

Si tienes miles de relaciones, estos indices pueden ayudar:

```sql
-- Indice para busquedas por cluster
CREATE INDEX idx_instance_alert ON snapmirror_status_current(instance_id, alert_level);

-- Indice para queries historicas por fecha
CREATE INDEX idx_history_date ON snapmirror_status_history(collected_at, alert_level);
```

### 3. Backup de Base de Datos

Script de backup automatico:

```bash
#!/bin/bash
# backup_db.sh

BACKUP_DIR=/var/backups/snapmirror
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE=$BACKUP_DIR/snapmirror_$DATE.sql.gz

mkdir -p $BACKUP_DIR

mysqldump -u snapmirror_user -pSnapMirror123! \
  snapmirror_monitoring | gzip > $BACKUP_FILE

# Mantener solo ultimos 30 dias
find $BACKUP_DIR -name "snapmirror_*.sql.gz" -mtime +30 -delete

echo "Backup completado: $BACKUP_FILE"
```

Añadir a cron:
```bash
# Backup diario a las 2 AM
0 2 * * * /root/scripts/backup_db.sh
```

### 4. Alerting en Grafana

Configurar alertas automaticas:

1. **Email Notifications:**
   - Alerting > Notification channels > Add channel
   - Type: Email
   - Addresses: tu-equipo@netapp.com

2. **Alerta de Criticos:**
   - En Dashboard > Panel "Critical"
   - Edit > Alert
   - Condicion: `WHEN last() OF query(A) IS ABOVE 0`
   - For: 5m (esperar 5 min antes de alertar)
   - Send to: Email

3. **Alerta de Collector Detenido:**
   - Crear panel nuevo con query:
     ```sql
     SELECT TIMESTAMPDIFF(MINUTE, MAX(collected_at), NOW()) as minutes_since_last
     FROM snapmirror_status_current;
     ```
   - Alert cuando `minutes_since_last > 10`

### 5. Monitoreo del Collector

Script de healthcheck:

```bash
#!/bin/bash
# healthcheck.sh

# Verificar que el servicio esta corriendo
if ! systemctl is-active --quiet collector; then
    echo "ERROR: Servicio collector detenido"
    systemctl start collector
    exit 1
fi

# Verificar ultima recoleccion (debe ser < 10 minutos)
LAST_COLLECTION=$(mysql -u snapmirror_user -pSnapMirror123! \
  -D snapmirror_monitoring -N -e \
  "SELECT TIMESTAMPDIFF(MINUTE, MAX(collected_at), NOW()) FROM snapmirror_status_current;")

if [ "$LAST_COLLECTION" -gt 10 ]; then
    echo "ERROR: Ultima recoleccion hace $LAST_COLLECTION minutos"
    systemctl restart collector
    exit 1
fi

echo "OK: Collector funcionando correctamente"
exit 0
```

Añadir a cron cada 5 minutos:
```bash
*/5 * * * * /root/scripts/healthcheck.sh >> /var/log/collector-health.log 2>&1
```

### 6. Gestion de Credenciales Segura

Para produccion, NO guardar passwords en CSV. Usar variables de entorno:

```bash
# Crear archivo .env (no commitear al repo)
export ONTAP_DEFAULT_USER="admin"
export ONTAP_DEFAULT_PASSWORD="SecurePassword123!"
```

Modificar `discover_ontap_clusters.py` para leer de .env:

```python
import os
default_user = os.getenv('ONTAP_DEFAULT_USER', 'admin')
default_password = os.getenv('ONTAP_DEFAULT_PASSWORD')
```

### 7. Alta Disponibilidad

Para entornos criticos:

1. **Collector redundante:**
   - Ejecutar 2 instancias del collector en servidores diferentes
   - Ambos escriben a la misma BD (no hay conflicto)
   - Si uno falla, el otro continua

2. **MySQL replication:**
   - Master-Slave para backup automatico
   - Master-Master para HA completa

3. **Grafana HA:**
   - Load balancer delante de multiples instancias Grafana
   - Todas apuntan a la misma MySQL

## Seguridad

### Recomendaciones

1. **Credenciales:**
   - NO commitear `ontap_instances.csv` con passwords reales al repositorio
   - Añadir `ontap_instances.csv` a `.gitignore`
   - Usar vault (HashiCorp Vault, Azure Key Vault, CyberArk, etc.)
   - Rotar passwords regularmente (cada 90 dias)

2. **MySQL:**
   - Usuario con permisos minimos (SELECT, INSERT, UPDATE, DELETE)
   - NO dar permisos DROP, CREATE, ALTER
   - Conexion SSL/TLS en produccion:
     ```yaml
     database:
       ssl_ca: /path/to/ca-cert.pem
       ssl_cert: /path/to/client-cert.pem
       ssl_key: /path/to/client-key.pem
     ```

3. **REST API ONTAP:**
   - Crear usuario de solo lectura en ONTAP:
     ```
     security login create -user-or-group-name snapmirror-monitor \
       -application http -authentication-method password \
       -role readonly
     ```
   - Habilitar `verify_ssl=True` en produccion (requiere certificados validos)

4. **Firewall:**
   - Restringir acceso a MySQL solo desde servidor collector
   - Limitar IPs que pueden consultar ONTAP API
   - Usar VPN para acceso a Grafana desde fuera de la red corporativa

5. **Logs:**
   - NO loguear passwords (ya implementado en el codigo)
   - Rotar logs regularmente
   - Proteger archivos de log (chmod 640)

## Logs y Debugging

### Ubicacion de Logs

- **Collector:** `logs/collector.log`
- **Systemd:** `journalctl -u collector -f`
- **MySQL:** `/var/log/mysql/error.log`
- **Grafana:** `/var/log/grafana/grafana.log`

### Niveles de Logging

Cambiar en `config.yaml`:

```yaml
logging:
  level: DEBUG  # DEBUG, INFO, WARNING, ERROR
```

- **DEBUG:** Toda la informacion (peticiones API, queries SQL, etc.)
- **INFO:** Operaciones normales (recolecciones, resultados)
- **WARNING:** Problemas no criticos (timeouts, datos faltantes)
- **ERROR:** Errores graves (fallos de conexion, crashes)

### Ejemplos de Logs

**Recoleccion exitosa:**
```
2026-01-20 07:45:50 - src.collector - INFO - [1/3] Recolectando cluster1...
2026-01-20 07:45:51 - ontap_client - INFO - Obtenidas 1 relaciones de 192.168.0.101
2026-01-20 07:45:51 - src.collector - INFO - OK cluster1: 1 relaciones procesadas
```

**Error de conexion:**
```
2026-01-20 07:45:50 - ontap_client - ERROR - Error conectando a 192.168.0.105: Timeout
2026-01-20 07:45:50 - src.collector - ERROR - Error procesando cluster5: Connection timeout
```

**Modo DEBUG (muy verbose):**
```
2026-01-20 07:45:50 - ontap_client - DEBUG - GET https://192.168.0.101/api/snapmirror/relationships
2026-01-20 07:45:50 - ontap_client - DEBUG - Query params: {'fields': 'uuid,source.path,...'}
2026-01-20 07:45:51 - database - DEBUG - INSERT INTO snapmirror_status_current VALUES (...)
```

### Rotacion de Logs

**Linux (logrotate):**

Crear `/etc/logrotate.d/snapmirror-collector`:

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

Script para limpiar logs viejos:

```powershell
# Mantener solo ultimos 30 dias
$logDir = "C:\path\to\CORME\logs"
Get-ChildItem -Path $logDir -Filter "*.log" | 
  Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | 
  Remove-Item
```

## Contribucion

Para añadir features o reportar bugs:

1. Crear rama de feature
2. Testear en modo mock antes de desplegar
3. Documentar cambios en CHANGELOG.md
4. Crear Pull Request con descripcion detallada

## Licencia

Uso interno NetApp - Todos los derechos reservados

## Soporte

Para soporte tecnico o consultas:
- Email: [tu-email@netapp.com]
- Slack: #snapmirror-monitoring
- Wiki: [URL de documentacion interna]

---

**Version:** 1.0.0  
**Ultima actualizacion:** Enero 2026  
**Autor:** NetApp Professional Services  
**Testeado en:**
- RHEL 8.10 / RHEL 9.3
- Python 3.9 / 3.12
- MySQL 8.0.40
- Grafana 10.2.3
- ONTAP 9.6+
