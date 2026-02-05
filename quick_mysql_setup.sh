#!/bin/bash
# Script ULTRA RÁPIDO para configurar MariaDB si ya está instalado
# Uso: sudo ./quick_mysql_setup.sh

echo "========================================="
echo "  Setup Rápido de MySQL/MariaDB"
echo "========================================="
echo ""

# Iniciar MariaDB si está parado
echo "[1/3] Iniciando MariaDB..."
systemctl start mariadb 2>/dev/null || systemctl start mysqld 2>/dev/null
systemctl enable mariadb 2>/dev/null || systemctl enable mysqld 2>/dev/null
sleep 2

if systemctl is-active --quiet mariadb || systemctl is-active --quiet mysqld; then
    echo "✓ MariaDB corriendo"
else
    echo "✗ MariaDB no está corriendo"
    echo ""
    echo "Intenta instalarlo primero:"
    echo "  sudo dnf install -y mariadb-server mariadb"
    echo "  sudo systemctl start mariadb"
    exit 1
fi

echo ""
echo "[2/3] Configurando base de datos..."

# Configurar sin password primero (instalación nueva)
if mysql -u root -e "SELECT 1;" &>/dev/null; then
    echo "  → Acceso sin password, configurando..."
    mysql -u root <<-'EOF'
-- Configurar root
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';
FLUSH PRIVILEGES;

-- Crear base de datos y usuario
CREATE DATABASE IF NOT EXISTS snapmirror_monitoring;
CREATE USER IF NOT EXISTS 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EOF
    echo "  ✓ Configurado"
elif mysql -u root -pNetApp123! -e "SELECT 1;" &>/dev/null; then
    echo "  → Password root ya configurado, creando usuario..."
    mysql -u root -pNetApp123! <<-'EOF'
CREATE DATABASE IF NOT EXISTS snapmirror_monitoring;
CREATE USER IF NOT EXISTS 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EOF
    echo "  ✓ Usuario creado"
else
    echo "  ✗ No se pudo acceder a MySQL"
    echo ""
    echo "Intenta ejecutar manualmente:"
    echo "  sudo mysql -u root"
    echo ""
    echo "Y dentro de MySQL:"
    echo "  ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';"
    echo "  CREATE DATABASE snapmirror_monitoring;"
    echo "  CREATE USER 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';"
    echo "  GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';"
    echo "  FLUSH PRIVILEGES;"
    exit 1
fi

echo ""
echo "[3/3] Cargando schema..."

if [ -f "config/mysql_schema.sql" ]; then
    if mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql 2>/dev/null; then
        echo "✓ Schema cargado"
        
        # Mostrar tablas
        TABLES=$(mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -se "SHOW TABLES;")
        TABLE_COUNT=$(echo "$TABLES" | wc -l)
        
        echo ""
        echo "Tablas creadas ($TABLE_COUNT):"
        echo "$TABLES" | sed 's/^/  - /'
    else
        echo "✗ Error cargando schema"
    fi
else
    echo "✗ No se encontró config/mysql_schema.sql"
fi

echo ""
echo "========================================="
echo "✓ LISTO"
echo "========================================="
echo ""
echo "Verificar:"
echo "  python3 test_mysql_connection.py"
echo "  python3 check_setup.py"
echo ""
echo "Siguiente paso:"
echo "  cd config/ && mv ontap_instances_mock.csv ontap_instances.csv && cd .."
echo "  python3 run_collector.py --mode mock --once"
echo ""
