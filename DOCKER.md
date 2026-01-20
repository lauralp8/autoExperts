# Docker Deployment Guide

## 🐋 Opción Docker Compose

Alternativa rápida al setup nativo. Levanta MySQL + Grafana en contenedores.

### Ventajas
- ✅ **Setup en 30 segundos** - Un solo comando
- ✅ **Aislamiento** - No afecta al sistema
- ✅ **Portabilidad** - Funciona igual en Windows/Linux/Mac
- ✅ **Fácil cleanup** - `docker-compose down -v`

### Desventajas
- ⚠️ Requiere Docker instalado
- ⚠️ Consume más RAM (~500MB)
- ⚠️ No funciona en todos los Labs on Demand

---

## 📋 Prerequisitos

### 1. Instalar Docker

**Windows:**
```powershell
# Descargar e instalar Docker Desktop
# https://www.docker.com/products/docker-desktop
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

**Linux (RHEL/CentOS):**
```bash
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### 2. Verificar Instalación

```bash
docker --version
docker-compose --version
```

---

## 🚀 Deployment Rápido

### Linux

```bash
cd ~/CORME

# Dar permisos de ejecución
chmod +x docker-start.sh

# Levantar servicios
./docker-start.sh
```

### Windows (PowerShell)

```powershell
cd "C:\Users\ca57934\OneDrive - NetApp Inc\Autocosas\CORME"

# Ejecutar
.\docker-start.ps1
```

**Tiempo:** ~30 segundos

---

## 📊 Servicios Desplegados

| Servicio | Puerto | URL | Credenciales |
|----------|--------|-----|--------------|
| **MySQL** | 3306 | `localhost:3306` | User: `snapmirror_user`<br>Pass: `SnapMirror123!` |
| **Grafana** | 3000 | `http://localhost:3000` | User: `admin`<br>Pass: `admin` |

---

## 🎯 Uso Post-Deployment

### 1. Instalar Dependencias Python

```bash
pip3 install -r requirements.txt
```

### 2. Configurar Conexión

El archivo `config/config.yaml` ya está configurado para Docker:

```yaml
database:
  host: localhost  # OK para Docker
  port: 3306
  user: snapmirror_user
  password: SnapMirror123!
```

### 3. Generar Datos de Prueba

```bash
python3 generate_mock_csv.py --num-instances 50
```

### 4. Ejecutar Collector

```bash
python3 run_collector.py --mode mock --once
```

### 5. Abrir Grafana

1. Navegar a: `http://localhost:3000`
2. Login: `admin` / `admin`
3. **Dashboards** → **Import**
4. Cargar: `grafana/snapmirror_dashboard.json`
5. El datasource MySQL ya está pre-configurado

---

## 🔧 Gestión de Contenedores

### Ver Logs

```bash
# Logs de todos los servicios
docker-compose logs -f

# Solo MySQL
docker-compose logs -f mysql

# Solo Grafana
docker-compose logs -f grafana
```

### Detener Servicios

```bash
docker-compose stop
```

### Reiniciar Servicios

```bash
docker-compose restart
```

### Detener y Eliminar Contenedores

```bash
# Mantiene los datos
docker-compose down

# Elimina TODO (incluye datos)
docker-compose down -v
```

### Ver Estado

```bash
docker-compose ps
```

Salida esperada:
```
NAME                   STATUS    PORTS
snapmirror_mysql       Up        0.0.0.0:3306->3306/tcp
snapmirror_grafana     Up        0.0.0.0:3000->3000/tcp
```

---

## 🗄️ Gestión de Base de Datos

### Conectar a MySQL

```bash
# Desde el host
mysql -h localhost -u snapmirror_user -p'SnapMirror123!' snapmirror_monitoring

# Desde dentro del contenedor
docker exec -it snapmirror_mysql mysql -u root -p'NetApp123!'
```

### Backup de BD

```bash
docker exec snapmirror_mysql mysqldump -u root -p'NetApp123!' snapmirror_monitoring > backup.sql
```

### Restaurar BD

```bash
docker exec -i snapmirror_mysql mysql -u root -p'NetApp123!' snapmirror_monitoring < backup.sql
```

### Reiniciar Schema

