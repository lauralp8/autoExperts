# Guía Rápida de Inicio - SnapMirror Monitor

## ⚡ Setup Rápido (5 minutos)

### 1. Instalar Dependencias
```powershell
pip install -r requirements.txt
```

### 2. Configurar MySQL
Editar credenciales en `config/config.yaml`:
```yaml
database:
  host: localhost
  user: root
  password: TU_PASSWORD
```

Inicializar BD:
```powershell
python init_database.py
```

### 3. Generar Datos de Prueba
```powershell
python generate_mock_csv.py --num-instances 50
```

### 4. Ejecutar Collector (Modo Mock)
```powershell
python run_collector.py --mode mock --once
```

### 5. Importar Dashboard en Grafana
1. Grafana → Dashboards → Import
2. Cargar: `grafana/snapmirror_dashboard.json`
3. Seleccionar datasource MySQL

## ✅ Verificación

Abrir Grafana y verificar:
- Mapa con marcadores de instancias
- Estadísticas en paneles superiores
- Tabla con alertas (si hay lag simulado)

## 🔄 Siguiente Paso

**Para Producción:**
1. Editar `config/ontap_instances.csv` con IPs reales
2. Cambiar modo a `real` en `config.yaml`
3. Ejecutar: `python run_collector.py --mode real`

## 📚 Documentación Completa

Ver [README.md](README.md) para información detallada.
