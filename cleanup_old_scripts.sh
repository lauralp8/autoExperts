#!/bin/bash
# Script para limpiar archivos obsoletos de instalación
# Estos scripts ya no son necesarios ahora que tenemos install_mysql_community.sh

echo "========================================="
echo "  Limpieza de scripts obsoletos"
echo "========================================="
echo ""

SCRIPTS_TO_REMOVE=(
    "install_mariadb_repo.sh"
    "install_mariadb_wget.sh"
    "install_mysql_manual.sh"
    "quick_mysql_setup.sh"
)

echo "Los siguientes scripts serán eliminados:"
for script in "${SCRIPTS_TO_REMOVE[@]}"; do
    if [ -f "$script" ]; then
        echo "  - $script"
    fi
done

echo ""
read -p "¿Continuar? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[SsYy]$ ]]; then
    for script in "${SCRIPTS_TO_REMOVE[@]}"; do
        if [ -f "$script" ]; then
            rm -f "$script"
            echo "✓ Eliminado: $script"
        fi
    done
    
    echo ""
    echo "✓ Limpieza completada"
    echo ""
    echo "Script activo:"
    echo "  install_mysql_community.sh - Instalación MySQL Community 8.0"
else
    echo "Cancelado"
fi
