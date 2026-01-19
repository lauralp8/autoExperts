# SnapMirror Monitor - Changelog

## [1.0.0] - 2026-01-19

### ✨ Features Iniciales

#### Core Functionality
- ✅ Recolector Python con polling en cascada (staggered)
- ✅ Cliente REST API para ONTAP 9.12+ (solo GET requests)
- ✅ Soporte para 1400+ instancias ONTAP Select
- ✅ Distribución de carga: 0.2s delay entre instancias
- ✅ Ejecución asíncrona con asyncio

#### Base de Datos
- ✅ Schema MySQL completo con 4 tablas principales
- ✅ Vistas optimizadas para Grafana (v_snapmirror_map, v_snapmirror_detail)
- ✅ Tabla histórica con particionado por fecha
- ✅ Índices optimizados para queries frecuentes

#### Monitorización
- ✅ Dashboard Grafana con Geomap
- ✅ Código de colores por severidad (OK/Warning/Critical/Error)
- ✅ Umbrales configurables:
  - Warning: lag > 15 minutos
  - Critical: lag > 1 hora
- ✅ Tabla de alertas activas
- ✅ Gráficas de tendencia (24h)

#### Modos de Operación
- ✅ **Modo MOCK**: Simulación con datos generados
  - 100 instancias por defecto (configurable)
  - 3 relaciones SnapMirror por instancia
  - 30% probabilidad de lag
  - 5% probabilidad de errores
- ✅ **Modo REAL**: Conexión a ONTAP Select real

#### Utilidades
- ✅ Script de inicialización de BD (`init_database.py`)
- ✅ Generador de CSV mock (`generate_mock_csv.py`)
- ✅ Configuración centralizada en YAML
- ✅ Logging a archivo y consola
- ✅ Argumentos CLI completos

#### Documentación
- ✅ README completo con arquitectura
- ✅ QUICKSTART para setup rápido
- ✅ Comentarios inline en código
- ✅ Ejemplos de uso

### 🔧 Configuración

#### Archivos de Configuración
- `config/config.yaml` - Configuración principal
- `config/mysql_schema.sql` - Schema de base de datos
- `config/ontap_instances.csv` - Lista de instancias ONTAP

#### Parámetros Principales
```yaml
collector:
  interval_seconds: 300        # 5 minutos
  stagger_delay_seconds: 0.2   # 200ms entre instancias
  max_concurrent: 50           # Requests simultáneos

thresholds:
  warning: 900    # 15 min
  critical: 3600  # 1 hora
```

### 📊 Métricas del Dashboard

1. **Estadísticas Globales**
   - Total instancias ONTAP
   - Total relaciones SnapMirror
   - Contador Warnings
   - Contador Críticos

2. **Mapa Geográfico**
   - Ubicación de instancias
   - Marcadores con código de colores
   - Tooltip con detalles

3. **Alertas Activas**
   - Tabla filtrada por severidad
   - Ordenamiento por lag
   - Drill-down disponible

4. **Tendencias**
   - Evolución de lag (24h)
   - Solo relaciones problemáticas
   - Líneas por relación

### 🎯 Casos de Uso Cubiertos

- ✅ Monitorización de lag SnapMirror en múltiples sitios
- ✅ Alertas automáticas por umbral
- ✅ Visualización geográfica de estado
- ✅ Histórico para análisis de tendencias
- ✅ Testing sin acceso a ONTAP (modo mock)

### 📝 Notas Técnicas

- Python 3.8+ requerido
- MySQL 5.7+ / MariaDB 10.3+
- Grafana 8.0+ (Geomap nativo)
- Librería netapp-ontap 9.12.0+

### 🔒 Seguridad

- Solo operaciones GET en ONTAP (read-only)
- SSL verification deshabilitado por defecto (development)
- Credenciales en archivo CSV (cambiar a vault en producción)
- Usuario MySQL con permisos mínimos

### 🚀 Performance

- **Tiempo de recolección completa**: ~4.7 min (1400 instancias × 0.2s)
- **Memoria**: < 200 MB en ejecución normal
- **CPU**: Bajo (asíncrono con asyncio)
- **Tráfico de red**: ~1 KB por instancia por ciclo

### ⚠️ Limitaciones Conocidas

1. Credenciales en plaintext (CSV) - usar vault en producción
2. SSL verification deshabilitado por defecto
3. Sin autenticación en API (solo local)
4. Particionado manual de tabla history

### 🔮 Roadmap Futuro

- [ ] Integración con HashiCorp Vault
- [ ] API REST para queries externas
- [ ] Exportación de métricas a Prometheus
- [ ] Dashboard mobile-friendly
- [ ] Alerting por instancia/región
- [ ] Auto-particionado de tablas
- [ ] Multi-tenancy support

### 🐛 Bugs Conocidos

Ninguno reportado en esta versión.

### 🙏 Agradecimientos

Desarrollado para NetApp Professional Services
Testing inicial con datos mock
