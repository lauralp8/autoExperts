#!/bin/bash
# =====================================================
# SnapMirror Monitor - Auto Setup Script  
# Para NetApp Lab on Demand (Linux/Ubuntu/RHEL)
# =====================================================

echo "========================================="
echo "SnapMirror Monitor - Auto Setup (Linux)"
echo "========================================="
echo ""

# Variables de configuración
MYSQL_ROOT_PASSWORD="NetApp123!"
MYSQL_APP_USER="snapmirror_user"
MYSQL_APP_PASSWORD="SnapMirror123!"
MYSQL_DATABASE="snapmirror_monitoring"

# Detectar distribución
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ No se puede detectar la distribución"
    exit 1
fi

echo "Distribución detectada: $OS"
echo ""

# =====================================================
# 1. VERIFICAR HERRAMIENTAS BÁSICAS
# =====================================================
echo "[1/6] Verificando herramientas básicas..."
echo "✓ Herramientas básicas verificadas"

# =====================================================
# 2. INSTALAR PYTHON 3
# =====================================================
echo ""
echo "[2/6] Verificando Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instálalo manualmente."
    exit 1
else
    echo "✓ Python ya instalado: $(python3 --version)"
fi

# =====================================================
# 3. INSTALAR MARIADB (desde RPM directo)
# =====================================================
echo ""
echo "[3/6] Instalando MariaDB..."

if rpm -q mariadb-server &>/dev/null; then
    echo "✓ MariaDB ya instalado"
    systemctl start mariadb 2>/dev/null || true
    systemctl enable mariadb 2>/dev/null || true
else
    echo "Descargando MariaDB desde mirror oficial..."
    
    # Descargar RPMs de MariaDB 10.11 (compatible RHEL 9)
    MARIADB_VERSION="10.11.6"
    MARIADB_BASE_URL="https://archive.mariadb.org/mariadb-${MARIADB_VERSION}/yum/rhel/9/x86_64"
    
    mkdir -p /tmp/mariadb_install
    cd /tmp/mariadb_install
    
    wget -q "${MARIADB_BASE_URL}/MariaDB-server-${MARIADB_VERSION}-1.el9.x86_64.rpm" || {
        echo "⚠ No se pudo descargar MariaDB, usando versión del sistema si existe"
        cd - > /dev/null
    }
    wget -q "${MARIADB_BASE_URL}/MariaDB-client-${MARIADB_VERSION}-1.el9.x86_64.rpm" 2>/dev/null || true
    wget -q "${MARIADB_BASE_URL}/MariaDB-common-${MARIADB_VERSION}-1.el9.x86_64.rpm" 2>/dev/null || true
    wget -q "${MARIADB_BASE_URL}/MariaDB-shared-${MARIADB_VERSION}-1.el9.x86_64.rpm" 2>/dev/null || true
    
    # Instalar RPMs
    if [ -f "MariaDB-server-${MARIADB_VERSION}-1.el9.x86_64.rpm" ]; then
        rpm -ivh --nodeps MariaDB-*.rpm 2>/dev/null || {
            echo "⚠ Instalación de RPMs falló, continuando..."
        }
        cd - > /dev/null
        rm -rf /tmp/mariadb_install
        
        systemctl start mariadb 2>/dev/null || systemctl start mysql 2>/dev/null || true
        systemctl enable mariadb 2>/dev/null || systemctl enable mysql 2>/dev/null || true
        echo "✓ MariaDB instalado"
    else
        cd - > /dev/null
        echo "⚠ No se pudo instalar MariaDB automáticamente"
    fi
fi

# Configurar MariaDB
echo "  ⚙ Configurando MariaDB..."
mysql -u root <<EOF 2>/dev/null
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';
FLUSH PRIVILEGES;
EOF
echo "✓ MariaDB configurado"

# =====================================================
# 4. INSTALAR GRAFANA (desde RPM directo)
# =====================================================
echo ""
echo "[4/6] Instalando Grafana..."

if rpm -q grafana &>/dev/null; then
    echo "✓ Grafana ya instalado"
    systemctl start grafana-server 2>/dev/null || true
    systemctl enable grafana-server 2>/dev/null || true
else
    echo "Descargando Grafana desde sitio oficial..."
    
    # Descargar última versión de Grafana para RHEL 9
    GRAFANA_VERSION="10.2.3"
    GRAFANA_RPM="grafana-${GRAFANA_VERSION}-1.x86_64.rpm"
    GRAFANA_URL="https://dl.grafana.com/oss/release/${GRAFANA_RPM}"
    
    cd /tmp
    wget -q "$GRAFANA_URL" -O "$GRAFANA_RPM" || {
        echo "⚠ No se pudo descargar Grafana"
    }
    
    if [ -f "$GRAFANA_RPM" ]; then
        rpm -ivh --nodeps "$GRAFANA_RPM" 2>/dev/null || {
            echo "⚠ Error instalando Grafana RPM"
        }
        rm -f "$GRAFANA_RPM"
        
        systemctl daemon-reload 2>/dev/null || true
        systemctl start grafana-server 2>/dev/null || true
        systemctl enable grafana-server 2>/dev/null || true
        echo "✓ Grafana instalado"
    else
        echo "⚠ No se pudo instalar Grafana automáticamente"
    fi
    --no-warn-script-location 2>/dev/null || true
python3 -m pip install netapp-ontap requests PyMySQL PyYAML aiohttp --quiet --no-warn-script-location 2>/dev/null || {
    echo "⚠ Algunas dependencias Python pueden no haberse instalado"
}
fi

# =====================================================
# 5. INSTALAR DEPENDENCIAS PYTHON
# =====================================================
echo ""
echo "[5/6] Instalando dependencias Python..."
python3 -m pip install --upgrade pip --quiet 2>/dev/null || true
python3 -m pip install netapp-ontap requests PyMySQL PyYAML aiohttp --quiet 2>/dev/null || true
echo "✓ Dependencias Python instaladas"

# =====================================================
# 6. INICIALIZAR BASE DE DATOS
# =====================================================
echo ""
echo "[6/6] Inicializando base de datos..."

mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF 2>/dev/null
CREATE DATABASE IF NOT EXISTS $MYSQL_DATABASE;
CREATE USER IF NOT EXISTS '$MYSQL_APP_USER'@'localhost' IDENTIFIED BY '$MYSQL_APP_PASSWORD';
GRANT ALL PRIVILEGES ON ${MYSQL_DATABASE}.* TO '$MYSQL_APP_USER'@'localhost';
FLUSH PRIVILEGES;
EOF
echo "✓ Base de datos creada"

if [ -f "config/mysql_schema.sql" ]; then
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" $MYSQL_DATABASE < config/mysql_schema.sql 2>/dev/null
    echo "✓ Schema MySQL creado"
fi

# Actualizar config.yaml
if [ -f "config/config.yaml" ]; then
    sed -i "s/password: change_me_in_production/password: $MYSQL_APP_PASSWORD/" config/config.yaml
    echo "✓ Configuración actualizada"
fi

mkdir -p logs

echo ""
echo "========================================="
echo "✓ INSTALACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "Servicios:"
echo "  • MariaDB (Puerto 3306)"
echo "  • Grafana: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "Credenciales:"
echo "  MariaDB: root / $MYSQL_ROOT_PASSWORD"
echo "  Grafana: admin / admin"
echo ""
echo "Próximos pasos:"
echo "  python3 generate_mock_csv.py --num-instances 50"
echo "  python3 run_collector.py --mode mock --once"
echo ""
echo "¡Listo! 🚀"
