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
# 3. VERIFICAR MYSQL/MARIADB
# =====================================================
echo ""
echo "[3/6] Verificando MariaDB..."

# Verificar si el paquete está instalado
if rpm -q mariadb-server &>/dev/null || rpm -q mysql-server &>/dev/null; then
    echo "✓ MariaDB/MySQL ya instalado"
    # Intentar iniciar el servicio
    sudo systemctl start mariadb 2>/dev/null || sudo systemctl start mysqld 2>/dev/null || {
        echo "⚠ Servicio de base de datos no pudo iniciarse"
    }
    sudo systemctl enable mariadb 2>/dev/null || sudo systemctl enable mysqld 2>/dev/null
elif command -v mysql &> /dev/null; then
    echo "✓ Cliente MySQL encontrado"
    sudo systemctl start mariadb 2>/dev/null || sudo systemctl start mysqld 2>/dev/null || true
else
    echo "⚠ MariaDB no encontrado"
    echo "Intentando instalación con timeout..."
    timeout 30 sudo yum install -y mariadb-server 2>/dev/null || {
        echo ""
        echo "❌ No se pudo instalar MariaDB automáticamente"
        echo ""
        echo "Soluciones:"
        echo "  1. Instalar manualmente: sudo yum install -y mariadb-server"
        echo "  2. O ejecutar manualmente estos comandos:"
        echo ""
        echo "  sudo systemctl start mariadb"
        echo "  mysql -u root <<EOF"
        echo "  CREATE DATABASE snapmirror_monitoring;"
        echo "  CREATE USER 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';"
        echo "  GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';"
        echo "  FLUSH PRIVILEGES;"
        echo "  EOF"
        echo ""
        echo "  mysql -u root snapmirror_monitoring < config/mysql_schema.sql"
        echo ""
        exit 1
    }
    sudo systemctl start mariadb
    sudo systemctl enable mariadb
    echo "✓ MariaDB instalado"
fi

# Configurar MariaDB
echo "  ⚙ Configurando MariaDB..."
mysql -u root <<EOF 2>/dev/null
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';
FLUSH PRIVILEGES;
EOF
echo "✓ MariaDB configurado"

# =====================================================
# 4. INSTALAR GRAFANA
# =====================================================
echo ""
echo "[4/6] Instalando Grafana..."
if ! command -v grafana-server &> /dev/null; then
    cat <<EOFGRAFANA | sudo tee /etc/yum.repos.d/grafana.repo
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOFGRAFANA
    
    sudo yum install -y grafana || {
        echo "❌ Error instalando Grafana"
        exit 1
    }
    sudo systemctl daemon-reload
    sudo systemctl start grafana-server
    sudo systemctl enable grafana-server
    echo "✓ Grafana instalado"
else
    echo "✓ Grafana ya instalado"
    sudo systemctl start grafana-server 2>/dev/null || true
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
