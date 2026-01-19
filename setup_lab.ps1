# =====================================================
# SnapMirror Monitor - Auto Setup Script
# Para NetApp Lab on Demand (Windows)
# =====================================================

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "SnapMirror Monitor - Auto Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Variables de configuración
$MYSQL_ROOT_PASSWORD = "NetApp123!"
$MYSQL_APP_USER = "snapmirror_user"
$MYSQL_APP_PASSWORD = "SnapMirror123!"
$MYSQL_DATABASE = "snapmirror_monitoring"
$GRAFANA_ADMIN_PASSWORD = "admin"

# Función para verificar si un comando existe
function Test-Command {
    param($Command)
    try {
        if (Get-Command $Command -ErrorAction Stop) { return $true }
    } catch { return $false }
}

# =====================================================
# 1. INSTALAR CHOCOLATEY (Gestor de paquetes)
# =====================================================
Write-Host "[1/6] Instalando Chocolatey..." -ForegroundColor Yellow
if (-not (Test-Command choco)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Actualizar PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "  ✓ Chocolatey instalado" -ForegroundColor Green
} else {
    Write-Host "  ✓ Chocolatey ya instalado" -ForegroundColor Green
}

# =====================================================
# 2. INSTALAR PYTHON
# =====================================================
Write-Host "`n[2/6] Instalando Python 3.11..." -ForegroundColor Yellow
if (-not (Test-Command python)) {
    choco install python311 -y --force
    # Actualizar PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "  ✓ Python instalado" -ForegroundColor Green
} else {
    $pythonVersion = python --version
    Write-Host "  ✓ Python ya instalado: $pythonVersion" -ForegroundColor Green
}

# =====================================================
# 3. INSTALAR MYSQL
# =====================================================
Write-Host "`n[3/6] Instalando MySQL Server..." -ForegroundColor Yellow
if (-not (Test-Command mysql)) {
    choco install mysql -y --params "/port:3306"
    
    # Iniciar servicio MySQL
    Start-Sleep -Seconds 10
    Start-Service MySQL80
    
    Write-Host "  ✓ MySQL Server instalado" -ForegroundColor Green
    Write-Host "  ⚙ Configurando MySQL..." -ForegroundColor Yellow
    
    # Configurar password de root (MySQL 8.0+)
    $mysqlSecureInstall = @"
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
"@
    
    $mysqlSecureInstall | & "C:\tools\mysql\current\bin\mysql.exe" -u root --skip-password
    
    Write-Host "  ✓ MySQL configurado" -ForegroundColor Green
} else {
    Write-Host "  ✓ MySQL ya instalado" -ForegroundColor Green
}

# =====================================================
# 4. INSTALAR GRAFANA
# =====================================================
Write-Host "`n[4/6] Instalando Grafana..." -ForegroundColor Yellow
if (-not (Test-Command grafana-server)) {
    choco install grafana -y
    
    # Iniciar servicio Grafana
    Start-Sleep -Seconds 5
    Start-Service grafana
    
    Write-Host "  ✓ Grafana instalado" -ForegroundColor Green
    Write-Host "  ℹ URL: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
} else {
    Write-Host "  ✓ Grafana ya instalado" -ForegroundColor Green
    # Asegurar que está corriendo
    Start-Service grafana -ErrorAction SilentlyContinue
}

# =====================================================
# 5. CONFIGURAR PYTHON Y DEPENDENCIAS
# =====================================================
Write-Host "`n[5/6] Instalando dependencias Python..." -ForegroundColor Yellow

# Actualizar pip
python -m pip install --upgrade pip --quiet

# Instalar dependencias del proyecto
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt --quiet
    Write-Host "  ✓ Dependencias Python instaladas" -ForegroundColor Green
} else {
    Write-Host "  ⚠ requirements.txt no encontrado, instalando manualmente..." -ForegroundColor Yellow
    pip install netapp-ontap requests PyMySQL PyYAML aiohttp --quiet
    Write-Host "  ✓ Dependencias básicas instaladas" -ForegroundColor Green
}

# =====================================================
# 6. INICIALIZAR BASE DE DATOS
# =====================================================
Write-Host "`n[6/6] Inicializando base de datos MySQL..." -ForegroundColor Yellow

