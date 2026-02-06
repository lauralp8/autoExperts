#!/bin/bash
# Instalación de MySQL Community 8.0 con RPMs directos
# Uso: sudo ./install_mysql_community.sh

set -e

echo "========================================="
echo "  Instalación MySQL Community 8.0"
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
echo "[1/3] Descargando MySQL Community RPMs..."
echo ""

# Crear directorio temporal
TMPDIR="/tmp/mysql_install_$$"
mkdir -p $TMPDIR
cd $TMPDIR

# MySQL Community 8.0 para RHEL (versión dinámica)
MYSQL_REPO_RPM="mysql80-community-release-el${RHEL_VERSION}-1.noarch.rpm"
MYSQL_REPO_URL="https://dev.mysql.com/get/${MYSQL_REPO_RPM}"

echo "→ Descargando repositorio MySQL..."
if curl -L -o ${MYSQL_REPO_RPM} ${MYSQL_REPO_URL} 2>/dev/null; then
    echo "  ✓ Descargado desde dev.mysql.com"
elif wget -q -O ${MYSQL_REPO_RPM} ${MYSQL_REPO_URL} 2>/dev/null; then
    echo "  ✓ Descargado desde dev.mysql.com"
else
    echo "  ✗ Error descargando repositorio"
    exit 1
fi

echo ""
echo "[2/3] Instalando repositorio MySQL..."
echo ""

rpm -ivh ${MYSQL_REPO_RPM} --force || true

echo "✓ Repositorio MySQL instalado"

echo ""
echo "→ Descargando paquetes MySQL desde repositorio..."
echo ""

# Descargar solo los RPMs esenciales (sin usar dnf install)
cd $TMPDIR

# URLs directas del repositorio MySQL con versión dinámica
BASE_URL="https://repo.mysql.com/yum/mysql-8.0-community/el/${RHEL_VERSION}/x86_64"

# Lista de paquetes a descargar (orden correcto)
PACKAGES=(
    "mysql-community-common-8.0.40-1.el${RHEL_VERSION}.x86_64.rpm"
    "mysql-community-client-plugins-8.0.40-1.el${RHEL_VERSION}.x86_64.rpm"
    "mysql-community-libs-8.0.40-1.el${RHEL_VERSION}.x86_64.rpm"
    "mysql-community-client-8.0.40-1.el${RHEL_VERSION}.x86_64.rpm"
    "mysql-community-icu-data-files-8.0.40-1.el${RHEL_VERSION}.x86_64.rpm"
    "mysql-community-server-8.0.40-1.el${RHEL_VERSION}.x86_64.rpm"
)

echo "Descargando paquetes MySQL..."
for pkg in "${PACKAGES[@]}"; do
    echo "  → ${pkg}"
    if curl -f -L -o "${pkg}" "${BASE_URL}/${pkg}" 2>/dev/null; then
        echo "    ✓ Descargado"
    elif wget -q -O "${pkg}" "${BASE_URL}/${pkg}" 2>/dev/null; then
        echo "    ✓ Descargado"
    else
        echo "    ✗ Error descargando ${pkg}"
        echo "    ⚠️  Intentando continuar..."
    fi
done

echo ""
echo "[3/3] Instalando MySQL Community Server..."
echo ""

# Instalar en orden correcto
echo "→ Instalando paquetes..."
for pkg in "${PACKAGES[@]}"; do
    if [ -f "${pkg}" ]; then
        echo "  → Instalando ${pkg}..."
        rpm -ivh "${pkg}" --nodeps --force 2>/dev/null || rpm -Uvh "${pkg}" --nodeps --force || true
    fi
done

# Limpiar
cd /
rm -rf $TMPDIR

echo ""
echo "✓ MySQL instalado"

echo ""
echo "[4/4] Iniciando y configurando MySQL..."
echo ""

# Iniciar MySQL
systemctl start mysqld
systemctl enable mysqld
sleep 3

if systemctl is-active --quiet mysqld; then
    echo "✓ MySQL corriendo"
else
    echo "✗ Error: MySQL no arrancó"
    exit 1
fi

# Obtener password temporal de root
echo "→ Obteniendo password temporal de root..."
TEMP_PASS=$(grep 'temporary password' /var/log/mysqld.log 2>/dev/null | tail -1 | awk '{print $NF}')

if [ -z "$TEMP_PASS" ]; then
    echo "  ⚠️  No se encontró password temporal (posible reinstalación)"
    echo "  → Intentando conectar sin password..."
    
    # Resetear password si es necesario
    systemctl stop mysqld
    mysqld --skip-grant-tables --user=mysql &
    MYSQLD_PID=$!
    sleep 5
    
    mysql -u root <<EOF
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';
EOF
    
    kill $MYSQLD_PID 2>/dev/null || true
    sleep 2
    systemctl start mysqld
    sleep 3
else
    echo "  ✓ Password temporal: ${TEMP_PASS}"
    
    # Cambiar password de root
    echo "→ Configurando password de root..."
    mysql -u root -p"${TEMP_PASS}" --connect-expired-password <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';
FLUSH PRIVILEGES;
EOF
fi

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
TABLES=$(mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;" -sN 2>/dev/null | wc -l)

if [ "$TABLES" -ge 4 ]; then
    echo "  ✓ $TABLES tablas creadas correctamente"
    mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
else
    echo "  ⚠️  Se esperaban 4 tablas, se crearon $TABLES"
    echo "     (Esto es normal si config/mysql_schema.sql no existe aún)"
fi

echo ""
echo "========================================="
echo "  ✓ Instalación MySQL completada"
echo "========================================="
echo ""
echo "MySQL Community 8.0 instalado"
echo ""
echo "Credenciales:"
echo "  Root:     root / NetApp123!"
echo "  Usuario:  snapmirror_user / SnapMirror123!"
echo "  Base de datos: snapmirror_monitoring"
echo ""
echo "Siguiente paso:"
echo "  python3 check_setup.py"
echo ""
