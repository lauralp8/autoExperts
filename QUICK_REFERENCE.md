# Referencia Rápida - SnapMirror Monitor

## Credenciales por Defecto

```
MySQL root:      NetApp123!
MySQL app user:  snapmirror_user
MySQL app pass:  SnapMirror123!
Base de datos:   snapmirror_monitoring

Grafana user:    admin
Grafana pass:    admin (cambiar en primer login)
```

## Instalación Rápida (RHEL 8/9)

```bash
# 1. Clonar repositorio
git clone <repo> corme
cd corme

# 2. Instalar MySQL Community 8.0
chmod +x install_mysql_community.sh
sudo ./install_mysql_community.sh

# 3. Instalar dependencias Python
pip3 install -r requirements.txt

# 4. Generar datos de prueba
python3 generate_mock_csv.py --num-instances 50

# 5. Ejecutar collector (modo mock)
python3 run_collector.py --mode mock --once

# 6. Verificar
python3 check_setup.py
```

## Comandos Útiles MySQL

```bash
# Conectar a MySQL como root
mysql -u root -pNetApp123!

# Conectar con usuario de aplicación
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring

# Ver bases de datos
mysql -u root -pNetApp123! -e "SHOW DATABASES;"

# Ver tablas
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"

# Cargar schema
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql

# Resetear base de datos
mysql -u root -pNetApp123! <<EOF
DROP DATABASE IF EXISTS snapmirror_monitoring;
CREATE DATABASE snapmirror_monitoring;
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EOF
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql
```

## Comandos Útiles Collector

```bash
# Verificar configuración
python3 check_setup.py

# Generar CSV mock con N instancias
python3 generate_mock_csv.py --num-instances 100

# Ejecutar collector una vez (modo mock)
python3 run_collector.py --mode mock --once

# Ejecutar collector una vez (modo real)
python3 run_collector.py --mode real --once

# Ejecutar collector en continuo (cada 5 min)
python3 run_collector.py --mode real

# Ver estado de instancias
python3 remove_instance.py --list

# Probar conexión MySQL
python3 test_mysql_connection.py
```

## Troubleshooting

### MySQL no arranca

```bash
# Ver logs
sudo journalctl -u mysqld -n 50

# Ver estado
sudo systemctl status mysqld

# Reiniciar
sudo systemctl restart mysqld
```

### Tablas no se crearon

```bash
# Verificar que existe la BD
mysql -u root -pNetApp123! -e "SHOW DATABASES;"

# Cargar schema manualmente
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql

# Verificar tablas
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
```

### Grafana no conecta a MySQL

```bash
# 1. Verificar MySQL corriendo
sudo systemctl status mysqld

# 2. Probar conexión
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SELECT 1;"

# 3. En Grafana datasource, usar:
#    Host: 127.0.0.1:3306 (en vez de localhost:3306)
```

### Error de permisos MySQL

```bash
# Recrear usuario
mysql -u root -pNetApp123! <<EOF
DROP USER IF EXISTS 'snapmirror_user'@'localhost';
CREATE USER 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EOF
```

## Servicios

```bash
# MySQL
sudo systemctl status mysqld
sudo systemctl start mysqld
sudo systemctl stop mysqld
sudo systemctl restart mysqld

# Grafana
sudo systemctl status grafana-server
sudo systemctl start grafana-server
sudo systemctl stop grafana-server

# Collector (si está como servicio)
sudo systemctl status collector
sudo systemctl start collector
sudo systemctl stop collector
sudo journalctl -u collector -f
```

## Mantenimiento

```bash
# Ver estadísticas del histórico
python3 cleanup_history.py

# Simular limpieza (sin borrar)
python3 cleanup_history.py --days 30 --dry-run

# Borrar registros > 30 días
python3 cleanup_history.py --days 30

# Mantener solo última semana
python3 cleanup_history.py --days 7
```

**Recomendación:** Ejecutar semanalmente `python3 cleanup_history.py --days 30`

## URLs

- Grafana: http://localhost:3000
- MySQL: localhost:3306
