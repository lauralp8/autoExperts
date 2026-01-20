#!/bin/bash
# =====================================================
# SnapMirror Monitor - Docker Deployment Script
# Levanta MySQL + Grafana con Docker Compose
# =====================================================

set -e

echo "========================================="
echo "SnapMirror Monitor - Docker Setup"
echo "========================================="
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado"
    echo ""
    echo "Instalar Docker:"
    echo "  Ubuntu/Debian: curl -fsSL https://get.docker.com | sh"
    echo "  RHEL: sudo yum install -y docker"
    exit 1
fi

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "❌ Docker Compose no está instalado"
    exit 1
fi

# Usar docker-compose o docker compose según disponibilidad
DOCKER_COMPOSE="docker-compose"
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
fi

echo "✓ Docker y Docker Compose detectados"
echo ""

# Crear directorio de Grafana provisioning si no existe
mkdir -p grafana/dashboards

# Detener contenedores anteriores si existen
echo "Deteniendo contenedores anteriores (si existen)..."
$DOCKER_COMPOSE down 2>/dev/null || true
echo ""

# Levantar servicios
echo "Levantando servicios..."
echo "  • MySQL (puerto 3306)"
echo "  • Grafana (puerto 3000)"
echo ""
$DOCKER_COMPOSE up -d

# Esperar a que los servicios estén listos
echo ""
echo "Esperando a que los servicios inicien..."
sleep 10

# Verificar estado
if docker ps | grep -q "snapmirror_mysql"; then
    echo "✓ MySQL corriendo"
else
    echo "❌ MySQL no se inició correctamente"
    $DOCKER_COMPOSE logs mysql
    exit 1
fi

if docker ps | grep -q "snapmirror_grafana"; then
    echo "✓ Grafana corriendo"
else
    echo "❌ Grafana no se inició correctamente"
    $DOCKER_COMPOSE logs grafana
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
echo "  • Ver logs:     $DOCKER_COMPOSE logs -f"
echo "  • Detener:      $DOCKER_COMPOSE down"
echo "  • Reiniciar:    $DOCKER_COMPOSE restart"
echo "  • Eliminar todo: $DOCKER_COMPOSE down -v"
echo ""
echo "========================================="
