#!/bin/bash
# Script para limpiar instalación parcial o incorrecta de MySQL
# Uso: sudo ./cleanup_mysql.sh

echo "========================================="
echo "  Limpieza de MySQL"
echo "========================================="
echo ""

echo "⚠️  ADVERTENCIA: Este script eliminará:"
echo "  - Todos los paquetes MySQL/MariaDB instalados"
echo "  - Archivos de configuración"
echo "  - Datos de bases de datos"
echo ""
read -p "¿Continuar? (s/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo "Cancelado"
    exit 0
fi

echo ""
echo "→ Deteniendo servicios MySQL/MariaDB..."
systemctl stop mysqld 2>/dev/null || true
systemctl stop mariadb 2>/dev/null || true

echo "→ Deshabilitando servicios..."
systemctl disable mysqld 2>/dev/null || true
systemctl disable mariadb 2>/dev/null || true

echo "→ Eliminando paquetes MySQL Community..."
rpm -qa | grep mysql-community | xargs rpm -e --nodeps 2>/dev/null || true

echo "→ Eliminando paquetes MariaDB..."
rpm -qa | grep mariadb | xargs rpm -e --nodeps 2>/dev/null || true

echo "→ Eliminando repositorios MySQL..."
rm -f /etc/yum.repos.d/mysql*.repo
rm -f /etc/yum.repos.d/mariadb*.repo

echo "→ Eliminando archivos de configuración..."
rm -rf /etc/my.cnf
rm -rf /etc/my.cnf.d/
rm -rf /var/lib/mysql/
rm -rf /var/log/mysqld.log
rm -rf /var/run/mysqld/

echo "→ Limpiando cache de yum..."
yum clean all 2>/dev/null || true

echo ""
echo "✓ Limpieza completada"
echo ""
echo "Próximos pasos:"
echo "  1. chmod +x install_mysql_community.sh"
echo "  2. sudo ./install_mysql_community.sh"
echo ""
