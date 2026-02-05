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

docs/
  GUIA_OPERACION.md          # Guía completa de operación

run_collector.py              # Script principal
init_database.py              # Inicialización de BD
discover_ontap_clusters.py    # Descubrimiento interactivo
remove_instance.py            # Gestión de instancias (alta/baja)
check_setup.py                # Verificación de configuración
test_mysql_connection.py      # Test de conexión MySQL
install_mysql_community.sh    # Instalación MySQL Community 8.0 (RECOMENDADO)
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

**Si el script falla al instalar MySQL:**
```bash
# Instalación MySQL Community 8.0
chmod +x install_mysql_community.sh
sudo ./install_mysql_community.sh
```

Este script descarga e instala MySQL 8.0 directamente desde Oracle, configura la base de datos, crea el usuario y carga el schema automáticamente.

**Verificar instalación:**
```bash
python3 check_setup.py
```

Este script verifica que todos los componentes estén correctamente configurados.

**Cargar schema y generar datos de prueba:**
```bash
# Cargar schema de base de datos
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql

# Generar datos mock para testing
python3 generate_mock_csv.py --num-instances 100

# Ejecutar collector en modo mock (una vez)
python3 run_collector.py --mode mock --once

# Verificar que hay datos
python3 check_setup.py
```

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
# Nota: Genera 'config/ontap_instances_mock.csv'
# Renombrar a 'ontap_instances.csv' o actualizar config.yaml
```

Opción C - Editar CSV manualmente:
```csv
name,ip_address,latitude,longitude,location_name,username,password
cluster1,192.168.0.101,40.4165,-3.7038,Madrid,admin,Netapp1!
```

**4. Configurar Grafana:**

Acceder a Grafana (http://localhost:3000 - user: admin / pass: admin)

**a) Añadir datasource MySQL:**
```
Configuración > Data sources > Add data source > MySQL

Configuraciones:
  Name: SnapMirror DB
  Host: localhost:3306        (o 127.0.0.1:3306 si da error)
  Database: snapmirror_monitoring
  User: snapmirror_user
  Password: SnapMirror123!
  
  Session timezone: (dejar vacío)
  
  ⚠️ IMPORTANTE: NO marcar "TLS/SSL" a menos que MySQL tenga SSL configurado
  
  [Save & Test]  ← Debe mostrar "Database Connection OK"
```

Si aparece error "failed to connect to server", ver sección Troubleshooting.

**b) Importar dashboard:**
```bash
Dashboards > Import > Upload JSON file
  → Seleccionar: grafana/snapmirror_dashboard.json
  → Elegir datasource: SnapMirror DB
  → Import
```

## Uso

### Scripts útiles

| Script | Descripción | Ejemplo |
|--------|-------------|---------|
| `run_collector.py` | Script principal del collector | `python3 run_collector.py --mode mock --once` |
| `check_setup.py` | Verificar configuración completa | `python3 check_setup.py` |
| `test_mysql_connection.py` | Probar conexión a MySQL (troubleshooting) | `python3 test_mysql_connection.py` |
| `remove_instance.py` | Gestionar instancias (baja/alta) | `python3 remove_instance.py --list` |
| `generate_mock_csv.py` | Generar datos de prueba | `python3 generate_mock_csv.py --num-instances 100` |
| `discover_ontap_clusters.py` | Descubrir clusters interactivamente | `python3 discover_ontap_clusters.py` |
| `init_database.py` | Inicializar base de datos | `python3 init_database.py` |

### Ejecución del collector

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

### Valores por defecto (Referencia Rápida)

| Parámetro | Valor | Ubicación |
|-----------|-------|----------|
| **Base de datos** | `snapmirror_monitoring` | `config/config.yaml` |
| **Usuario MySQL** | `snapmirror_user` | `config/config.yaml` |
| **Password MySQL** | `SnapMirror123!` | `config/config.yaml` |
| **Host MySQL** | `localhost` | `config/config.yaml` |
| **Puerto MySQL** | `3306` | `config/config.yaml` |
| **Grafana URL** | `http://localhost:3000` | - |
| **Grafana user** | `admin` | Por defecto |
| **Grafana pass** | `admin` | Por defecto |
| **CSV instancias** | `config/ontap_instances.csv` | - |
| **Intervalo colección** | `300s` (5 min) | `config/config.yaml` |
| **Threshold Warning** | `900s` (15 min) | `config/config.yaml` |
| **Threshold Critical** | `3600s` (60 min) | `config/config.yaml` |

### Archivo config/config.yaml

Todos los parámetros se configuran en `config/config.yaml`:

