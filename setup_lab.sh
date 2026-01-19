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
GRAFANA_ADMIN_PASSWORD="admin"

# Detectar distribución
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "❌ No se puede detectar la distribución"
    exit 1
fi

echo "Distribución detectada: $OS $VERSION"
echo ""

# =====================================================
# 1. ACTUALIZAR SISTEMA (OPCIONAL)
# =====================================================
echo "[1/6] Actualizando sistema (opcional)..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo apt-get update -qq 2>/dev/null || echo "⚠ No se pudo actualizar repositorios (continuando...)"
    sudo apt-get install -y wget curl gnupg2 software-properties-common 2>/dev/null || true
elif [ "$OS" = "rhel" ] || [ "$OS" = "centos" ] || [ "$OS" = "rocky" ]; then
    sudo yum update -y -q 2>/dev/null || echo "⚠ No se pudo actualizar sistema (continuando...)"
    sudo yum install -y wget curl 2>/dev/null || echo "⚠ wget/curl puede que ya estén instalados"
fi
echo "✓ Paso de actualización completado"

# =====================================================
# 2. INSTALAR PYTHON 3
# =====================================================
echo ""
echo "[2/6] Instalando Python 3..."
if ! command -v python3 &> /dev/null; then
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt-get install -y python3 python3-pip python3-venv || {
            echo "❌ Error instalando Python"
            exit 1
        }
    elif [ "$OS" = "rhel" ] || [ "$OS" = "centos" ] || [ "$OS" = "rocky" ]; then
        sudo yum install -y python3 python3-pip || {
            echo "❌ Error instalando Python"
            exit 1
        }
    fi
    echo "✓ Python instalado"
else
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python ya instalado: $PYTHON_VERSION"
fi

# =====================================================
# 3. INSTALAR MYSQL
# =====================================================
echo ""
echo "[3/6] Instalando MySQL Server..."
if ! command -v mysql &> /dev/null; then
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        # Preconfigurar password de root
        sudo debconf-set-selections <<< "mysql-server mysql-server/root_password password $MYSQL_ROOT_PASSWORD"
        sudo debconf-set-selections <<< "mysql-server mysql-server/root_password_again password $MYSQL_ROOT_PASSWORD"
        
        sudo apt-get install -y mysql-server || {
            echo "❌ Error instalando MySQL"
            exit 1
        }
        sudo systemctl start mysql
        sudo systemctl enable mysql
        
    elif [ "$OS" = "rhel" ] || [ "$OS" = "centos" ] || [ "$OS" = "rocky" ]; then
        sudo yum install -y mysql-server || {
            echo "❌ Error instalando MySQL. Intentando con mariadb-server..."
            sudo yum install -y mariadb-server || {
                echo "❌ Error instalando base de datos"
                exit 1
            }
        }
        sudo systemctl start mysqld 2>/dev/null || sudo systemctl start mariadb
        sudo systemctl enable mysqld 2>/dev/null || sudo systemctl enable mariadb
        
        # Obtener password temporal (solo MySQL, no MariaDB)
        if [ -f /var/log/mysqld.log ]; then
            TEMP_PASSWORD=$(sudo grep 'temporary password' /var/log/mysqld.log 2>/dev/null | tail -1 | awk '{print $NF}')
            
            if [ ! -z "$TEMP_PASSWORD" ]; then
                # Cambiar password de MySQL
                mysql -u root -p"$TEMP_PASSWORD" --connect-expired-password <<EOF 2>/dev/null
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';
FLUSH PRIVILEGES; 2>/dev/null || mysql -u root <<EOF 2>/dev/null
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOF
echo "✓ MySQL asegurado (o ya estaba configurado)stalado"
    sudo systemctl start mysql 2>/dev/null || sudo systemctl start mysqld 2>/dev/null || sudo systemctl start mariadb 2>/dev/null
fi

# Secure installation
echo "  ⚙ Asegurando instalación MySQL..."
mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOF
echo "✓ MySQL asegurado"

# =====================================================
# 4. INSTALAR GRAFANA
# =====================================================
echo ""
echo "[4/6] Instalando Grafana..."
if ! command -v grafana-server &> /dev/null; then
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        # Añadir repositorio de Grafana
        sudo mkdir -p /etc/apt/keyrings/
        wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
        echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
        
        sudo apt-get update -qq
        sudo apt-get install -y grafana || {
            echo "❌ Error instalando Grafana"
            exit 1
        }
        
    elif [ "$OS" = "rhel" ] || [ "$OS" = "centos" ] || [ "$OS" = "rocky" ]; then
        # Añadir repositorio de Grafana
        cat <<EOF | sudo tee /etc/yum.repos.d/grafana.repo
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
        
        sudo yum install -y grafana || {
            echo "❌ Error instalando Grafana"
            exit 1
        }
    fi
    
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

