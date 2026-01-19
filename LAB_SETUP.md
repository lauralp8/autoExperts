# Lab on Demand - Setup Instructions

## 🚀 Instalación Automática

### Windows (PowerShell como Administrador)

```powershell
# Navegar al directorio del proyecto
cd "C:\Users\ca57934\OneDrive - NetApp Inc\Autocosas\CORME"

# Permitir ejecución de scripts
Set-ExecutionPolicy Bypass -Scope Process -Force

# Ejecutar instalación
.\setup_lab.ps1
```

**Tiempo estimado:** 10-15 minutos

### Linux (Ubuntu/RHEL/CentOS)

```bash
# Navegar al directorio del proyecto
cd ~/CORME

# Dar permisos de ejecución
chmod +x setup_lab.sh

# Ejecutar instalación
sudo ./setup_lab.sh
```

**Tiempo estimado:** 10-15 minutos

---

## ✅ Qué Instala el Script

### Software Base
- ✅ **Python 3.11+** - Runtime para scripts
- ✅ **MySQL Server 8.0** - Base de datos
- ✅ **Grafana 10.x** - Dashboard y visualización

### Configuración Automática
- ✅ Base de datos `snapmirror_monitoring` creada
- ✅ Usuario MySQL `snapmirror_user` configurado
- ✅ Schema completo (tablas, vistas, índices)
- ✅ Dependencias Python instaladas
- ✅ Servicios iniciados automáticamente

### Credenciales por Defecto

**MySQL:**
- Root password: `NetApp123!`
- App user: `snapmirror_user`
- App password: `SnapMirror123!`
- Database: `snapmirror_monitoring`

**Grafana:**
- URL: `http://localhost:3000`
- User: `admin`
- Password: `admin` (cambiar en primer login)

---

## 🧪 Verificación Post-Instalación

### 1. Verificar Servicios

**Windows:**
```powershell
Get-Service MySQL80, grafana | Select-Object Name, Status
```

**Linux:**
```bash
systemctl status mysql grafana-server
```

### 2. Probar Conexión MySQL

```powershell
# Windows
& "C:\tools\mysql\current\bin\mysql.exe" -u snapmirror_user -p"SnapMirror123!" -e "SHOW DATABASES;"
```

```bash
# Linux
mysql -u snapmirror_user -p'SnapMirror123!' -e "SHOW DATABASES;"
```

Debe mostrar: `snapmirror_monitoring`

### 3. Verificar Python

```powershell
python --version
python -m pip list | Select-String "netapp-ontap|PyMySQL|aiohttp"
```

### 4. Acceder a Grafana

Abrir navegador: `http://localhost:3000`
- Login: `admin` / `admin`

---

## 🎯 Primeros Pasos

### 1. Generar Datos de Prueba

```powershell
python generate_mock_csv.py --num-instances 50
```

### 2. Ejecutar Primera Recolección (Mock)

```powershell
python run_collector.py --mode mock --once
```

Verificar salida:
```
[1/50] Recolectando ontap-select-madrid-0001...
✓ ontap-select-madrid-0001: 3 relaciones procesadas
...
✓ Recolección completada en XX segundos
```

### 3. Importar Dashboard en Grafana

1. Abrir Grafana: `http://localhost:3000`
2. **Configuration** → **Data Sources** → **Add data source**
3. Seleccionar **MySQL**
4. Configurar:
   - Host: `localhost:3306`
   - Database: `snapmirror_monitoring`
   - User: `snapmirror_user`
   - Password: `SnapMirror123!`
5. Click **Save & Test**

6. **Dashboards** → **Import** → **Upload JSON**
7. Seleccionar: `grafana/snapmirror_dashboard.json`
8. Asignar datasource MySQL
9. Click **Import**

### 4. Verificar Dashboard

Deberías ver:
- ✅ Mapa con marcadores de instancias
- ✅ Estadísticas (instancias, relaciones, alertas)
- ✅ Tabla con relaciones SnapMirror
- ✅ Gráficas de tendencia

