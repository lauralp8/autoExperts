# Requisitos — Adaptación a Napp Console (rama `justmap`)

> Documento interno para el equipo técnico.  
> Proyecto base: `ps_corpme_snapmirror_grafana_monitor_python`  
> Alcance de esta rama: **mapas SnapMirror únicamente** (sin dashboard de capacidad, sin auto-resize).

---

## 1. Contexto y objetivos

El proyecto original monitoriza relaciones SnapMirror consultando directamente la REST API de cada clúster ONTAP Select. Esta adaptación cambia la fuente de datos a **Napp Console**, que actúa como plano de control centralizado y expone su propia API para obtener el estado de las relaciones de todos los clústeres gestionados.

**Lo que hacemos en esta rama:**
- Mantener la arquitectura completa (Collector → MySQL → Grafana).
- Sustituir el cliente `src/ontap_client.py` (que habla con ONTAP directamente) por un nuevo módulo `src/napp_client.py` que consulta **Napp Console API**.
- Conservar los dos dashboards de mapas Grafana:
  - `grafana/snapmirror_dashboard.json` — mapa geo con todas las instancias.
  - `grafana/snapmirror_dashboard_per_relationship.json` — vista por relación individual.
- **Eliminar / no incluir:**
  - `grafana/instance_detail_dashboard.json` (dashboard de capacidad) — **no está en esta rama**.
  - `grafana/alerting_rules.json` / `grafana/alerting_contact_points.yaml` (alertas de auto-resize) — **no están en esta rama**.
  - `webhook_server.py` / `webhook.service` (servidor de eventos para auto-resize) — **no están en esta rama**.

---

## 2. Inventario de cambios necesarios

### 2.1 Nuevo módulo: `src/napp_client.py`

Reemplaza `src/ontap_client.py`. Debe implementar la misma interfaz que el colector espera:

```python
class NappClient:
    def __init__(self, base_url: str, api_token: str, verify_ssl: bool = True): ...
    def get_snapmirror_relationships(self, instance_id: str) -> List[Dict]: ...
    def test_connection(self) -> bool: ...
```

**Datos que debe devolver `get_snapmirror_relationships`** (misma estructura que antes):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `uuid` | str | Identificador único de la relación |
| `source_path` | str | Ruta origen (ej. `svm_name:volume_name`) |
| `destination_path` | str | Ruta destino |
| `policy` | str | Nombre de la política SnapMirror |
| `state` | str | `snapmirrored`, `uninitialized`, `broken-off`, etc. |
| `healthy` | bool | Estado de salud de la relación |
| `lag_seconds` | int | Lag en segundos |
| `transfer_state` | str | Estado de la transferencia activa (`idle`, `transferring`, etc.) |

### 2.2 Requisitos de la API de Napp Console

> ⚠️ **Pendiente de confirmar con el equipo de Napp Console** los endpoints exactos y el esquema de autenticación.

**Preguntas a resolver antes de implementar:**

1. **Autenticación**: ¿Bearer token estático, OAuth2, API key en header? ¿Cuánto dura el token?
2. **Endpoint de relaciones SnapMirror**: ¿Qué URL devuelve las relaciones de todas las instancias (o de una en concreto)?
   - Sugerencia a confirmar: `GET /api/v1/snapmirror/relationships?instance_id={id}`
3. **Formato del lag**: ¿ISO 8601 (`PT1H30M`) como ONTAP, o segundos directamente?
4. **Paginación**: ¿Devuelve todos los registros en una sola respuesta, o hay que paginar?
5. **Inventario de instancias**: ¿Hay endpoint para listar las instancias gestionadas por Napp Console, o seguimos usando el CSV?
6. **Certificados SSL**: ¿El entorno de producción tiene certificado firmado por CA conocida?

**Estructura mínima esperada de la respuesta** (a confirmar):

```json
{
  "records": [
    {
      "uuid": "abc-123",
      "source": { "path": "svm1:vol1" },
      "destination": { "path": "svm2:vol1" },
      "policy": { "name": "MirrorAllSnapshots" },
      "state": "snapmirrored",
      "healthy": true,
      "lag_time": "PT5M30S",
      "transfer": { "state": "idle" }
    }
  ]
}
```

### 2.3 Fichero de configuración (`config/config.yaml`)

Añadir sección `napp_console` y eliminar la sección `ontap` si existiera:

```yaml
napp_console:
  base_url: https://<napp-console-host>   # URL base de la API
  api_token: <change_me>                  # Token de acceso (usar .env o vault en producción)
  verify_ssl: true
  timeout_seconds: 30
```

> **Seguridad**: nunca commitear el token al repositorio. Usar variable de entorno `NAPP_CONSOLE_API_TOKEN` o un fichero `.env` excluido por `.gitignore`.

### 2.4 Inventario de instancias (`config/ontap_instances.csv`)

