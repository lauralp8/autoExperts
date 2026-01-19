# NetApp ONTAP Select - SnapMirror Monitor

Sistema de monitorización para relaciones SnapMirror en 1400+ instancias ONTAP Select distribuidas geográficamente. Dashboard en Grafana con visualización en mapa y alertas automáticas.

## 📋 Descripción

Solución completa que recolecta el estado de relaciones SnapMirror desde múltiples instancias ONTAP Select via REST API, almacena los datos en MySQL y presenta un dashboard interactivo en Grafana con:

- **Mapa geográfico** con código de colores por estado
- **Alertas automáticas** (Warning: >15min lag, Critical: >1h lag)
- **Recolección en cascada** para distribuir carga (cada 5 minutos)
- **Modo simulación** para testing sin acceso a ONTAP real

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────┐
│   1400 ONTAP Select Instances              │
│   (Distribuidas geográficamente)            │
└──────────────┬──────────────────────────────┘
               │ REST API (GET only)
               │ Recolección en cascada
               ▼
┌──────────────────────────────────────────────┐
│   Python Collector (asyncio)                │
│   - Polling cada 5 min                       │
│   - 0.2s delay entre instancias              │
│   - Modo mock/real                           │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│   MySQL Database                             │
│   - ontap_instances                          │
│   - snapmirror_relationships                 │
│   - snapmirror_status_current                │
│   - snapmirror_status_history                │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│   Grafana Dashboard                          │
│   - Geomap con markers coloreados            │
│   - Tabla de alertas activas                 │
│   - Gráficas de tendencia                    │
└──────────────────────────────────────────────┘
```

## 📁 Estructura del Proyecto

```
CORME/
├── config/
│   ├── config.yaml                 # Configuración principal
│   ├── mysql_schema.sql            # Schema de base de datos
│   └── ontap_instances.csv         # Lista de instancias ONTAP
│
├── src/
│   ├── collector.py                # Recolector principal
│   ├── ontap_client.py             # Cliente REST API ONTAP
│   ├── database.py                 # Operaciones MySQL
│   └── mock_data.py                # Generador de datos simulados
│
├── grafana/
│   └── snapmirror_dashboard.json   # Dashboard pre-configurado
│
├── logs/                           # Logs de ejecución
│
├── run_collector.py                # Script principal
├── init_database.py                # Inicialización de BD
├── generate_mock_csv.py            # Generador de CSV mock
├── requirements.txt                # Dependencias Python
└── README.md                       # Este archivo
```

## 🚀 Instalación y Setup

### 1. Requisitos Previos

- **Python 3.8+**
- **MySQL 5.7+ / MariaDB 10.3+**
- **Grafana 8.0+**
- Acceso a instancias ONTAP Select (modo real)

### 2. Instalar Dependencias

```powershell
# Clonar o ubicarse en el directorio del proyecto
cd "C:\Users\ca57934\OneDrive - NetApp Inc\Autocosas\CORME"

# Instalar dependencias Python
pip install -r requirements.txt
```

### 3. Configurar MySQL

Editar credenciales en [config/config.yaml](config/config.yaml):

```yaml
database:
  host: localhost
  port: 3306
  user: snapmirror_user
  password: TU_PASSWORD_AQUI
  database: snapmirror_monitoring
```

Inicializar base de datos:

```powershell
python init_database.py
```

### 4. Configurar Instancias ONTAP

**Opción A: Modo MOCK (para testing)**

Generar CSV de ejemplo con 100 instancias:

```powershell
python generate_mock_csv.py --num-instances 100 --output config/ontap_instances.csv
```

**Opción B: Modo REAL**

Editar [config/ontap_instances.csv](config/ontap_instances.csv) con tus instancias:

```csv
name,ip_address,latitude,longitude,location_name,username,password
ontap-madrid-01,10.1.1.100,40.4168,-3.7038,Madrid DC1,admin,Password123
ontap-barcelona-01,10.1.2.100,41.3851,2.1734,Barcelona DC1,admin,Password123
```

### 5. Configurar Grafana

1. **Añadir MySQL Datasource:**
   - Configuration → Data Sources → Add MySQL
   - Host: `localhost:3306`
   - Database: `snapmirror_monitoring`
   - User/Password: (según config.yaml)

2. **Importar Dashboard:**
   - Dashboards → Import → Upload JSON
   - Seleccionar: `grafana/snapmirror_dashboard.json`
   - Asignar datasource MySQL

## 🎯 Uso

### Modo MOCK (Testing)

Ejecutar una sola recolección con datos simulados:

```powershell
python run_collector.py --mode mock --once
```

Ejecutar en modo continuo (cada 5 minutos):

```powershell
python run_collector.py --mode mock
```

### Modo REAL (Producción)

Asegurarse de que [config/ontap_instances.csv](config/ontap_instances.csv) esté configurado correctamente.

Ejecución única:

```powershell
python run_collector.py --mode real --once
```

Ejecución continua (recomendado en producción):

```powershell
python run_collector.py --mode real
```

### Opciones Avanzadas

```powershell
# Ver ayuda completa
python run_collector.py --help

# Usar configuración personalizada
python run_collector.py --config mi_config.yaml

