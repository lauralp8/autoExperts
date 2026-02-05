#!/bin/bash
# Script manual para instalar MySQL/MariaDB en RHEL
# Uso: sudo ./install_mysql_manual.sh

set -e

echo "========================================="
echo "  Instalación Manual de MySQL/MariaDB"
echo "========================================="
echo ""

# Detectar si estamos en RHEL
if [ -f /etc/redhat-release ]; then
    echo "✓ Sistema RHEL/CentOS detectado"
else
    echo "⚠ Este script está diseñado para RHEL/CentOS"
    exit 1
fi

# Verificar si ya existe MySQL o MariaDB
if systemctl list-units --type=service --all | grep -qE 'mysqld|mariadb'; then
    echo "⚠ MySQL o MariaDB ya está instalado"
    systemctl status mysqld 2>/dev/null || systemctl status mariadb 2>/dev/null || true
    echo ""
    read -p "¿Quieres reinstalar? (s/N): " REINSTALL
    if [ "$REINSTALL" != "s" ] && [ "$REINSTALL" != "S" ]; then
        echo "Abortado. Continúa con la configuración manual."
        exit 0
    fi
fi

echo ""
echo "[1/4] Instalando MariaDB desde repositorios RHEL..."
echo ""

# Instalar MariaDB (disponible en repos de RHEL)
dnf install -y mariadb-server mariadb || yum install -y mariadb-server mariadb

echo ""
echo "[2/4] Iniciando servicio MariaDB..."
echo ""

systemctl start mariadb
systemctl enable mariadb
systemctl status mariadb --no-pager

echo ""
echo "[3/4] Configurando MariaDB..."
echo ""

# Configurar root password
ROOT_PASS="NetApp123!"

echo "Configurando password de root..."

# Asegurar MariaDB sin interacción
mysql -u root <<-EOF
-- Configurar password de root
ALTER USER 'root'@'localhost' IDENTIFIED BY '${ROOT_PASS}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOF

echo "✓ Password de root configurado"

echo ""
echo "[4/4] Creando base de datos y usuario..."
echo ""

# Crear base de datos y usuario
mysql -u root -p${ROOT_PASS} <<-EOF
CREATE DATABASE IF NOT EXISTS snapmirror_monitoring;
CREATE USER IF NOT EXISTS 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;

-- Mostrar resultado
SHOW DATABASES LIKE 'snapmirror%';
SELECT User, Host FROM mysql.user WHERE User = 'snapmirror_user';
EOF

echo ""
echo "✓ Base de datos creada"

echo ""
echo "[5/5] Cargando schema..."
echo ""

# Cargar schema si existe
if [ -f "config/mysql_schema.sql" ]; then
    mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql
    echo "✓ Schema cargado"
    
    # Verificar tablas
    echo ""
    echo "Tablas creadas:"
    mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
else
    echo "⚠ No se encontró config/mysql_schema.sql"
    echo "  Ejecuta manualmente: mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql"
fi

echo ""
echo "========================================="
echo "✓ INSTALACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "Credenciales:"
echo "  Root:     root / NetApp123!"
echo "  App User: snapmirror_user / SnapMirror123!"
echo "  Database: snapmirror_monitoring"
echo ""
echo "Verificar:"
echo "  systemctl status mariadb"
echo "  mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e 'SHOW TABLES;'"
echo ""
echo "Siguiente paso:"
echo "  python3 check_setup.py"
echo "  python3 test_mysql_connection.py"
echo ""
