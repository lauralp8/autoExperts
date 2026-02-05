# SnapMirror Monitor - Guía Completa de Operación

## Índice
1. [Arquitectura General](#1-arquitectura-general)
2. [Qué hace cada componente](#2-qué-hace-cada-componente)
3. [Cómo funciona run_collector.py](#3-cómo-funciona-run_collectorpy)
4. [Cómo trae los datos de ONTAP](#4-cómo-trae-los-datos-de-ontap)
5. [Cómo procesa y guarda en la BBDD](#5-cómo-procesa-y-guarda-en-la-bbdd)
6. [Cómo llegan los datos a Grafana](#6-cómo-llegan-los-datos-a-grafana)
7. [Gestión de Instancias (Alta/Baja)](#7-gestión-de-instancias-altabaja)
8. [Requisitos e Instalación](#8-requisitos-e-instalación)
9. [Mejoras Potenciales para Grafana](#9-mejoras-potenciales-para-grafana)
10. [Puntos de Venta](#10-puntos-de-venta)

---

## 1. Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUJO DE DATOS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────┐    ┌─────────┐  │
│  │ ontap_instances │ -> │ Python Collector │ -> │ MySQL  │ -> │ Grafana │  │
│  │     (.csv)      │    │                  │    │        │    │         │  │
│  └─────────────────┘    └────────┬─────────┘    └────────┘    └─────────┘  │
│                                  │                                          │
│                                  ▼                                          │
│                         ┌────────────────┐                                  │
│                         │ ONTAP REST API │                                  │
│                         │ (1400+ clusters)│                                 │
│                         └────────────────┘                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Ciclo de operación (cada 5 minutos):**
1. El collector lee los clusters desde el CSV
2. Consulta cada cluster vía REST API (con 0.2s de delay entre consultas para no saturar)
3. Procesa los datos y calcula niveles de alerta
4. Guarda en MySQL (estado actual + histórico)
5. Grafana lee directamente de MySQL y pinta los dashboards

---

## 2. Qué hace cada componente

| Archivo | Función |
|---------|---------|
| `run_collector.py` | **Script principal** - Punto de entrada, parsea argumentos, arranca el collector |
| `src/collector.py` | **Lógica principal** - Lee CSV, coordina recolección escalonada, calcula alertas |
| `src/ontap_client.py` | **Cliente REST API** - Habla con ONTAP (`/api/snapmirror/relationships`) |
| `src/database.py` | **Operaciones MySQL** - Insert, update, queries a la base de datos |
| `src/mock_data.py` | **Datos simulados** - Generador para testing sin conectar a ONTAP real |
| `config/config.yaml` | **Configuración** - BBDD, thresholds, intervalos |
| `config/ontap_instances.csv` | **Inventario** - Lista de clusters a monitorizar |
| `config/mysql_schema.sql` | **Schema SQL** - Estructura de tablas y vistas |
| `grafana/*.json` | **Dashboards** - Configuración de paneles Grafana |

---

## 3. Cómo funciona run_collector.py

`run_collector.py` es el **punto de entrada principal** del sistema. Es el script que se ejecuta directamente.

### Argumentos disponibles

```bash
python run_collector.py [opciones]
```

| Argumento | Descripción | Valor por defecto |
|-----------|-------------|-------------------|
| `--config` | Ruta al archivo de configuración | `config/config.yaml` |
| `--once` | Ejecutar una sola vez y salir | No (continuo) |
| `--mode` | Forzar modo `mock` o `real` | Usa el de config.yaml |
| `--log-level` | Nivel de log: DEBUG, INFO, WARNING, ERROR | INFO |

### Ejemplos de uso

```bash
# Una sola ejecución con datos simulados (testing)
python run_collector.py --once --mode mock

# Una sola ejecución con datos reales
python run_collector.py --once --mode real

# Modo continuo (producción) - cada 5 minutos
python run_collector.py --mode real

# Con configuración personalizada
python run_collector.py --config mi_config.yaml --once

# Debug detallado
python run_collector.py --log-level DEBUG --once
```

### Qué hace internamente

1. **Parsea argumentos** de línea de comandos
2. **Configura logging** (archivo `logs/collector.log` + consola)
3. **Crea el collector** (`SnapMirrorCollector`)
4. **Ejecuta setup()**: conecta a MySQL, carga instancias del CSV, las registra en BBDD
5. **Ejecuta la recolección**:
   - `--once`: ejecuta `collect_all_staggered()` una vez
   - Sin `--once`: ejecuta `run_continuous()` que repite cada 5 min
6. **Limpieza**: cierra conexiones al terminar

---

## 4. Cómo trae los datos de ONTAP

### Endpoint REST API utilizado

```
GET https://{cluster_ip}/api/snapmirror/relationships
```

### Campos que obtiene de cada relación

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `uuid` | Identificador único de la relación | `a1b2c3d4-...` |
| `source.path` | Volumen/SVM origen | `svm1:vol_data` |
| `destination.path` | Volumen/SVM destino | `svm2:vol_data_dr` |
| `policy.name` | Política de replicación | `MirrorAllSnapshots` |
| `state` | Estado de la relación | `snapmirrored`, `broken-off` |
| `healthy` | Indicador de salud | `true` / `false` |
| `lag_time` | Desfase en formato ISO 8601 | `PT1H30M45S` |
| `transfer.state` | Estado de transferencia actual | `idle`, `transferring` |
| `transfer.end_time` | Última transferencia completada | ISO timestamp |

### Conversión de lag_time

El código convierte el formato ISO 8601 a segundos:
- `PT1H30M45S` → 5445 segundos
- `PT15M` → 900 segundos
- `PT2H` → 7200 segundos

### Recolección escalonada (Staggered)

Para no saturar la red ni los clusters:
- **Delay entre consultas**: 0.2 segundos
- **1400 clusters × 0.2s = ~5 minutos** para completar un ciclo
- Esto coincide con el intervalo de recolección, evitando picos

---

## 5. Cómo procesa y guarda en la BBDD

### Tablas principales

| Tabla | Propósito | Comportamiento |
|-------|-----------|----------------|
| `ontap_instances` | Inventario de clusters | UPSERT (actualiza si existe) |
| `snapmirror_relationships` | Relaciones SnapMirror por cluster | UPSERT |
| `snapmirror_status_current` | Estado actual | Se SOBREESCRIBE cada ciclo |
| `snapmirror_status_history` | Histórico | Se INSERTA cada ciclo |

### Cálculo automático de alertas

```
┌─────────────────────────────────────────────────────────────┐
│                    NIVELES DE ALERTA                        │
├─────────────────────────────────────────────────────────────┤
│  lag < 15 min (900s)      →  alert_level = 'ok'      🟢     │
│  lag 15-60 min            →  alert_level = 'warning' 🟡     │
│  lag > 60 min (3600s)     →  alert_level = 'critical' 🔴    │
│  healthy = false          →  alert_level = 'error'   🟣     │
└─────────────────────────────────────────────────────────────┘
```

Los thresholds son configurables en `config/config.yaml`:
```yaml
thresholds:
  warning: 900   # 15 minutos
  critical: 3600 # 1 hora
```

### Flujo de guardado

```
Por cada cluster:
  1. upsert_instance()      → Registra/actualiza el cluster
  2. Por cada relación:
     a. upsert_relationship()    → Registra/actualiza la relación
     b. update_current_status()  → Sobreescribe estado actual
     c. insert_history()         → Añade al histórico
```

### Vistas SQL precreadas

| Vista | Uso | Descripción |
|-------|-----|-------------|
| `v_snapmirror_map` | Mapa Grafana | Datos agregados por cluster con coordenadas |
| `v_snapmirror_detail` | Tabla detalle | Todas las relaciones con su estado |

---

## 6. Cómo llegan los datos a Grafana

### Conexión

Grafana tiene configurado un **datasource MySQL** apuntando a:
- Host: según config
- Database: `snapmirror_monitoring`

### Paneles del dashboard

| Panel | Tipo | Query |
|-------|------|-------|
| Total ONTAP Instances | Stat | `SELECT COUNT(*) FROM ontap_instances WHERE is_active = TRUE` |
| Total SnapMirror Relations | Stat | `SELECT COUNT(*) FROM snapmirror_relationships` |
| Warnings | Stat | `SELECT COUNT(*) FROM snapmirror_status_current WHERE alert_level = 'warning'` |
| Critical | Stat | `SELECT COUNT(*) FROM snapmirror_status_current WHERE alert_level = 'critical'` |
| Errors | Stat | `SELECT COUNT(*) FROM snapmirror_status_current WHERE alert_level = 'error'` |
| Mapa | Geomap | `SELECT * FROM v_snapmirror_map` |
| Tabla detalle | Table | `SELECT * FROM v_snapmirror_detail` |

### Colores del mapa

El mapa usa el campo `overall_status` de `v_snapmirror_map`:
- **Verde**: Todos los relationships OK
- **Amarillo**: Al menos un warning
- **Rojo**: Al menos un critical
- **Morado**: Al menos un error (unhealthy)

---

## 7. Gestión de Instancias (Alta/Baja)

### Dar de ALTA una instancia

1. Añadir línea al CSV `config/ontap_instances.csv`:
```csv
nombre-cluster,192.168.1.100,40.4168,-3.7038,Madrid DC,admin,password123
```

2. El próximo ciclo de recolección la registrará automáticamente

### Dar de BAJA una instancia

#### Opción A - Baja lógica (recomendado)
```sql
UPDATE ontap_instances SET is_active = FALSE WHERE name = 'nombre-cluster';
```
- Los datos históricos se mantienen
- Grafana deja de mostrarla (filtra por `is_active = TRUE`)

#### Opción B - Eliminar del CSV
- Quitar la línea del archivo `config/ontap_instances.csv`
- El collector deja de consultarla
- Datos históricos permanecen en BBDD

#### Opción C - Eliminación total
```sql
DELETE FROM ontap_instances WHERE name = 'nombre-cluster';
```
- Las foreign keys `ON DELETE CASCADE` eliminan todo en cascada
- Se pierden todos los datos históricos

#### Opción D - Usar el script `remove_instance.py`
```bash
# Ver estado actual
python remove_instance.py --list

# Baja lógica (recomendado)
python remove_instance.py --name "nombre-cluster" --disable

# Eliminación completa
python remove_instance.py --name "nombre-cluster" --delete

# Por IP
python remove_instance.py --ip "192.168.1.100" --delete
```

---

## 8. Requisitos e Instalación

### Requisitos de sistema

| Componente | Versión mínima |
|------------|----------------|
| Python | 3.9+ |
| MySQL | 8.0+ |
| Grafana | 10.0+ |
| SO | RHEL/Ubuntu/Windows |

### Dependencias Python

```
pymysql>=1.0.0
pyyaml>=6.0
requests>=2.28.0
```

### Instalación rápida

```bash
# 1. Clonar repositorio
cd /opt
git clone <repo> corme
cd corme

# 2. Instalar dependencias
pip3 install -r requirements.txt

# 3. Configurar MySQL
mysql -u root -p < config/mysql_schema.sql

# 4. Editar configuración
vi config/config.yaml
vi config/ontap_instances.csv

# 5. Test con datos mock
python run_collector.py --once --mode mock

# 6. Test con datos reales
python run_collector.py --once --mode real

# 7. Configurar servicio (Linux)
sudo cp collector.service /etc/systemd/system/
sudo systemctl enable collector
sudo systemctl start collector
```

### Verificar funcionamiento

```bash
# Ver logs
tail -f logs/collector.log

# Ver estado del servicio
sudo systemctl status collector

# Verificar datos en MySQL
mysql -u snapmirror_user -p snapmirror_monitoring -e "SELECT * FROM v_snapmirror_map LIMIT 5;"
```

---

## 9. Mejoras Potenciales para Grafana

| Mejora | Descripción | Complejidad |
|--------|-------------|-------------|
| **Filtro por región** | Variable de template para filtrar por `location_name` | Baja |
| **Drill-down desde mapa** | Clic en marcador → detalle del cluster | Media |
| **Alerting nativo** | Alertas Grafana → email/Teams cuando hay criticals | Baja |
| **Gráfica de tendencia** | Time series con histórico de lag | Baja |
| **Top N peores** | Panel con las 10 relaciones con mayor lag | Baja |
| **Última recolección** | Indicador de hace cuánto se ejecutó el collector | Baja |
| **Filtro por política** | Ver solo relaciones con ciertas policies | Baja |
| **Dashboard por relación** | Ya existe: `snapmirror_dashboard_per_relationship.json` | ✅ |

---

## 10. Puntos de Venta

### Para el cliente

| Característica | Beneficio |
|----------------|-----------|
| **Escalabilidad probada** | Diseñado para 1400+ instancias con recolección escalonada |
| **Sin impacto en producción** | Solo lecturas REST API, 0.2s entre consultas |
| **Alertas automáticas** | Thresholds configurables, visualización inmediata |
| **Datos históricos** | Permite análisis de tendencias y auditoría |
| **Modo mock** | Pueden probar sin conectarse a ONTAP real |
| **Todo incluido** | Schema SQL, dashboards Grafana, servicio systemd |
| **Mantenimiento simple** | Dar de baja/alta con CSV o un UPDATE SQL |
| **Open source friendly** | Python estándar, sin licencias adicionales |

### Diferenciadores técnicos

- Recolección asíncrona con `asyncio`
- Delay configurable entre consultas (no satura la red)
- Vistas SQL optimizadas para Grafana
- Histórico para análisis de tendencias
- Flag `is_active` para bajas lógicas sin perder datos

---

## Contacto y Soporte

Para dudas o problemas:
1. Revisar logs: `logs/collector.log`
2. Verificar conectividad a clusters ONTAP
3. Verificar conexión a MySQL
4. Comprobar credenciales en `config.yaml` y CSV

---

*Documento generado para SnapMirror Monitor (CORME)*