# Cambiar nivel de logging
python run_collector.py --log-level DEBUG
```

## 📊 Dashboard de Grafana

El dashboard incluye:

### 1. **Métricas Generales**
- Total de instancias ONTAP
- Total de relaciones SnapMirror
- Contador de Warnings
- Contador de Críticos

### 2. **Mapa Geográfico**
- Marcadores con ubicación de cada instancia
- Código de colores:
  - 🟢 Verde: OK (lag < 15 min)
  - 🟡 Amarillo: Warning (lag 15-60 min)
  - 🔴 Rojo: Critical (lag > 60 min)
  - 🟣 Púrpura: Error (relación no saludable)
- Tamaño del marcador = número de relaciones
- Tooltip con detalles al hacer hover

### 3. **Tabla de Alertas Activas**
- Solo muestra relaciones con problemas
- Ordenadas por severidad y lag
- Información detallada: source, destination, policy, estado

### 4. **Gráfica de Tendencia**
- Evolución del lag en últimas 24 horas
- Solo relaciones problemáticas
- Útil para identificar patrones

## ⚙️ Configuración Detallada

### Umbrales de Alerta

Editar en [config/config.yaml](config/config.yaml):

```yaml
thresholds:
  warning: 900    # 15 minutos
  critical: 3600  # 1 hora
```

### Intervalo de Recolección

```yaml
collector:
  interval_seconds: 300          # 5 minutos
  stagger_delay_seconds: 0.2     # 200ms entre instancias
  max_concurrent: 50             # Requests concurrentes
```

**Cálculo de tiempo total:**
- 1400 instancias × 0.2s = 280 segundos (~4.7 minutos)
- Permite completar el ciclo antes del siguiente intervalo (5 min)

### Modo Simulación

```yaml
mock:
  num_instances: 100
  num_relationships_per_instance: 3
  simulate_lag_probability: 0.3   # 30% con lag
  simulate_error_probability: 0.05 # 5% con errores
```

## 🔍 Troubleshooting

### Error: No se puede conectar a MySQL

```
Error conectando a MySQL: (2003, "Can't connect to MySQL server...")
```

**Solución:**
1. Verificar que MySQL esté corriendo
2. Comprobar credenciales en `config.yaml`
3. Verificar firewall/puertos

### Error: Timeout en ONTAP

```
Timeout conectando a 10.1.1.100
```

**Solución:**
1. Verificar conectividad de red
2. Aumentar timeout en `src/ontap_client.py`:
   ```python
   self.timeout = 60  # Aumentar a 60 segundos
   ```

### Dashboard de Grafana vacío

**Solución:**
1. Verificar que el collector se haya ejecutado al menos una vez
2. Comprobar que hay datos en MySQL:
   ```sql
   SELECT COUNT(*) FROM snapmirror_status_current;
   ```
3. Verificar datasource en Grafana

### Rendimiento lento con 1400 instancias

**Solución:**
1. Ajustar concurrencia máxima:
   ```yaml
   collector:
     max_concurrent: 100  # Aumentar si la red lo permite
   ```
2. Reducir delay entre instancias:
   ```yaml
   stagger_delay_seconds: 0.1  # Reducir a 100ms
   ```

## 📈 Optimizaciones para Producción

### 1. Ejecutar como Servicio

**Windows (PowerShell como Administrador):**

```powershell
# Crear tarea programada
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\...\CORME\run_collector.py --mode real"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount
Register-ScheduledTask -TaskName "SnapMirror-Collector" -Action $action -Trigger $trigger -Principal $principal
```

**Linux (systemd):**

```bash
# Crear /etc/systemd/system/snapmirror-collector.service
[Unit]
Description=SnapMirror Monitor Collector
After=network.target mysql.service

[Service]
Type=simple
User=ontap
WorkingDirectory=/opt/CORME
ExecStart=/usr/bin/python3 run_collector.py --mode real
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Gestión de Credenciales

**Usar variables de entorno en lugar de CSV:**

```python
# En ontap_client.py, leer desde vault o variables de entorno
import os
password = os.environ.get('ONTAP_PASSWORD')
```

### 3. Particionado de Tabla History

El schema ya incluye particionado por fecha para la tabla `snapmirror_status_history`. Agregar particiones cada mes:

```sql
ALTER TABLE snapmirror_status_history 
ADD PARTITION (
  PARTITION p_2026_02 VALUES LESS THAN (TO_DAYS('2026-03-01'))
);
```

### 4. Alerting en Grafana

Configurar notificaciones automáticas:

1. Notification channels → Add channel
2. En panel de Dashboard → Edit → Alert
3. Configurar condición: `when critical_count > 0`
4. Enviar a: Email, Slack, PagerDuty, etc.

## 🛡️ Seguridad

### Recomendaciones

1. **Credenciales:**
   - NO commitear `ontap_instances.csv` con passwords reales
   - Usar vault (HashiCorp Vault, Azure Key Vault, etc.)
   - Rotar passwords regularmente

2. **MySQL:**
   - Usuario con permisos mínimos (SELECT, INSERT, UPDATE)
   - Conexión SSL/TLS en producción

3. **REST API:**
   - Usuario ONTAP de solo lectura
   - Habilitar `verify_ssl=True` en producción

4. **Firewall:**
   - Restringir acceso a MySQL solo desde servidor collector
   - Limitar IPs que pueden consultar ONTAP

## 📝 Logs

Los logs se guardan en:
- `logs/collector.log` - Log detallado de todas las operaciones

Rotación automática (configurar con `logrotate` en Linux o Task Scheduler en Windows).

## 🤝 Contribución

Para añadir features o reportar bugs:

1. Crear rama de feature
2. Testear en modo mock
3. Documentar cambios
4. Crear Pull Request

## 📄 Licencia

Uso interno NetApp - Todos los derechos reservados

## 🆘 Soporte

Contacto: [Tu email o equipo de soporte]

---

**Versión:** 1.0.0  
**Última actualización:** Enero 2026  
**Autor:** NetApp Professional Services
