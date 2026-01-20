# =====================================================
# SnapMirror Monitor - Docker Deployment Script
# Levanta MySQL + Grafana con Docker Compose (Windows)
# =====================================================

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "SnapMirror Monitor - Docker Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Verificar Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker no está instalado" -ForegroundColor Red
    Write-Host ""
    Write-Host "Descargar Docker Desktop desde:" -ForegroundColor Yellow
    Write-Host "https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
    exit 1
}

# Verificar Docker Compose
$dockerComposeCmd = "docker-compose"
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    $dockerComposeCmd = "docker compose"
}

Write-Host "✓ Docker detectado" -ForegroundColor Green
Write-Host ""

# Crear directorio de Grafana provisioning si no existe
New-Item -ItemType Directory -Force -Path "grafana\dashboards" | Out-Null

# Detener contenedores anteriores si existen
Write-Host "Deteniendo contenedores anteriores (si existen)..." -ForegroundColor Yellow
& $dockerComposeCmd down 2>$null
Write-Host ""

# Levantar servicios
Write-Host "Levantando servicios..." -ForegroundColor Yellow
Write-Host "  • MySQL (puerto 3306)" -ForegroundColor Gray
Write-Host "  • Grafana (puerto 3000)" -ForegroundColor Gray
Write-Host ""

& $dockerComposeCmd up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al levantar servicios" -ForegroundColor Red
    exit 1
}

# Esperar a que los servicios estén listos
Write-Host ""
Write-Host "Esperando a que los servicios inicien..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Verificar estado
$mysqlRunning = docker ps --filter "name=snapmirror_mysql" --format "{{.Names}}"
$grafanaRunning = docker ps --filter "name=snapmirror_grafana" --format "{{.Names}}"

if ($mysqlRunning) {
    Write-Host "✓ MySQL corriendo" -ForegroundColor Green
} else {
    Write-Host "❌ MySQL no se inició correctamente" -ForegroundColor Red
    docker logs snapmirror_mysql
    exit 1
}

if ($grafanaRunning) {
    Write-Host "✓ Grafana corriendo" -ForegroundColor Green
} else {
    Write-Host "❌ Grafana no se inició correctamente" -ForegroundColor Red
    docker logs snapmirror_grafana
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✓ SERVICIOS DESPLEGADOS CORRECTAMENTE" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Servicios disponibles:" -ForegroundColor White
Write-Host "  • MySQL:   localhost:3306" -ForegroundColor Gray
Write-Host "  • Grafana: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Credenciales:" -ForegroundColor White
Write-Host "  MySQL:" -ForegroundColor Yellow
Write-Host "    - User: snapmirror_user" -ForegroundColor Gray
Write-Host "    - Pass: SnapMirror123!" -ForegroundColor Gray
Write-Host "    - DB:   snapmirror_monitoring" -ForegroundColor Gray
Write-Host ""
Write-Host "  Grafana:" -ForegroundColor Yellow
Write-Host "    - User: admin" -ForegroundColor Gray
Write-Host "    - Pass: admin" -ForegroundColor Gray
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Instalar dependencias Python:" -ForegroundColor White
Write-Host "     pip install -r requirements.txt" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Generar datos de prueba:" -ForegroundColor White
Write-Host "     python generate_mock_csv.py --num-instances 50" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Ejecutar collector:" -ForegroundColor White
Write-Host "     python run_collector.py --mode mock --once" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Abrir Grafana e importar dashboard:" -ForegroundColor White
Write-Host "     http://localhost:3000" -ForegroundColor Cyan
Write-Host "     Dashboard: grafana/snapmirror_dashboard.json" -ForegroundColor Gray
Write-Host ""
Write-Host "Comandos útiles:" -ForegroundColor Yellow
Write-Host "  • Ver logs:      docker-compose logs -f" -ForegroundColor Gray
Write-Host "  • Detener:       docker-compose down" -ForegroundColor Gray
Write-Host "  • Reiniciar:     docker-compose restart" -ForegroundColor Gray
Write-Host "  • Eliminar todo: docker-compose down -v" -ForegroundColor Gray
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