```yaml
database:
  host: localhost
  port: 3306
  user: snapmirror_user
  password: SnapMirror123!
  database: snapmirror_monitoring  # ← Nombre de la base de datos

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

**IMPORTANTE:** Asegúrate de configurar el datasource MySQL primero (ver sección Instalación paso 4).

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

## Troubleshooting

### Error en Grafana: "failed to connect to server" al configurar datasource

Si al configurar el datasource MySQL en Grafana aparece el error `[sqleng.connectionError] failed to connect to server`:

**🔍 Diagnóstico rápido:**
```bash
python3 test_mysql_connection.py
```
Este script te dirá exactamente qué configuración usar en Grafana.

**Soluciones paso a paso:**

**1. Verificar que MySQL está corriendo:**
```bash
sudo systemctl status mysqld
# o
sudo systemctl status mariadb
```

**2. Verificar que la base de datos existe:**
```bash
mysql -u root -p -e "SHOW DATABASES LIKE 'snapmirror_monitoring';"
```

**3. Verificar que el usuario existe y tiene permisos:**
```bash
mysql -u root -p
```
```sql
SELECT User, Host FROM mysql.user WHERE User = 'snapmirror_user';
SHOW GRANTS FOR 'snapmirror_user'@'localhost';
EXIT;
```

**4. Probar conexión manualmente:**
```bash
mysql -u snapmirror_user -pSnapMirror123! -h localhost snapmirror_monitoring -e "SELECT 1;"
```

**5. Si el comando anterior falla, recrear el usuario:**
```bash
mysql -u root -p
```
```sql
DROP USER IF EXISTS 'snapmirror_user'@'localhost';
CREATE USER 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**6. Configuración del datasource en Grafana:**

Asegúrate de usar estas configuraciones exactas:
```
Host: localhost:3306  (o 127.0.0.1:3306 si localhost no funciona)
Database: snapmirror_monitoring
User: snapmirror_user
Password: SnapMirror123!

⚠️ IMPORTANTE: NO marcar "Use TLS" a menos que MySQL esté configurado con SSL
```

**7. Si MySQL escucha solo en 127.0.0.1:**

En el datasource de Grafana, cambiar:
- De: `localhost:3306`
- A: `127.0.0.1:3306`

**8. Verificar logs de Grafana:**
```bash
sudo journalctl -u grafana-server -n 50 --no-pager
# o
sudo tail -f /var/log/grafana/grafana.log
```

### Error: "No se crearon las tablas esperadas" o MySQL no se instaló

Si el setup automático falla al instalar o configurar MySQL:

**Opción A - Instalación MySQL Community 8.0 (RECOMENDADO para RHEL sin suscripción):**
```bash
chmod +x install_mysql_community.sh
sudo ./install_mysql_community.sh
```
Este script descarga MySQL 8.0 directamente desde Oracle, no requiere suscripción RHEL, y configura todo automáticamente (base de datos, usuario, schema).

**Opción B - Instalación manual paso a paso:**

```bash
# 1. Instalar MySQL (requiere suscripción RHEL o usar install_mysql_community.sh)
sudo dnf install -y mysql-server mysql
# o en Ubuntu: sudo apt install -y mysql-server

# 2. Iniciar servicio
sudo systemctl start mysqld
sudo systemctl enable mysqld
sudo systemctl status mysqld

# 3. Verificar que MySQL está corriendo
sudo systemctl status mysqld

# 4. Configurar password de root (si es necesario)
sudo mysql -u root

# 5. Dentro de MySQL, ejecutar:
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';
FLUSH PRIVILEGES;
EXIT;

# 6. Crear base de datos y usuario
mysql -u root -pNetApp123!
```
```sql
CREATE DATABASE snapmirror_monitoring;
CREATE USER 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

```bash
# 7. Cargar el schema
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql

# 8. Verificar que se crearon las tablas
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
```

Deberías ver 4 tablas: `ontap_instances`, `snapmirror_relationships`, `snapmirror_status_current`, `snapmirror_status_history`

### Error: "Connection refused" al ejecutar collector

Verificar que MySQL está corriendo y acepta conexiones:
```bash
sudo systemctl status mysqld
mysql -u snapmirror_user -pSnapMirror123! -e "SELECT 1;"
```

### CSV de instancias no encontrado

Si usaste `generate_mock_csv.py`, el archivo se crea como `ontap_instances_mock.csv`:
```bash
cd config/
mv ontap_instances_mock.csv ontap_instances.csv
```

O editar `config.yaml` para apuntar al archivo correcto.

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

