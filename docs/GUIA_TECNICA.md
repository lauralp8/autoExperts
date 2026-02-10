# Guía Técnica - SnapMirror Monitor

## Índice

1. [Descripción de Scripts Python](#descripción-de-scripts-python)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Guía de Demostración](#guía-de-demostración)
4. [Mejoras Potenciales para Grafana](#mejoras-potenciales-para-grafana)
5. [Casos de Uso Avanzados](#casos-de-uso-avanzados)

---

## Descripción de Scripts Python

### Scripts Principales

#### `run_collector.py` - Script Principal del Collector

**Propósito:** Orquesta la recolección de datos de SnapMirror desde todos los clusters ONTAP configurados.

**Qué hace:**
1. Lee la configuración desde `config/config.yaml`
2. Carga la lista de instancias ONTAP desde el CSV
3. Para cada instancia:
   - Conecta via REST API
   - Obtiene todas las relaciones SnapMirror
   - Extrae estado, lag, health status
   - Calcula nivel de alerta (ok/warning/critical/error)
4. Guarda los datos en MySQL (tablas current e history)
5. En modo continuo, repite cada N segundos (configurable)

**Parámetros:**
```bash
python3 run_collector.py --mode mock --once    # Una ejecución, datos simulados
python3 run_collector.py --mode real --once    # Una ejecución, datos reales
python3 run_collector.py --mode real           # Continuo (cada 5 min)
python3 run_collector.py --help                # Ver todas las opciones
```

**Flujo de datos:**
```
CSV instancias → Collector → REST API ONTAP → Parser → MySQL → Grafana
```

---

#### `check_setup.py` - Verificación de Configuración

**Propósito:** Diagnostica el estado completo del sistema antes de ejecutar el collector.

**Qué verifica:**
1. **Archivos requeridos:**
   - `config/config.yaml` existe y es válido
   - `config/mysql_schema.sql` existe
   - Scripts Python existen
   - Dashboard JSON existe

2. **Configuración:**
   - YAML válido
   - Parámetros de conexión MySQL
   - Thresholds configurados

3. **Dependencias Python:**
   - PyMySQL instalado
   - PyYAML instalado
   - requests instalado

4. **Base de datos MySQL:**
   - Conexión exitosa
   - Tablas creadas (4 tablas esperadas)
   - Permisos correctos

5. **Grafana:**
   - Servicio corriendo
   - Puerto 3000 accesible

**Uso:**
```bash
python3 check_setup.py
```

**Salida ejemplo:**
```
✓ Archivos requeridos
✓ Configuración
✓ Dependencias Python
✓ Base de datos MySQL
✓ Grafana

✓ SISTEMA LISTO
```

---

#### `discover_ontap_clusters.py` - Descubrimiento Interactivo

**Propósito:** Asistente guiado para añadir nuevos clusters ONTAP al monitoreo.

**Qué hace:**
1. Solicita IP/hostname del cluster
2. Solicita credenciales (usuario/password)
3. Prueba conexión REST API
4. Obtiene información del cluster:
   - Nombre del cluster
   - UUID
   - Versión ONTAP
5. Descubre relaciones SnapMirror existentes
6. Solicita coordenadas geográficas (para el mapa)
7. Añade la entrada al CSV de instancias

**Flujo interactivo:**
```
Usuario → IP → Credenciales → Test conexión → Descubrir SM → Guardar CSV
```

**Uso:**
```bash
python3 discover_ontap_clusters.py
```

**Ventaja:** No requiere conocimiento técnico del formato CSV, guía paso a paso.

---

#### `generate_mock_csv.py` - Generador de Datos de Prueba

**Propósito:** Crea instancias ONTAP ficticias para demos y testing.

**Qué genera:**
- N instancias con nombres aleatorios (ej: "ONTAP-Madrid-001")
- IPs ficticias en rango 10.x.x.x
- Coordenadas distribuidas por España
- Credenciales de prueba

**Parámetros:**
```bash
python3 generate_mock_csv.py --num-instances 50    # 50 instancias
python3 generate_mock_csv.py --num-instances 1400  # Escala real
```

**Salida:** `config/ontap_instances_mock.csv`

**Nota:** El collector en modo `--mode mock` genera datos SnapMirror simulados para estas instancias.

---

#### `init_database.py` - Inicialización de Base de Datos

**Propósito:** Crea la estructura de base de datos desde cero.

**Qué hace:**
1. Conecta a MySQL como root
2. Crea la base de datos `snapmirror_monitoring`
3. Crea las 4 tablas principales
4. Crea índices para optimizar queries
5. Crea el usuario de aplicación con permisos

**Cuándo usarlo:**
- Primera instalación
- Después de un reset de MySQL
- Si las tablas se corrompieron

**Uso:**
```bash
python3 init_database.py
```

---

#### `test_mysql_connection.py` - Test de Conexión MySQL

**Propósito:** Diagnostica problemas de conexión a MySQL.

**Qué prueba:**
1. Resolución de hostname (localhost vs 127.0.0.1)
2. Puerto 3306 abierto
3. Credenciales válidas
4. Permisos sobre la base de datos
5. Tablas accesibles

**Uso:**
```bash
python3 test_mysql_connection.py
```

**Salida:** Indica exactamente qué configuración usar en Grafana.

---

#### `remove_instance.py` - Gestión de Instancias

**Propósito:** Administrar el inventario de clusters ONTAP.

**Funciones:**
```bash
python3 remove_instance.py --list              # Listar todas las instancias
python3 remove_instance.py --remove CLUSTER01  # Dar de baja un cluster
python3 remove_instance.py --activate CLUSTER01 # Reactivar un cluster
python3 remove_instance.py --status            # Ver estado de cada una
```

**Nota:** "Dar de baja" no borra datos, solo marca `is_active=FALSE` en la BD.

---

#### `cleanup_history.py` - Limpieza de Histórico

**Propósito:** Eliminar registros antiguos de la tabla `snapmirror_status_history` para controlar el crecimiento de la base de datos.

**Por qué es necesario:**
- El histórico crece ~288 registros/día por relación (intervalos de 5 min)
- Con 100 relaciones = ~28,800 registros/día = ~864,000 registros/mes
- Sin limpieza, la tabla puede crecer a millones de registros

**Uso:**
```bash
# Ver estadísticas del histórico (sin borrar nada)
python3 cleanup_history.py

# Simular borrado (ver qué se borraría)
python3 cleanup_history.py --days 30 --dry-run

# Borrar registros con más de 30 días
python3 cleanup_history.py --days 30

# Mantener solo última semana
python3 cleanup_history.py --days 7
```

**Ejemplo de salida:**
```
✓ Conectado a MySQL

============================================================
ESTADÍSTICAS DEL HISTÓRICO
============================================================
  Total registros:      1.234.567
  Registro más antiguo: 2025-12-01 10:30:00
  Registro más reciente:2026-02-10 15:45:00
  Media registros/día:  28.800
============================================================

⚠️  Registros a eliminar (>30 días): 456.789

¿Estás seguro de que quieres borrar estos registros?
Escribe 'SI' para confirmar: SI

============================================================
✓ LIMPIEZA COMPLETADA
  Registros eliminados: 456.789
============================================================
```

**Recomendaciones:**
- Ejecutar semanalmente con `--days 30` (mantener último mes)
- Para dashboards de trending, 30 días suele ser suficiente
- Ejecutar en horario de bajo uso

**Automatizar con cron:**
```bash
# Añadir a crontab (ejecutar domingos a las 3 AM)
0 3 * * 0 cd /root/corme && python3 cleanup_history.py --days 30 --yes >> /var/log/corme_cleanup.log 2>&1
```

---

### Módulos Internos (`src/`)

#### `src/collector.py` - Motor de Recolección

**Clase principal:** `SnapMirrorCollector`

**Funciones disponibles:**

| Función | Descripción |
|---------|-------------|
| `__init__(config_path)` | Inicializa collector con archivo de configuración |
| `setup()` | Configura conexiones DB y carga instancias |
| `_load_config(path)` | Carga configuración desde YAML |
| `_load_instances_from_csv(path)` | Carga instancias desde CSV |
| `_register_instances()` | Registra todas las instancias en BD |
| `_collect_from_instance_mock(instance)` | Recolecta datos simulados |
| `_collect_from_instance_real(instance)` | Recolecta vía REST API real |
| `_process_instance_data(instance, data)` | Procesa y guarda datos en BD |
| `collect_single_instance(instance, idx, total)` | Recolecta de una instancia (async) |
| `collect_all_staggered()` | **Recolecta de todas las instancias con delay** |
| `run_continuous()` | Ejecuta recolección continua cada N segundos |
| `cleanup()` | Libera recursos y cierra conexiones |

**Cálculo de alert_level:**
```python
# Dentro de _process_instance_data():
if not healthy:
    alert_level = 'error'
elif lag_seconds >= critical_threshold:  # 3600s (1h)
    alert_level = 'critical'
elif lag_seconds >= warning_threshold:   # 900s (15min)
    alert_level = 'warning'
else:
    alert_level = 'ok'
```

**Características:**
- Asyncio para paralelismo controlado
- Delay configurable entre llamadas (evita saturación)
- Timeout por instancia (30s por defecto)
- Manejo de errores por instancia (no falla todo si una falla)

---

#### `src/ontap_client.py` - Cliente REST API ONTAP

**Clase principal:** `ONTAPClient`

**Funciones disponibles:**

| Función | Descripción | Retorno |
|---------|-------------|--------|
| `__init__(host, username, password, verify_ssl=False)` | Constructor del cliente | - |
| `get_cluster_info()` | Obtiene info básica del cluster | `{uuid, name, version}` |
| `get_snapmirror_relationships()` | **Lista todas las relaciones SnapMirror** | `[{uuid, source_path, ...}]` |
| `test_connection()` | Prueba la conexión al cluster | `True/False` |
| `_parse_iso_duration(duration_str)` | Convierte duración ISO 8601 a segundos | `int` (segundos) |

**Endpoints REST API utilizados:**
```
GET /api/cluster                     # Info del cluster
GET /api/snapmirror/relationships    # Relaciones SnapMirror
```

**Campos extraídos por relación:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `uuid` | string | Identificador único de la relación |
| `source_path` | string | Volumen origen (ej: "svm1:vol1") |
| `destination_path` | string | Volumen destino |
| `policy` | string | Política SnapMirror aplicada |
| `state` | string | Estado (snapmirrored, broken-off, etc.) |
| `healthy` | bool | true si relación saludable |
| `lag_seconds` | int | Lag convertido a segundos |
| `transfer_state` | string | Estado de transferencia actual |
| `last_transfer_end_time` | string | Timestamp última transferencia |

**Ejemplo de uso (integración externa):**
```python
from src.ontap_client import ONTAPClient

client = ONTAPClient('192.168.0.101', 'admin', 'Netapp1!', verify_ssl=False)

# Probar conexión
if client.test_connection():
    print("Conexión OK")
    
    # Obtener info del cluster
    info = client.get_cluster_info()
    print(f"Cluster: {info['name']} v{info['version']}")
    
    # Obtener relaciones SnapMirror
    relationships = client.get_snapmirror_relationships()
    for rel in relationships:
        print(f"{rel['source_path']} -> {rel['destination_path']}")
        print(f"  Lag: {rel['lag_seconds']}s, Healthy: {rel['healthy']}")
```

**Nota sobre SSL:** `verify_ssl=False` desactiva verificación de certificados. En producción, considera usar certificados válidos.

---

#### `src/database.py` - Operaciones MySQL

**Clase principal:** `SnapMirrorDB`

**Tablas gestionadas:**

| Tabla | Propósito |
|-------|----------|
| `ontap_instances` | Inventario de clusters |
| `snapmirror_relationships` | Relaciones configuradas |
| `snapmirror_status_current` | Último estado conocido |
| `snapmirror_status_history` | Histórico para trending |

**Funciones disponibles:**

| Función | Descripción | Uso típico |
|---------|-------------|------------|
| `connect()` | Establece conexión a MySQL | Al inicio del collector |
| `disconnect()` | Cierra la conexión | Al finalizar |
| `upsert_instance(name, ip, lat, lon, location, uuid)` | Inserta o actualiza un cluster ONTAP | Registro inicial |
| `upsert_relationship(instance_id, uuid, src, dst, policy, type)` | Inserta o actualiza relación SnapMirror | Cada ciclo |
| `update_current_status(rel_id, inst_id, lag, state, health, ...)` | Actualiza estado actual | Cada ciclo |
| `insert_history(rel_id, inst_id, lag, state, health, alert)` | Añade registro al histórico | Cada ciclo |
| `get_instance_by_name(name)` | Obtiene instancia por nombre | Búsquedas |
| `get_all_instances()` | Lista todas las instancias activas | Listados |
| `get_map_view()` | Datos agregados para mapa Grafana | Dashboard |
| `get_detail_view(instance_name)` | Vista detallada de relaciones | Dashboard |
| `get_statistics()` | Estadísticas generales (ok/warn/crit) | Dashboard |
| `cleanup_old_history(days=30)` | **Borra registros históricos antiguos** | Mantenimiento |
| `get_history_stats()` | Estadísticas de la tabla histórico | Mantenimiento |

**Ejemplo de uso (integración externa):**
```python
from src.database import SnapMirrorDB

db = SnapMirrorDB('localhost', 3306, 'snapmirror_user', 'SnapMirror123!', 'snapmirror_monitoring')
db.connect()

# Obtener estadísticas
stats = db.get_statistics()
print(f"Total relaciones: {stats['total_relationships']}")
print(f"Críticas: {stats['critical_count']}")

# Limpiar histórico > 30 días
deleted = db.cleanup_old_history(30)
print(f"Registros eliminados: {deleted}")

db.disconnect()
```

---

#### `src/mock_data.py` - Generador de Datos Simulados

**Propósito:** Genera datos SnapMirror realistas para demos.

**Qué simula:**
- Estados variados (80% healthy, 15% warning, 5% critical)
- Lags aleatorios pero realistas
- Nombres de volúmenes típicos
- Coordenadas geográficas en España

**Uso interno:** Cuando se ejecuta `run_collector.py --mode mock`

---

## Arquitectura del Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        ONTAP Clusters                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│  │Cluster 1│ │Cluster 2│ │Cluster 3│ │Cluster N│  (1400+)     │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘              │
└───────┼──────────┼──────────┼──────────┼────────────────────────┘
        │          │          │          │
        │    REST API (HTTPS 443)        │
        │          │          │          │
        ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Python Collector                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ontap_client │  │  collector   │  │   database   │          │
│  │  (REST API)  │→ │  (orchestr.) │→ │   (MySQL)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  Intervalo: 5 min | Delay entre clusters: 0.2s | Timeout: 30s  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ INSERT/UPDATE
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MySQL Database                               │
│  ┌──────────────────┐  ┌────────────────────────┐              │
│  │ ontap_instances  │  │ snapmirror_status_current│             │
│  │ (inventario)     │  │ (estado actual)          │             │
│  └──────────────────┘  └────────────────────────┘              │
│  ┌──────────────────┐  ┌────────────────────────┐              │
│  │ snapmirror_      │  │ snapmirror_status_     │              │
│  │ relationships    │  │ history (trending)     │              │
│  └──────────────────┘  └────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SELECT (queries)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Grafana Dashboard                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Mapa     │  │   Tabla     │  │  Gráficas   │             │
│  │ geográfico  │  │ relaciones  │  │  trending   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  Auto-refresh: 30 segundos                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

```
1. Collector lee CSV de instancias
2. Para cada instancia (con delay de 0.2s):
   a. Conecta via REST API
   b. GET /api/snapmirror/relationships
   c. Parsea respuesta JSON
   d. Calcula alert_level basado en lag y health
   e. INSERT/UPDATE en MySQL
3. Grafana hace SELECT cada 30 segundos
4. Dashboard actualiza visualizaciones
```

---

## Guía de Demostración

### Preparación (15 min antes)

```bash
# 1. Verificar que todo funciona
python3 check_setup.py

# 2. Generar datos frescos
python3 run_collector.py --mode mock --once

# 3. Abrir Grafana
# http://localhost:3000 (admin/admin)
```

### Script de Demo (30-45 min)

#### 1. Contexto del Problema (5 min)

**Puntos a mencionar:**
- "Tenemos 1400+ instancias ONTAP Select distribuidas geográficamente"
- "Cada instancia tiene relaciones SnapMirror para DR"
- "Necesitamos visibilidad centralizada del estado de replicación"
- "Alertas proactivas antes de que el lag sea crítico"

#### 2. Dashboard Overview (10 min)

**Mostrar en Grafana:**

1. **Métricas superiores:**
   - "Aquí vemos el total de instancias monitoreadas"
   - "Número de relaciones SnapMirror activas"
   - "Contadores de warnings, critical y errors"

2. **Mapa geográfico:**
   - "Cada punto representa un cluster ONTAP"
   - "El color indica el peor estado de sus relaciones"
   - "Verde = OK, Amarillo = Warning, Rojo = Critical"
   - "Click en un punto para ver detalles"

3. **Tabla de relaciones:**
   - "Aquí están TODAS las relaciones SnapMirror"
   - "Ordenadas por severidad - los problemas arriba"
   - "Podemos filtrar por cluster, ubicación, estado"
   - "El lag muestra cuánto tiempo desde la última sync"

4. **Gráfica de trending:**
   - "Evolución del lag en las últimas 24 horas"
   - "Útil para detectar tendencias antes de que sea crítico"
   - "Picos pueden indicar problemas de red o storage"

#### 3. Demo del Collector (10 min)

**En terminal:**

```bash
# Mostrar ejecución en vivo
python3 run_collector.py --mode mock --once
```

**Explicar mientras ejecuta:**
- "El collector consulta cada cluster via REST API"
- "Hay un delay de 0.2s entre clusters para no saturar"
- "Los datos se guardan en MySQL"
- "Grafana los muestra automáticamente"

**Mostrar logs:**
```bash
# Si está como servicio
sudo journalctl -u collector -f
```

#### 4. Añadir Nueva Instancia (5 min)

**Demostrar discover:**
```bash
python3 discover_ontap_clusters.py
```

**Explicar:**
- "No hace falta editar archivos manualmente"
- "El asistente guía paso a paso"
- "Prueba la conexión antes de añadir"
- "La nueva instancia aparece automáticamente en Grafana"

#### 5. Troubleshooting (5 min)

**Mostrar herramientas de diagnóstico:**
```bash
# Verificar configuración
python3 check_setup.py

# Test conexión MySQL
python3 test_mysql_connection.py

# Ver estado de instancias
python3 remove_instance.py --list
```

#### 6. Q&A (5-10 min)

**Preguntas frecuentes:**

Q: "¿Cada cuánto se actualiza?"
A: "El collector corre cada 5 minutos, Grafana refresca cada 30 segundos"

Q: "¿Qué pasa si un cluster está caído?"
A: "El collector continúa con los demás, el error se registra pero no bloquea"

Q: "¿Puedo añadir alertas por email?"
A: "Sí, Grafana tiene alerting integrado, se puede configurar email, Slack, etc."

Q: "¿Cuánto histórico se guarda?"
A: "Ilimitado por defecto. Usa `python3 cleanup_history.py --days 30` para borrar registros antiguos"

Q: "¿Cómo limpio el histórico antiguo?"
A: "Ejecuta `python3 cleanup_history.py` para ver estadísticas, o `--days 30` para borrar >30 días"

---

## Mejoras Potenciales para Grafana

### 1. Alerting Avanzado

**Configurar en Grafana:**

```yaml
# Alerta: Lag > 1 hora
Nombre: SnapMirror Critical Lag
Condición: lag_seconds > 3600
Frecuencia: cada 5 min
Notificación: Email / Slack / PagerDuty
```

**Queries sugeridas:**
```sql
-- Relaciones críticas (enviar alerta)
SELECT i.name, s.source_path, s.destination_path, 
       s.lag_seconds/60 as lag_minutes
FROM snapmirror_status_current s
JOIN ontap_instances i ON s.instance_id = i.id
WHERE s.alert_level = 'critical'
  AND i.is_active = TRUE;
```

### 2. Dashboard por Cliente/Región

**Nuevo dashboard con variables:**

```sql
-- Variable: $region
SELECT DISTINCT location_name FROM ontap_instances WHERE is_active = TRUE;

-- Variable: $cluster  
SELECT name FROM ontap_instances WHERE location_name = '$region';
```

**Paneles filtrados:**
- Mapa: solo muestra clusters de $region
- Tabla: filtrada por $cluster
- Stats: contadores de esa región

### 3. Panel de Capacidad

**Nueva query para trending de transferencias:**
```sql
SELECT 
  DATE_FORMAT(collected_at, '%Y-%m-%d %H:00') as hora,
  COUNT(*) as transferencias,
  AVG(lag_seconds) as lag_promedio
FROM snapmirror_status_history
WHERE collected_at > NOW() - INTERVAL 7 DAY
GROUP BY hora
ORDER BY hora;
```

**Visualización:** Gráfica de barras + línea de tendencia

### 4. Heat Map de Problemas

**Query para heat map temporal:**
```sql
SELECT 
  HOUR(collected_at) as hora,
  DAYNAME(collected_at) as dia,
  COUNT(CASE WHEN alert_level IN ('warning','critical','error') THEN 1 END) as problemas
FROM snapmirror_status_history
WHERE collected_at > NOW() - INTERVAL 30 DAY
GROUP BY dia, hora;
```

**Uso:** Identificar patrones (ej: "los problemas ocurren los viernes a las 18h")

### 5. SLA Dashboard

**Métricas de cumplimiento:**
```sql
-- % de tiempo en estado OK (últimos 30 días)
SELECT 
  i.name,
  ROUND(
    SUM(CASE WHEN h.alert_level = 'ok' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 
    2
  ) as sla_percent
FROM snapmirror_status_history h
JOIN ontap_instances i ON h.instance_id = i.id
WHERE h.collected_at > NOW() - INTERVAL 30 DAY
GROUP BY i.name
ORDER BY sla_percent ASC;
```

**Panel:** Tabla con SLA por cluster, coloreada (verde >99%, amarillo >95%, rojo <95%)

### 6. Drill-down por Relación

**Dashboard secundario con variable $relationship:**

```sql
-- Historial de una relación específica
SELECT 
  collected_at,
  lag_seconds/60 as lag_minutes,
  state,
  health_status
FROM snapmirror_status_history
WHERE relationship_id = $relationship
ORDER BY collected_at DESC
LIMIT 1000;
```

**Navegación:** Click en tabla principal → abre dashboard de detalle

### 7. Comparativa Entre Clusters

**Query para comparar rendimiento:**
```sql
SELECT 
  i.name,
  i.location_name,
  COUNT(DISTINCT r.id) as total_relaciones,
  AVG(s.lag_seconds) as lag_promedio,
  MAX(s.lag_seconds) as lag_maximo,
  SUM(CASE WHEN s.alert_level = 'critical' THEN 1 ELSE 0 END) as criticos_24h
FROM ontap_instances i
JOIN snapmirror_relationships r ON i.id = r.instance_id
JOIN snapmirror_status_current s ON r.id = s.relationship_id
WHERE i.is_active = TRUE
GROUP BY i.id
ORDER BY lag_promedio DESC;
```

### 8. Notificaciones Inteligentes

**Configurar en Grafana Alerting:**

| Alerta | Condición | Acción |
|--------|-----------|--------|
| Lag Warning | lag > 15 min | Log |
| Lag Critical | lag > 1 hora | Email |
| Cluster Down | no data 10 min | Slack + Email |
| Múltiples Critical | >5 critical | PagerDuty |

### 9. Reporte Automático

**Usar Grafana Reporter o Image Renderer:**

- PDF diario con estado de todas las relaciones
- Email semanal con resumen de SLA
- Exportar PNG del mapa para presentaciones

### 10. Integración con ServiceNow/Jira

**Webhook desde Grafana:**

```json
{
  "url": "https://servicenow.company.com/api/incident",
  "method": "POST",
  "body": {
    "short_description": "SnapMirror Critical: ${alertname}",
    "description": "Cluster: ${cluster}, Lag: ${lag_minutes} min",
    "urgency": 2,
    "category": "Storage"
  }
}
```

---

## Casos de Uso Avanzados

### Monitoreo Multi-Site

**Escenario:** Varios datacenters con collectors locales, dashboard centralizado.

**Arquitectura:**
```
DC Madrid           DC Barcelona         DC Central
┌─────────┐         ┌─────────┐         ┌─────────┐
│Collector│         │Collector│         │ Grafana │
│  Local  │───────► │  Local  │───────► │Central  │
│ MySQL   │         │ MySQL   │         │ MySQL   │
└─────────┘         └─────────┘         └─────────┘
```

**Implementación:**
- Cada DC tiene su collector y MySQL local
- MySQL central replica de los locales
- Grafana apunta a MySQL central

### Automatización de Respuesta

**Escenario:** Reiniciar SnapMirror automáticamente si falla.

**Implementación:**
1. Grafana detecta `state = 'broken-off'`
2. Webhook a script Python
3. Script ejecuta `snapmirror resync` via REST API
4. Log del evento para auditoría

### Capacity Planning

**Escenario:** Predecir cuándo el lag será crítico.

**Implementación:**
1. Query histórico de lag por hora
2. Aplicar regresión lineal
3. Mostrar predicción en Grafana
4. Alertar si predicción > threshold en 24h

---

## Contacto

**Autor:** NetApp Professional Services  
**Fecha:** Febrero 2026  
**Versión:** 1.0.0

Para dudas técnicas o mejoras, contactar al equipo de PS.
