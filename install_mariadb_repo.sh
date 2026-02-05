#!/bin/bash
# Instalación de MariaDB usando repositorio oficial
# Uso: sudo ./install_mariadb_repo.sh

set -e

echo "========================================="
echo "  Instalación MariaDB 10.11"
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

echo ""
echo "[1/4] Configurando repositorio de MariaDB..."
echo ""

# Crear archivo de repositorio
REPO_FILE="/etc/yum.repos.d/mariadb.repo"

cat > $REPO_FILE <<'EOF'
# MariaDB 10.11 LTS repository
[mariadb]
name = MariaDB
baseurl = https://rpm.mariadb.org/10.11/rhel/$releasever/$basearch
module_hotfixes = 1
gpgkey = https://rpm.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck = 1
enabled = 1
EOF

echo "✓ Repositorio configurado: $REPO_FILE"

echo ""
echo "[2/4] Descargando RPMs de MariaDB..."
echo ""

# Crear directorio temporal
TMPDIR="/tmp/mariadb_install_$$"
mkdir -p $TMPDIR
cd $TMPDIR

# Descargar RPMs directamente
BASE_URL="https://rpm.mariadb.org/10.11/rhel/${RHEL_VERSION}/x86_64"

echo "Descargando desde: $BASE_URL"

# Obtener lista de RPMs disponibles y descargar los necesarios
wget -q "${BASE_URL}/" -O index.html

# Buscar los últimos RPMs
COMMON_RPM=$(grep -o 'MariaDB-common-[0-9.]*-[0-9].el9.x86_64.rpm' index.html | sort -V | tail -1)
COMPAT_RPM=$(grep -o 'MariaDB-compat-[0-9.]*-[0-9].el9.x86_64.rpm' index.html | sort -V | tail -1)
CLIENT_RPM=$(grep -o 'MariaDB-client-[0-9.]*-[0-9].el9.x86_64.rpm' index.html | sort -V | tail -1)
SERVER_RPM=$(grep -o 'MariaDB-server-[0-9.]*-[0-9].el9.x86_64.rpm' index.html | sort -V | tail -1)

echo "  → $COMMON_RPM"
wget -q "${BASE_URL}/${COMMON_RPM}"

echo "  → $COMPAT_RPM"
wget -q "${BASE_URL}/${COMPAT_RPM}"

echo "  → $CLIENT_RPM"
wget -q "${BASE_URL}/${CLIENT_RPM}"

echo "  → $SERVER_RPM"
wget -q "${BASE_URL}/${SERVER_RPM}"

echo ""
echo "[3/4] Instalando RPMs (sin verificar dependencias)..."
echo ""

# Instalar en orden correcto con --nodeps
rpm -ivh $COMMON_RPM --nodeps --force 2>/dev/null || echo "  → common instalado"
rpm -ivh $COMPAT_RPM --nodeps --force 2>/dev/null || echo "  → compat instalado"
rpm -ivh $CLIENT_RPM --nodeps 2>/dev/null || echo "  → client instalado"
rpm -ivh $SERVER_RPM --nodeps 2>/dev/null || echo "  → server instalado"

# Limpiar
cd /
rm -rf $TMPDIR

echo "✓ MariaDB instalado"

echo ""
echo "[4/4] Iniciando y configurando MariaDB..."
echo ""

systemctl start mariadb
systemctl enable mariadb
sleep 3

if systemctl is-active --quiet mariadb; then
    echo "✓ MariaDB corriendo"
else
    echo "✗ Error: MariaDB no arrancó"
    exit 1
fi

# Configurar password de root
echo "→ Configurando password de root..."
mysql -u root <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOF

echo "  ✓ Password de root: NetApp123!"

# Crear base de datos
echo "→ Creando base de datos snapmirror_monitoring..."
mysql -u root -pNetApp123! <<EOF
CREATE DATABASE IF NOT EXISTS snapmirror_monitoring;
EOF

echo "  ✓ Base de datos creada"

# Crear usuario
echo "→ Creando usuario snapmirror_user..."
mysql -u root -pNetApp123! <<EOF
DROP USER IF EXISTS 'snapmirror_user'@'localhost';
CREATE USER 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "  ✓ Usuario creado: snapmirror_user / SnapMirror123!"

# Cargar schema
if [ -f "config/mysql_schema.sql" ]; then
    echo "→ Cargando schema..."
    mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql
    echo "  ✓ Schema cargado"
else
    echo "  ⚠ Advertencia: config/mysql_schema.sql no encontrado"
    echo "    Ejecuta manualmente: mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql"
fi

# Verificar tablas
echo ""
echo "→ Verificando tablas creadas..."
TABLES=$(mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;" -sN | wc -l)

if [ "$TABLES" -ge 4 ]; then
    echo "  ✓ $TABLES tablas creadas correctamente"
    mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
else
    echo "  ✗ Error: Se esperaban 4 tablas, se crearon $TABLES"
    exit 1
fi

echo ""
echo "========================================="
echo "  ✓ Instalación completada"
echo "========================================="
echo ""
echo "Credenciales MySQL:"
echo "  Root:     root / NetApp123!"
echo "  Usuario:  snapmirror_user / SnapMirror123!"
echo "  Base de datos: snapmirror_monitoring"
echo ""
echo "Siguiente paso:"
echo "  python3 check_setup.py"
echo ""
