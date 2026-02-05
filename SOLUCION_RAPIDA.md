# Solución rápida para tu problema actual

Según tu salida, el problema es que MySQL no se instaló correctamente. Aquí está la solución:

## Paso 1: Instalar MariaDB manualmente

Ejecuta este comando desde el directorio del proyecto:

```bash
chmod +x install_mysql_manual.sh
sudo ./install_mysql_manual.sh
```

Este script hará TODO automáticamente:
- ✅ Instalar MariaDB
- ✅ Iniciar el servicio
- ✅ Configurar password de root (NetApp123!)
- ✅ Crear la base de datos `snapmirror_monitoring`
- ✅ Crear el usuario `snapmirror_user` con password `SnapMirror123!`
- ✅ Cargar el schema (tablas)

## Paso 2: Verificar que todo funciona

```bash
# Verificar configuración completa
python3 check_setup.py

# Probar conexión MySQL específicamente
python3 test_mysql_connection.py
```

## Paso 3: Mover el CSV generado

```bash
cd config/
mv ontap_instances_mock.csv ontap_instances.csv
cd ..
```

## Paso 4: Probar el collector con datos mock

```bash
python3 run_collector.py --mode mock --once
```

Deberías ver algo como:
```
Starting cascade collection: 100 instances
[1/100] Collecting ontap-select-sevilla-0001...
✓ ontap-select-sevilla-0001: 3 relationships processed
...
```

## Paso 5: Configurar Grafana

1. Abrir http://192.168.0.63:3000 (o http://localhost:3000)
2. Login: admin / admin
3. Ir a: Configuration > Data sources > Add data source > MySQL
4. Configurar:
   ```
   Host: 127.0.0.1:3306
   Database: snapmirror_monitoring
   User: snapmirror_user
   Password: SnapMirror123!
   
   ⚠️ NO marcar TLS/SSL
   ```
5. Click en "Save & test" → debe mostrar "Database Connection OK"
6. Ir a: Dashboards > Import > Upload JSON file
7. Seleccionar: grafana/snapmirror_dashboard.json
8. Elegir datasource: SnapMirror DB
9. Click Import

---

## Si algo falla

### Error: MariaDB ya está instalado pero parado
```bash
sudo systemctl start mariadb
sudo systemctl status mariadb
```

### Error: No puedo conectar a MySQL
```bash
# Probar con diagnóstico
python3 test_mysql_connection.py
```

### Error: Las tablas no existen
```bash
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring < config/mysql_schema.sql
mysql -u snapmirror_user -pSnapMirror123! snapmirror_monitoring -e "SHOW TABLES;"
```

### Error en Grafana: "failed to connect to server"
- Prueba cambiar `localhost:3306` por `127.0.0.1:3306` en el datasource
- Asegúrate de NO marcar "TLS/SSL"
- Ejecuta: `python3 test_mysql_connection.py` para ver la configuración exacta

---

¿Necesitas ayuda adicional? Revisa el README.md sección Troubleshooting.
