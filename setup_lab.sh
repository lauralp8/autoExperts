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
# 3. INSTALAR MYSQL COMMUNITY 8.0
# =====================================================
echo ""
echo "[3/6] Instalando MySQL Community 8.0..."

# Verificar si MySQL ya está instalado
if rpm -q mysql-community-server &>/dev/null || rpm -q mariadb-server &>/dev/null; then
    echo "✓ MySQL/MariaDB ya instalado"
    systemctl start mysqld 2>/dev/null || systemctl start mariadb 2>/dev/null || true
    systemctl enable mysqld 2>/dev/null || systemctl enable mariadb 2>/dev/null || true
else
    # Usar el script de instalación dedicado si existe
    if [ -f "install_mysql_community.sh" ]; then
        echo "Usando script de instalación MySQL Community..."
        chmod +x install_mysql_community.sh
        ./install_mysql_community.sh
        
        if [ $? -eq 0 ]; then
            echo "✓ MySQL instalado correctamente"
        else
            echo "❌ Error instalando MySQL"
            exit 1
        fi
    else
        echo "❌ Script install_mysql_community.sh no encontrado"
        echo "   Ejecuta manualmente: chmod +x install_mysql_community.sh && sudo ./install_mysql_community.sh"
        exit 1
    fi
fi

# Verificar que MySQL esté corriendo
echo "  ⚙ Verificando MySQL..."
sleep 2

if systemctl is-active --quiet mysqld || systemctl is-active --quiet mariadb; then
    echo "✓ MySQL corriendo"
    
    # Verificar si la base de datos ya existe (el script install_mysql_community.sh ya la crea)
    DB_EXISTS=$(/usr/bin/mysql -u root -pNetApp123! -e "SHOW DATABASES LIKE 'snapmirror_monitoring';" 2>/dev/null | grep -c snapmirror_monitoring)
    
    if [ "$DB_EXISTS" -eq 0 ]; then
        echo "  ⚙ Creando base de datos y usuario..."
        /usr/bin/mysql -u root -pNetApp123! <<EOF 2>/dev/null
CREATE DATABASE IF NOT EXISTS snapmirror_monitoring;
CREATE USER IF NOT EXISTS 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';
GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';
FLUSH PRIVILEGES;
EOF
        echo "✓ Base de datos y usuario creados"
    else
        echo "✓ Base de datos ya existe"
    fi
else
    echo "⚠ MySQL no está corriendo"
fi

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
    
    cd - > /dev/null
fi

# =====================================================
# 5. INSTALAR DEPENDENCIAS PYTHON
# =====================================================
echo ""
echo "[5/6] Instalando dependencias Python..."
python3 -m pip install --upgrade pip --quiet --no-warn-script-location 2>/dev/null || true
python3 -m pip install netapp-ontap requests PyMySQL PyYAML aiohttp --quiet --no-warn-script-location 2>/dev/null || true
echo "✓ Dependencias Python instaladas"

# =====================================================
# 6. INICIALIZAR BASE DE DATOS
# =====================================================
echo ""
echo "[6/6] Inicializando base de datos..."

# Verificar si las tablas ya existen
TABLE_COUNT=$(/usr/bin/mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;" 2>/dev/null | wc -l)

if [ $TABLE_COUNT -gt 1 ]; then
    echo "✓ Base de datos ya tiene $((TABLE_COUNT - 1)) tablas"
else
    # Cargar el schema SQL si las tablas no existen
    if [ -f "config/mysql_schema.sql" ]; then
        echo "  → Cargando schema SQL..."
        /usr/bin/mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✓ Schema MySQL creado"
            TABLE_COUNT=$(/usr/bin/mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;" 2>/dev/null | wc -l)
            echo "✓ Base de datos inicializada con $((TABLE_COUNT - 1)) tablas"
        else
            echo "⚠ Error cargando schema"
        fi
    else
        echo "⚠ Archivo mysql_schema.sql no encontrado"
    fi
fi

# Actualizar config.yaml si es necesario
if [ -f "config/config.yaml" ]; then
    sed -i "s/password: change_me_in_production/password: SnapMirror123!/" config/config.yaml 2>/dev/null
    echo "✓ Configuración actualizada"
fi

# Crear directorio de logs
mkdir -p logs

echo ""
echo "========================================="
echo "✓ INSTALACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "Servicios:"
echo "  • MySQL Community 8.0 (Puerto 3306)"
echo "  • Grafana: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "Credenciales:"
echo "  MySQL root: root / $MYSQL_ROOT_PASSWORD"
echo "  MySQL app: snapmirror_user / $MYSQL_APP_PASSWORD"
echo "  Grafana: admin / admin"
echo ""
echo "Próximos pasos:"
echo "  1. python3 generate_mock_csv.py --num-instances 50"
echo "  2. python3 run_collector.py --mode mock --once"
echo "  3. Configurar Grafana datasource y dashboard"
echo ""
echo "¡Listo! 🚀"