```bash
docker exec -i snapmirror_mysql mysql -u root -p'NetApp123!' <<EOF
DROP DATABASE IF EXISTS snapmirror_monitoring;
CREATE DATABASE snapmirror_monitoring;
EOF

# Recrear tablas
docker exec -i snapmirror_mysql mysql -u root -p'NetApp123!' snapmirror_monitoring < config/mysql_schema.sql
```

---

## 🐛 Troubleshooting

### Error: "Cannot connect to Docker daemon"

```bash
# Linux - Iniciar Docker
sudo systemctl start docker

# Verificar permisos
sudo usermod -aG docker $USER
# Logout y login de nuevo
```

### Error: "Port already in use"

```bash
# Ver qué proceso usa el puerto
# Linux
sudo netstat -tlnp | grep :3306
sudo netstat -tlnp | grep :3000

# Windows
netstat -ano | findstr :3306
netstat -ano | findstr :3000

# Detener servicio nativo si existe
sudo systemctl stop mysql
sudo systemctl stop grafana-server
```

### MySQL no se inicia

```bash
# Ver logs detallados
docker-compose logs mysql

# Reiniciar contenedor
docker-compose restart mysql

# Eliminar y recrear
docker-compose down -v
docker-compose up -d
```

### Grafana muestra "Bad Gateway"

```bash
# Esperar más tiempo (puede tardar en iniciar)
sleep 10

# Verificar que MySQL está listo
docker exec snapmirror_mysql mysqladmin ping -h localhost -u root -p'NetApp123!'

# Reiniciar Grafana
docker-compose restart grafana
```

---

## 🔄 Actualización de Imágenes

```bash
# Detener servicios
docker-compose down

# Actualizar imágenes
docker-compose pull

# Reiniciar
docker-compose up -d
```

---

## 💾 Persistencia de Datos

Los datos se guardan en **Docker Volumes**:

```bash
# Listar volumes
docker volume ls | grep corme

# Ver ubicación
docker volume inspect corme_mysql_data
docker volume inspect corme_grafana_data
```

Para **eliminar completamente** los datos:

```bash
docker-compose down -v
```

---

## 🌐 Acceso Remoto

Si quieres acceder desde otra máquina:

### 1. Modificar docker-compose.yml

Cambiar:
```yaml
ports:
  - "3000:3000"  # Solo localhost
```

Por:
```yaml
ports:
  - "0.0.0.0:3000:3000"  # Todas las interfaces
```

### 2. Abrir Firewall

**Linux:**
```bash
sudo firewall-cmd --add-port=3000/tcp --permanent
sudo firewall-cmd --reload
```

**Windows:**
```powershell
New-NetFirewallRule -DisplayName "Grafana" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

### 3. Acceder

```
http://<IP-DEL-SERVIDOR>:3000
```

---

## 📊 Comparativa: Docker vs Instalación Nativa

| Aspecto | Docker | Nativo (setup_lab.sh) |
|---------|--------|----------------------|
| **Setup Time** | 30 segundos | 10-15 minutos |
| **Requisitos** | Docker instalado | Permisos sudo |
| **Aislamiento** | ✅ Completo | ❌ Afecta sistema |
| **Portabilidad** | ✅ Alta | ⚠️ Depende del SO |
| **Performance** | ⚠️ Overhead mínimo | ✅ Nativo |
| **Cleanup** | ✅ `docker-compose down -v` | ⚠️ Manual |
| **Labs sin Docker** | ❌ No funciona | ✅ Funciona |

---

## 🎓 Recomendación

**Usa Docker si:**
- ✅ Tienes Docker disponible en el lab
- ✅ Quieres setup ultra-rápido
- ✅ Necesitas limpiar fácilmente después

**Usa Instalación Nativa si:**
- ✅ El lab no permite Docker
- ✅ Prefieres control total
- ✅ Quieres máximo performance

Ambas opciones **funcionan con el mismo código Python** - solo cambia la infraestructura.

---

## 📞 Comandos de Referencia Rápida

```bash
# Levantar
./docker-start.sh

# Ver estado
docker-compose ps

# Logs
docker-compose logs -f

# Detener
docker-compose stop

# Reiniciar
docker-compose restart

# Eliminar
docker-compose down

# Eliminar con datos
docker-compose down -v

# Acceso MySQL
docker exec -it snapmirror_mysql mysql -u root -p'NetApp123!'

# Backup
docker exec snapmirror_mysql mysqldump -u root -p'NetApp123!' snapmirror_monitoring > backup.sql
```