El nombre del fichero puede mantenerse o renombrarse a `config/instances.csv`.  
Las columnas relevantes para los mapas son:

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| `name` | Nombre de la instancia en Napp Console | `Madrid-01` |
| `napp_instance_id` | ID de la instancia en Napp Console | `inst-abc123` |
| `latitude` | Latitud para el mapa Grafana | `40.4168` |
| `longitude` | Longitud para el mapa Grafana | `-3.7038` |
| `location` | Descripción del site | `Madrid DC1` |

### 2.5 Módulo `src/collector.py`

Cambios menores necesarios:
- Sustituir la importación de `ONTAPClient` por `NappClient`.
- Leer `napp_instance_id` desde el CSV (en vez de `host`).
- Pasar `base_url` y `api_token` desde la config en lugar de credenciales por instancia.

### 2.6 `requirements.txt`

Eliminar `netapp-ontap>=9.12.0` (SDK de ONTAP ya no se usa). El resto de dependencias se mantiene.

### 2.7 Scripts a revisar / adaptar

| Script | Estado | Comentario |
|--------|--------|------------|
| `src/napp_client.py` | **Nuevo — pendiente de crear** | Reemplaza `ontap_client.py` |
| `src/ontap_client.py` | **Deprecado** | Dejar en rama, renombrar o eliminar según decisión del equipo |
| `src/collector.py` | **Modificar** | Pequeño ajuste de importaciones y parámetros |
| `src/database.py` | **Sin cambios** | El schema MySQL no cambia |
| `src/mock_data.py` | **Sin cambios** | Sigue siendo válido para testing |
| `discover_ontap_clusters.py` | **Deprecado** | Específico de ONTAP. Considerar crear `discover_napp_instances.py` si Napp Console tiene endpoint de inventario |
| `check_setup.py` | **Revisar** | Actualizar para verificar config `napp_console` en vez de credenciales ONTAP |
| `run_collector.py` | **Sin cambios** | El punto de entrada no necesita cambios |
| `init_database.py` | **Sin cambios** | |
| `remove_instance.py` | **Sin cambios** | Gestión del CSV, independiente del API |

---

## 3. Dashboards Grafana (alcance de esta rama)

### Incluidos

| Fichero | Dashboard | Descripción |
|---------|-----------|-------------|
| `grafana/snapmirror_dashboard.json` | **Mapa global** | Geo-map con todas las instancias, coloreadas por estado de alerta |
| `grafana/snapmirror_dashboard_per_relationship.json` | **Vista por relación** | Tabla detallada y gráfico de lag por relación individual |

### No incluidos en esta rama

| Fichero | Motivo |
|---------|--------|
| `grafana/instance_detail_dashboard.json` | Dashboard de capacidad de volúmenes — fuera de alcance |
| `grafana/alerting_rules.json` | Reglas de alerta para auto-resize — fuera de alcance |
| `grafana/alerting_contact_points.yaml` | Contact points para alertas de auto-resize — fuera de alcance |

---

## 4. Esquema de base de datos

El schema MySQL en `config/mysql_schema.sql` **no requiere cambios** para los mapas.  
Las tablas relevantes son:

- `snapmirror_current` — Estado más reciente de cada relación (leída por Grafana en tiempo real).
- `snapmirror_history` — Histórico para gráficos de tendencia de lag.
- Vista `v_snapmirror_summary` — Agregado por instancia para el mapa.

---

## 5. Plan de trabajo sugerido

```
Fase 1 — Información (bloqueante)
  [ ] Obtener documentación oficial de Napp Console API
  [ ] Confirmar endpoints de SnapMirror relationships
  [ ] Confirmar mecanismo de autenticación
  [ ] Obtener acceso a entorno de pruebas de Napp Console

Fase 2 — Desarrollo
  [ ] Crear src/napp_client.py con los métodos de la interfaz
  [ ] Adaptar src/collector.py (imports + lectura de config napp_console)
  [ ] Actualizar config/config.yaml con sección napp_console
  [ ] Actualizar config/ontap_instances.csv con columna napp_instance_id
  [ ] Actualizar requirements.txt (quitar netapp-ontap)
  [ ] Adaptar check_setup.py para validar config napp_console

Fase 3 — Test
  [ ] Probar con mock data (python3 run_collector.py --mode mock --once)
  [ ] Probar contra entorno de pruebas de Napp Console
  [ ] Importar dashboards en Grafana de lab y validar que el mapa pinta correctamente

Fase 4 — Documentación y entrega
  [ ] Actualizar README_ES.md con guía de operación para Napp Console
  [ ] Actualizar docs/GUIA_TECNICA.md
  [ ] Revisar precheck.txt y cliente_precheck.txt
```

---

## 6. Decisiones pendientes

| # | Decisión | Responsable | Fecha límite |
|---|----------|-------------|--------------|
| 1 | Confirmar endpoints y auth de Napp Console API | Equipo Napp Console | — |
| 2 | ¿Renombrar `ontap_instances.csv` a `instances.csv`? | Equipo | — |
| 3 | ¿Eliminar `src/ontap_client.py` o mantenerlo como referencia? | Equipo | — |
| 4 | ¿Despliegue como servicio systemd o contenedor? | Equipo | — |
| 5 | Gestión segura del API token (`.env`, vault, otro) | Equipo | — |