# Crear usuario y base de datos
$mysqlInit = @"
CREATE DATABASE IF NOT EXISTS $MYSQL_DATABASE;
CREATE USER IF NOT EXISTS '$MYSQL_APP_USER'@'localhost' IDENTIFIED BY '$MYSQL_APP_PASSWORD';
GRANT ALL PRIVILEGES ON ${MYSQL_DATABASE}.* TO '$MYSQL_APP_USER'@'localhost';
FLUSH PRIVILEGES;
"@

$mysqlInit | & "C:\tools\mysql\current\bin\mysql.exe" -u root -p"$MYSQL_ROOT_PASSWORD"

# Ejecutar schema SQL
if (Test-Path "config\mysql_schema.sql") {
    Get-Content "config\mysql_schema.sql" | & "C:\tools\mysql\current\bin\mysql.exe" -u root -p"$MYSQL_ROOT_PASSWORD" $MYSQL_DATABASE
    Write-Host "  ✓ Schema MySQL creado" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Schema SQL no encontrado en config/mysql_schema.sql" -ForegroundColor Yellow
}

# Actualizar config.yaml con las credenciales
if (Test-Path "config\config.yaml") {
    Write-Host "`n  ⚙ Actualizando config.yaml..." -ForegroundColor Yellow
    
    $configContent = Get-Content "config\config.yaml" -Raw
    $configContent = $configContent -replace 'password: change_me_in_production', "password: $MYSQL_APP_PASSWORD"
    $configContent = $configContent -replace 'user: snapmirror_user', "user: $MYSQL_APP_USER"
    $configContent | Set-Content "config\config.yaml"
    
    Write-Host "  ✓ Configuración actualizada" -ForegroundColor Green
}

# =====================================================
# RESUMEN FINAL
# =====================================================
Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "✓ INSTALACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Servicios instalados:" -ForegroundColor White
Write-Host "  • Python $(python --version 2>&1)" -ForegroundColor Gray
Write-Host "  • MySQL Server 8.0 (Puerto 3306)" -ForegroundColor Gray
Write-Host "  • Grafana (Puerto 3000)" -ForegroundColor Gray
Write-Host ""
Write-Host "Credenciales MySQL:" -ForegroundColor White
Write-Host "  • Root password: $MYSQL_ROOT_PASSWORD" -ForegroundColor Gray
Write-Host "  • App user: $MYSQL_APP_USER" -ForegroundColor Gray
Write-Host "  • App password: $MYSQL_APP_PASSWORD" -ForegroundColor Gray
Write-Host "  • Database: $MYSQL_DATABASE" -ForegroundColor Gray
Write-Host ""
Write-Host "URLs:" -ForegroundColor White
Write-Host "  • Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Generar datos de prueba:" -ForegroundColor White
Write-Host "     python generate_mock_csv.py --num-instances 50" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Ejecutar collector en modo mock:" -ForegroundColor White
Write-Host "     python run_collector.py --mode mock --once" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Abrir Grafana e importar dashboard:" -ForegroundColor White
Write-Host "     grafana/snapmirror_dashboard.json" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Para ONTAP real, editar:" -ForegroundColor White
Write-Host "     config/ontap_instances.csv" -ForegroundColor Gray
Write-Host "     python run_collector.py --mode real --once" -ForegroundColor Gray
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan

# Verificar servicios
Write-Host "`nVerificando servicios..." -ForegroundColor Yellow
$mysqlStatus = (Get-Service MySQL80).Status
$grafanaStatus = (Get-Service grafana).Status

Write-Host "  MySQL: $mysqlStatus" -ForegroundColor $(if($mysqlStatus -eq 'Running'){'Green'}else{'Red'})
Write-Host "  Grafana: $grafanaStatus" -ForegroundColor $(if($grafanaStatus -eq 'Running'){'Green'}else{'Red'})

if ($mysqlStatus -ne 'Running') {
    Write-Host "`n⚠ MySQL no está corriendo. Iniciando..." -ForegroundColor Yellow
    Start-Service MySQL80
}

if ($grafanaStatus -ne 'Running') {
    Write-Host "⚠ Grafana no está corriendo. Iniciando..." -ForegroundColor Yellow
    Start-Service grafana
}

Write-Host "`n¡Listo para usar! 🚀" -ForegroundColor Green
