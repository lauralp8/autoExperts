#!/bin/bash
# Script manual para instalar MySQL/MariaDB en RHEL
# Uso: sudo ./install_mysql_manual.sh

echo "========================================="
echo "  Configuración de MySQL/MariaDB"
echo "========================================="
echo ""

# Detectar si estamos en RHEL
if [ -f /etc/redhat-release ]; then
    echo "✓ Sistema RHEL/CentOS detectado"
else
    echo "⚠ Este script está diseñado para RHEL/CentOS"
    exit 1
fi

# Función para verificar si MariaDB/MySQL está corriendo
check_mysql_running() {
    if systemctl is-active --quiet mariadb 2>/dev/null; then
        return 0
    elif systemctl is-active --quiet mysqld 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Verificar si ya existe MySQL o MariaDB instalado
MYSQL_INSTALLED=false
if systemctl list-units --type=service --all | grep -qE 'mysqld|mariadb'; then
    echo "✓ MariaDB/MySQL ya está instalado"
    MYSQL_INSTALLED=true
    
    # Intentar iniciar si está parado
    if ! check_mysql_running; then
        echo "  → MariaDB está parado, intentando iniciar..."
        systemctl start mariadb 2>/dev/null || systemctl start mysqld 2>/dev/null || true
        sleep 2
        
        if check_mysql_running; then
            echo "  ✓ MariaDB iniciado correctamente"
        else
            echo "  ⚠ No se pudo iniciar MariaDB automáticamente"
            echo "  → Saltando instalación, solo configuraremos la base de datos"
        fi
    else
        echo "  ✓ MariaDB ya está corriendo"
    fi
fi

    else
        echo "  ✓ MariaDB ya está corriendo"
    fi
fi

# Instalar solo si no está instalado
if [ "$MYSQL_INSTALLED" = false ]; then
    echo ""
    echo "[1/4] Instalando MariaDB desde repositorios..."
    echo ""
    echo "⚠ NOTA: Si tienes problemas con los repos de RHEL (sistema no registrado),"
    echo "        el script intentará usar repos alternativos."
    echo ""
    
    # Intentar instalación con manejo de errores
    if dnf install -y mariadb-server mariadb 2>/dev/null; then
        echo "✓ Instalado con dnf"
    elif yum install -y mariadb-server mariadb 2>/dev/null; then
        echo "✓ Instalado con yum"
    else
        echo ""
        echo "⚠ Error al instalar MariaDB desde repositorios oficiales"
        echo ""
        echo "SOLUCIÓN ALTERNATIVA:"
        echo "1. Instalar manualmente con: sudo dnf install -y mariadb-server mariadb"
        echo "2. O descargar RPMs manualmente desde: https://mariadb.org/download/"
        echo ""
        echo "Si MariaDB ya está instalado pero no funciona, intenta:"
        echo "  sudo systemctl start mariadb"
        echo "  sudo systemctl status mariadb"
        echo ""
        exit 1
    fi

    echo ""
    echo "[2/4] Iniciando servicio MariaDB..."
    echo ""

    systemctl start mariadb
    systemctl enable mariadb
    sleep 2
    systemctl status mariadb --no-pager
else
    echo ""
    echo "[1/4] MariaDB ya instalado, omitiendo instalación..."
    echo ""
fi

echo ""
echo "[3/4] Configurando MariaDB..."
echo ""

# Configurar root password
ROOT_PASS="NetApp123!"

echo "Intentando configurar password de root..."

# Intentar primero sin password (instalación nueva)
if mysql -u root -e "SELECT 1;" 2>/dev/null; then
    echo "  → Acceso sin password detectado (instalación nueva)"
    mysql -u root <<-EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '${ROOT_PASS}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOF
    echo "  ✓ Password de root configurado"
elif mysql -u root -p${ROOT_PASS} -e "SELECT 1;" 2>/dev/null; then
    echo "  ✓ Password ya configurado correctamente"
else
    echo "  ⚠ No se pudo acceder como root"
    echo ""
    echo "  Intenta manualmente:"
    echo "    sudo mysql -u root"
    echo "    ALTER USER 'root'@'localhost' IDENTIFIED BY 'NetApp123!';"
    echo "    FLUSH PRIVILEGES;"
    echo ""
    read -p "¿Continuar con la configuración de base de datos? (s/N): " CONTINUE
    if [ "$CONTINUE" != "s" ] && [ "$CONTINUE" != "S" ]; then
        exit 1
    fi
fi

echo ""
echo "[4/4] Creando base de datos y usuario..."
echo ""

# Intentar con el ROOT_PASS configurado
if mysql -u root -p${ROOT_PASS} -e "SELECT 1;" &>/dev/null; then
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
    echo "✓ Base de datos y usuario creados"
else
    echo "⚠ No se pudo conectar con el password configurado"
    echo ""
    echo "Intenta ejecutar manualmente:"
    echo "  mysql -u root -p"
    echo "  (password: NetApp123!)"
    echo ""
    echo "  CREATE DATABASE snapmirror_monitoring;"
    echo "  CREATE USER 'snapmirror_user'@'localhost' IDENTIFIED BY 'SnapMirror123!';"
    echo "  GRANT ALL PRIVILEGES ON snapmirror_monitoring.* TO 'snapmirror_user'@'localhost';"
    echo "  FLUSH PRIVILEGES;"
    exit 1
fi

echo ""
echo "[5/5] Cargando schema..."
echo ""

# Cargar schema si existe
if [ -f "config/mysql_schema.sql" ]; then
    if mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql 2>/dev/null; then
        echo "✓ Schema cargado correctamente"
        
        # Verificar tablas
        echo ""
        echo "Tablas creadas:"
        mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
        
        TABLA_COUNT=$(mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;" | wc -l)
        if [ $TABLA_COUNT -ge 5 ]; then
            echo ""
            echo "✓ Se crearon $(($TABLA_COUNT - 1)) tablas correctamente"
        fi
    else
        echo "⚠ Error cargando schema"
        echo ""
        echo "Intenta manualmente:"
        echo "  mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql"
    fi
else
    echo "⚠ No se encontró config/mysql_schema.sql"
    echo "  Verifica que estás en el directorio raíz del proyecto"
fi

echo ""
echo "========================================="
echo "✓ CONFIGURACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "Credenciales MySQL:"
echo "  Root:     root / NetApp123!"
echo "  App User: snapmirror_user / SnapMirror123!"
echo "  Database: snapmirror_monitoring"
echo ""
echo "Servicio MariaDB:"
if systemctl is-active --quiet mariadb; then
    echo "  ✓ Corriendo"
elif systemctl is-active --quiet mysqld; then
    echo "  ✓ Corriendo"
else
    echo "  ⚠ No está corriendo"
    echo "    sudo systemctl start mariadb"
fi
echo ""
echo "Verificar instalación:"
echo "  1. Test de conexión:"
echo "     python3 test_mysql_connection.py"
echo ""
echo "  2. Verificación completa:"
echo "     python3 check_setup.py"
echo ""
echo "  3. Mover CSV mock a production:"
echo "     cd config/ && mv ontap_instances_mock.csv ontap_instances.csv && cd .."
echo ""
echo "  4. Probar collector:"
echo "     python3 run_collector.py --mode mock --once"
echo ""
echo "Configurar Grafana datasource:"
echo "  URL: http://localhost:3000 (admin/admin)"
echo "  Host: 127.0.0.1:3306"
echo "  Database: snapmirror_monitoring"
echo "  User: snapmirror_user"
echo "  Password: SnapMirror123!"
echo "  TLS/SSL: NO (sin marcar)"
echo ""
