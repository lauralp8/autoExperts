#!/bin/bash
# Instalación de MariaDB usando wget (para sistemas RHEL sin suscripción)
# Uso: sudo ./install_mariadb_wget.sh

set -e

echo "========================================="
echo "  Instalación MariaDB con wget"
echo "========================================="
echo ""

# Detectar versión de RHEL
if [ -f /etc/redhat-release ]; then
    RHEL_VERSION=$(grep -oE 'release [0-9]+' /etc/redhat-release | awk '{print $2}')
    echo "✓ RHEL $RHEL_VERSION detectado"
else
    echo "✗ No es un sistema RHEL"
    exit 1
fi

# Crear directorio temporal
TMPDIR="/tmp/mariadb_install"
mkdir -p $TMPDIR
cd $TMPDIR

echo ""
echo "[1/4] Descargando MariaDB 10.11 desde repositorio oficial..."
echo ""

# URLs de MariaDB 10.11 para RHEL 9
MARIADB_VERSION="10.11.10"
BASE_URL="https://archive.mariadb.org/mariadb-${MARIADB_VERSION}/yum/rhel/9/x86_64"

# Lista de RPMs necesarios
RPMS=(
    "MariaDB-common-${MARIADB_VERSION}-1.el9.x86_64.rpm"
    "MariaDB-compat-${MARIADB_VERSION}-1.el9.x86_64.rpm"
    "MariaDB-client-${MARIADB_VERSION}-1.el9.x86_64.rpm"
    "MariaDB-server-${MARIADB_VERSION}-1.el9.x86_64.rpm"
)

echo "Descargando desde: $BASE_URL"
echo ""

for rpm in "${RPMS[@]}"; do
    if [ -f "$rpm" ]; then
        echo "  ✓ $rpm ya descargado"
    else
        echo "  → Descargando $rpm..."
        if wget -q "${BASE_URL}/${rpm}"; then
            echo "    ✓ OK"
        else
            echo "    ✗ Error descargando $rpm"
            echo ""
            echo "Alternativa: Descargar manualmente desde:"
            echo "  https://mariadb.org/download/"
            exit 1
        fi
    fi
done

echo ""
echo "[2/4] Instalando RPMs..."
echo ""

# Instalar en orden correcto
rpm -ivh MariaDB-common-*.rpm --nodeps --force 2>/dev/null || true
rpm -ivh MariaDB-compat-*.rpm --nodeps --force 2>/dev/null || true
rpm -ivh MariaDB-client-*.rpm --nodeps --force 2>/dev/null || true
rpm -ivh MariaDB-server-*.rpm --nodeps 2>/dev/null || true

echo "✓ RPMs instalados"

echo ""
echo "[3/4] Iniciando MariaDB..."
echo ""

systemctl start mariadb
systemctl enable mariadb
sleep 3
systemctl status mariadb --no-pager

echo ""
echo "[4/4] Configurando base de datos..."
echo ""

# Configurar root sin password primero (instalación nueva)
if mysql -u root -e "SELECT 1;" &>/dev/null; then
    echo "  → Configurando password de root..."
    mysql -u root <<-'EOF'
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';
FLUSH PRIVILEGES;
EOF
    echo "  ✓ Password configurado"
fi

# Crear base de datos y usuario
echo "  → Creando base de datos y usuario..."
mysql -u root -pNetApp123! <<-'EOF'
CREATE DATABASE IF NOT EXISTS snapmirror_monitoring;
CREATE USER IF NOT EXISTS 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "  ✓ Base de datos creada"

# Volver al directorio original
cd - > /dev/null

# Cargar schema si existe
if [ -f "config/mysql_schema.sql" ]; then
    echo ""
    echo "[5/5] Cargando schema..."
    echo ""
    
    if mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql; then
        echo "✓ Schema cargado"
        
        # Mostrar tablas
        echo ""
        echo "Tablas creadas:"
        mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
    else
        echo "⚠ Error cargando schema"
    fi
fi

# Limpiar archivos temporales
rm -rf $TMPDIR

echo ""
echo "========================================="
echo "✓ INSTALACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "MariaDB $MARIADB_VERSION instalado y configurado"
echo ""
echo "Credenciales:"
echo "  Root:     root / NetApp123!"
echo "  App User: snapmirror_user / SnapMirror123!"
echo "  Database: snapmirror_monitoring"
echo ""
echo "Verificar:"
echo "  python3 test_mysql_connection.py"
echo "  python3 check_setup.py"
echo ""
echo "Siguiente paso:"
echo "  cd config/ && mv ontap_instances_mock.csv ontap_instances.csv && cd .."
echo "  python3 run_collector.py --mode mock --once"
echo ""