---

## 🔧 Troubleshooting

### Error: "MySQL no se puede conectar"

**Windows:**
```powershell
# Reiniciar servicio
Restart-Service MySQL80

# Verificar puerto
netstat -an | Select-String "3306"
```

**Linux:**
```bash
# Reiniciar servicio
sudo systemctl restart mysql

# Verificar puerto
sudo netstat -tlnp | grep 3306
```

### Error: "Grafana no responde"

**Windows:**
```powershell
Restart-Service grafana
```

**Linux:**
```bash
sudo systemctl restart grafana-server
```

### Error: "Python módulo no encontrado"

```powershell
pip install -r requirements.txt --force-reinstall
```

### Limpiar y Reiniciar

**Windows:**
```powershell
# Detener servicios
Stop-Service MySQL80, grafana

# Reiniciar base de datos
& "C:\tools\mysql\current\bin\mysql.exe" -u root -p"NetApp123!" -e "DROP DATABASE IF EXISTS snapmirror_monitoring;"
python init_database.py

# Reiniciar servicios
Start-Service MySQL80, grafana
```

**Linux:**
```bash
# Detener servicios
sudo systemctl stop mysql grafana-server

# Reiniciar base de datos
mysql -u root -p'NetApp123!' -e "DROP DATABASE IF EXISTS snapmirror_monitoring;"
python3 init_database.py

# Reiniciar servicios
sudo systemctl start mysql grafana-server
```

---

## 🌐 Configurar para ONTAP Real

Una vez que el Lab on Demand esté configurado con ONTAP:

### 1. Obtener Credenciales del Lab

Normalmente en Lab on Demand de NetApp:
- **IP Cluster:** Ver en la interfaz del lab
- **Usuario:** `admin`
- **Password:** Ver en la interfaz del lab (ej: `Netapp1!`)

### 2. Editar CSV con Instancias Reales

Editar `config/ontap_instances.csv`:

```csv
name,ip_address,latitude,longitude,location_name,username,password
ontap-lab-cluster1,192.168.0.101,40.4168,-3.7038,Lab Cluster 1,admin,Netapp1!
```

### 3. Cambiar Modo a Real

Editar `config/config.yaml`:

```yaml
collector:
  mode: real  # Cambiar de 'mock' a 'real'
```

### 4. Probar Conexión

```powershell
python run_collector.py --mode real --once
```

---

## 📊 Acceso Remoto (Opcional)

Si necesitas acceder desde fuera del Lab:

### Windows (Port Forwarding)

```powershell
# Permitir acceso externo a Grafana
netsh advfirewall firewall add rule name="Grafana" dir=in action=allow protocol=TCP localport=3000
```

### Linux (Firewall)

```bash
# Ubuntu/Debian
sudo ufw allow 3000/tcp

# RHEL/CentOS
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --reload
```

Acceder desde: `http://<IP-DEL-LAB>:3000`

---

## 🎓 Lab on Demand - Tips

### Persistencia

⚠️ **Importante:** Los Labs on Demand pueden ser **efímeros**. 

Para guardar tu progreso:
1. Exportar dashboard de Grafana (JSON)
2. Backup de MySQL:
   ```bash
   mysqldump -u root -p'NetApp123!' snapmirror_monitoring > backup.sql
   ```
3. Guardar archivos de configuración

### Snapshots del Lab

Si el Lab lo permite, crear snapshot después de:
- Instalación inicial completa
- Configuración de ONTAP
- Carga de datos de prueba

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisar logs:
   - `logs/collector.log`
   - MySQL: `/var/log/mysql/error.log` (Linux)
   - Grafana: `/var/log/grafana/grafana.log` (Linux)

2. Verificar versiones:
   ```powershell
   python --version
   mysql --version
   grafana-server --version
   ```

3. Ejecutar en modo debug:
   ```powershell
   python run_collector.py --mode mock --once --log-level DEBUG
   ```