# Actualizar pip
python3 -m pip install --upgrade pip --quiet

# Instalar dependencias del proyecto
if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt --quiet
    echo "✓ Dependencias Python instaladas"
else
    echo "⚠ requirements.txt no encontrado, instalando manualmente..."
    python3 -m pip install netapp-ontap requests PyMySQL PyYAML aiohttp --quiet
    echo "✓ Dependencias básicas instaladas"
fi
 (probar con y sin password)
mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF 2>/dev/null || mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS $MYSQL_DATABASE;
CREATE USER IF NOT EXISTS '$MYSQL_APP_USER'@'localhost' IDENTIFIED BY '$MYSQL_APP_PASSWORD';
GRANT ALL PRIVILEGES ON ${MYSQL_DATABASE}.* TO '$MYSQL_APP_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

if [ $? -eq 0 ]; then
    echo "✓ Base de datos y usuario creados"
else
    echo "❌ Error creando base de datos"
    exit 1
fi

# Ejecutar schema SQL
if [ -f "config/mysql_schema.sql" ]; then
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" $MYSQL_DATABASE < config/mysql_schema.sql 2>/dev/null || \
    mysql -u root $MYSQL_DATABASE < config/mysql_schema.sql 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✓ Schema MySQL creado"
    else
        echo "⚠ Error creando schema (puede que necesites ejecutar init_database.py manualmente)"
    fiDATABASE}.* TO '$MYSQL_APP_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

# Ejecutar schema SQL
if [ -f "config/mysql_schema.sql" ]; then
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" $MYSQL_DATABASE < config/mysql_schema.sql
    echo "✓ Schema MySQL creado"
else
    echo "⚠ Schema SQL no encontrado en config/mysql_schema.sql"
fi

# Actualizar config.yaml con las credenciales
if [ -f "config/config.yaml" ]; then
    echo "  ⚙ Actualizando config.yaml..."
    sed -i "s/password: change_me_in_production/password: $MYSQL_APP_PASSWORD/" config/config.yaml
    sed -i "s/user: snapmirror_user/user: $MYSQL_APP_USER/" config/config.yaml
    echo "✓ Configuración actualizada"
fi

# Crear directorio de logs
mkdir -p logs

# =====================================================
# CONFIGURAR FIREWALL (opcional)
# =====================================================
echo ""
echo "Configurando firewall (opcional)..."
if command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=3000/tcp  # Grafana
    sudo firewall-cmd --reload
    echo "✓ Puertos abiertos en firewall"
elif command -v ufw &> /dev/null; then
    sudo ufw allow 3000/tcp  # Grafana
    echo "✓ Puertos abiertos en firewall"
fi

# =====================================================
# RESUMEN FINAL
# =====================================================
echo ""
echo "========================================="
echo "✓ INSTALACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "Servicios instalados:"
echo "  • Python $(python3 --version)"
echo "  • MySQL Server (Puerto 3306)"
echo "  • Grafana (Puerto 3000)"
echo ""
echo "Credenciales MySQL:"
echo "  • Root password: $MYSQL_ROOT_PASSWORD"
echo "  • App user: $MYSQL_APP_USER"
echo "  • App password: $MYSQL_APP_PASSWORD"
echo "  • Database: $MYSQL_DATABASE"
echo ""
echo "URLs:"
echo "  • Grafana: http://$(hostname -I | awk '{print $1}'):3000 (admin/admin)"
echo ""
echo "Próximos pasos:"
echo "  1. Generar datos de prueba:"
echo "     python3 generate_mock_csv.py --num-instances 50"
echo ""
echo "  2. Ejecutar collector en modo mock:"
echo "     python3 run_collector.py --mode mock --once"
echo ""
echo "  3. Abrir Grafana e importar dashboard:"
echo "     grafana/snapmirror_dashboard.json"
echo ""
echo "  4. Para ONTAP real, editar:"
echo "     config/ontap_instances.csv"
echo "     python3 run_collector.py --mode real --once"
echo ""
echo "========================================="

# Verificar servicios
echo ""
echo "Verificando servicios..."
if systemctl is-active --quiet mysql || systemctl is-active --quiet mysqld; then
    echo "  MySQL: ✓ Running"
else
    echo "  MySQL: ✗ Stopped"
fi

if systemctl is-active --quiet grafana-server; then
    echo "  Grafana: ✓ Running"
else
    echo "  Grafana: ✗ Stopped"
fi

echo ""
echo "¡Listo para usar! 🚀"
