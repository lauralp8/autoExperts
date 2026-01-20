#!/bin/bash
# =====================================================
# SnapMirror Monitor - Docker Deployment Script
# Levanta MySQL + Grafana con Docker Compose
# =====================================================

set -e

echo "========================================="
echo "SnapMirror Monitor - Container Setup"
echo "========================================="
echo ""

# Detectar si hay Docker o Podman
USE_PODMAN=false
CONTAINER_CMD=""
COMPOSE_CMD=""

if command -v podman &> /dev/null; then
    echo "✓ Podman detectado (compatible con Docker)"
    USE_PODMAN=true
    CONTAINER_CMD="podman"
    
    # Para podman-compose, usar podman directamente con archivos compose
    if command -v podman-compose &> /dev/null; then
        COMPOSE_CMD="podman-compose"
    else
        echo "⚠️ podman-compose no instalado, usando podman directamente"
        COMPOSE_CMD="podman-compose-fallback"
    fi
    
elif command -v docker &> /dev/null; then
    echo "✓ Docker detectado"
    CONTAINER_CMD="docker"
    
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        echo "❌ Docker Compose no está instalado"
        exit 1
    fi
else
    echo "❌ Ni Docker ni Podman están instalados"
    echo ""
    echo "Para RHEL/CentOS, Podman suele venir preinstalado."
    echo "Verifica con: podman --version"
    echo ""
    echo "Si no está, usa el setup nativo:"
    echo "  ./setup_lab.sh"
    exit 1
fi

echo "✓ Sistema de contenedores listo"
echo ""

# Crear directorio de Grafana provisioning si no existe
mkdir -p grafana/dashboards

# Detener contenedores anteriores si existen
echo "Deteniendo contenedores anteriores (si existen)..."
if [ "$USE_PODMAN" = true ]; then
    podman pod stop snapmirror-pod 2>/dev/null || true
    podman pod rm snapmirror-pod 2>/dev/null || true
    podman rm -f snapmirror_mysql snapmirror_grafana 2>/dev/null || true
else
    $COMPOSE_CMD down 2>/dev/null || true
fi
echo ""

# Levantar servicios
echo "Levantando servicios..."
echo "  • MySQL (puerto 3306)"
echo "  • Grafana (puerto 3000)"
echo ""

if [ "$USE_PODMAN" = true ]; then
    # Crear pod para red compartida
    podman pod create --name snapmirror-pod -p 3306:3306 -p 3000:3000
    
    # Levantar MySQL
    podman run -d \
        --name snapmirror_mysql \
        --pod snapmirror-pod \
        -e MYSQL_ROOT_PASSWORD=NetApp123! \
        -e MYSQL_DATABASE=snapmirror_monitoring \
        -e MYSQL_USER=snapmirror_user \
        -e MYSQL_PASSWORD=SnapMirror123! \
        -v ./config/mysql_schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro,z \
        docker.io/library/mysql:8.0
    
    # Esperar a que MySQL esté listo
    echo "Esperando a que MySQL inicie..."
    sleep 15
    
    # Levantar Grafana
    podman run -d \
        --name snapmirror_grafana \
        --pod snapmirror-pod \
        -e GF_SECURITY_ADMIN_USER=admin \
        -e GF_SECURITY_ADMIN_PASSWORD=admin \
        docker.io/grafana/grafana:latest
else
    $COMPOSE_CMD up -d
fi

# Esperar a que los servicios estén listos
echo ""
echo "Esperando a que los servicios inicien..."
sleep 10

# Verificar estado
if $CONTAINER_CMD ps | grep -q "snapmirror_mysql"; then
    echo "✓ MySQL corriendo"
else
    echo "❌ MySQL no se inició correctamente"
    $CONTAINER_CMD logs snapmirror_mysql
    exit 1
fi

if $CONTAINER_CMD ps | grep -q "snapmirror_grafana"; then
    echo "✓ Grafana corriendo"
else
    echo "❌ Grafana no se inició correctamente"
    $CONTAINER_CMD logs snapmirror_grafana
    exit 1
fi

# Obtener IP del host
HOST_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
echo "✓ SERVICIOS DESPLEGADOS CORRECTAMENTE"
echo "========================================="
echo ""
echo "Servicios disponibles:"
echo "  • MySQL:   localhost:3306"
echo "  • Grafana: http://localhost:3000"
echo "             http://$HOST_IP:3000"
echo ""
echo "Credenciales:"
echo "  MySQL:"
echo "    - User: snapmirror_user"
echo "    - Pass: SnapMirror123!"
echo "    - DB:   snapmirror_monitoring"
echo ""
echo "  Grafana:"
echo "    - User: admin"
echo "    - Pass: admin"
echo ""
echo "Próximos pasos:"
echo "  1. Instalar dependencias Python:"
echo "     pip3 install -r requirements.txt"
echo ""
echo "  2. Generar datos de prueba:"
echo "     python3 generate_mock_csv.py --num-instances 50"
echo ""
echo "  3. Ejecutar collector:"
echo "     python3 run_collector.py --mode mock --once"
echo ""
echo "  4. Abrir Grafana e importar dashboard:"
echo "     http://localhost:3000"
echo "     Dashboard: grafana/snapmirror_dashboard.json"
echo ""
echo "Comandos útiles:"
if [ "$USE_PODMAN" = true ]; then
    echo "  • Ver logs:      podman logs -f snapmirror_mysql"
    echo "  • Detener:       podman pod stop snapmirror-pod"
    echo "  • Reiniciar:     podman pod restart snapmirror-pod"
    echo "  • Eliminar:      podman pod rm -f snapmirror-pod"
else
    echo "  • Ver logs:      $COMPOSE_CMD logs -f"
    echo "  • Detener:       $COMPOSE_CMD down"
    echo "  • Reiniciar:     $COMPOSE_CMD restart"
    echo "  • Eliminar todo: $COMPOSE_CMD down -v"
fi
echo ""
echo "========================================="
