-- Schema para SnapMirror Monitoring
-- NetApp ONTAP Select - Grafana Dashboard

CREATE DATABASE IF NOT EXISTS snapmirror_monitoring;
USE snapmirror_monitoring;

-- Tabla de instancias ONTAP Select
CREATE TABLE IF NOT EXISTS ontap_instances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    ip_address VARCHAR(50) NOT NULL,
    cluster_uuid VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_location (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de relaciones SnapMirror
CREATE TABLE IF NOT EXISTS snapmirror_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    relationship_uuid VARCHAR(100) NOT NULL,
    source_path VARCHAR(500),
    destination_path VARCHAR(500),
    policy VARCHAR(100),
    relationship_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES ontap_instances(id) ON DELETE CASCADE,
    UNIQUE KEY unique_relationship (instance_id, relationship_uuid),
    INDEX idx_uuid (relationship_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de estado actual de SnapMirror (última recolección)
CREATE TABLE IF NOT EXISTS snapmirror_status_current (
    id INT AUTO_INCREMENT PRIMARY KEY,
    relationship_id INT NOT NULL,
    instance_id INT NOT NULL,
    lag_seconds INT DEFAULT 0,
    lag_minutes DECIMAL(10, 2) AS (lag_seconds / 60) STORED,
    state VARCHAR(50),
    health_status VARCHAR(50),
    transfer_state VARCHAR(50),
    last_transfer_end_timestamp BIGINT,
    alert_level VARCHAR(20) DEFAULT 'ok',  -- ok, warning, critical, error
    error_message TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (relationship_id) REFERENCES snapmirror_relationships(id) ON DELETE CASCADE,
    FOREIGN KEY (instance_id) REFERENCES ontap_instances(id) ON DELETE CASCADE,
    UNIQUE KEY unique_current_status (relationship_id),
    INDEX idx_alert_level (alert_level),
    INDEX idx_instance (instance_id),
    INDEX idx_collected (collected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla histórica (sin particiones para compatibilidad con MySQL 8.0 + foreign keys)
CREATE TABLE IF NOT EXISTS snapmirror_status_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    relationship_id INT NOT NULL,
    instance_id INT NOT NULL,
    lag_seconds INT,
    state VARCHAR(50),
    health_status VARCHAR(50),
    alert_level VARCHAR(20),
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (relationship_id) REFERENCES snapmirror_relationships(id) ON DELETE CASCADE,
    INDEX idx_relationship_time (relationship_id, collected_at),
    INDEX idx_instance_time (instance_id, collected_at),
    INDEX idx_collected (collected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Vista para Grafana: Mapa con alertas
CREATE OR REPLACE VIEW v_snapmirror_map AS
SELECT 
    oi.id as instance_id,
    oi.name as instance_name,
    oi.ip_address,
    oi.latitude,
    oi.longitude,
    oi.location_name,
    COUNT(DISTINCT sr.id) as total_relationships,
    COUNT(DISTINCT CASE WHEN ssc.alert_level = 'critical' THEN sr.id END) as critical_count,
    COUNT(DISTINCT CASE WHEN ssc.alert_level = 'warning' THEN sr.id END) as warning_count,
    COUNT(DISTINCT CASE WHEN ssc.alert_level = 'error' THEN sr.id END) as error_count,
    COUNT(DISTINCT CASE WHEN ssc.alert_level = 'ok' THEN sr.id END) as ok_count,
    MAX(ssc.lag_seconds) as max_lag_seconds,
    AVG(ssc.lag_seconds) as avg_lag_seconds,
    MAX(ssc.collected_at) as last_check,
    CASE 
        WHEN COUNT(CASE WHEN ssc.alert_level = 'critical' THEN 1 END) > 0 THEN 'critical'
        WHEN COUNT(CASE WHEN ssc.alert_level = 'error' THEN 1 END) > 0 THEN 'error'
        WHEN COUNT(CASE WHEN ssc.alert_level = 'warning' THEN 1 END) > 0 THEN 'warning'
        ELSE 'ok'
    END as overall_status
FROM ontap_instances oi
LEFT JOIN snapmirror_relationships sr ON oi.id = sr.instance_id
LEFT JOIN snapmirror_status_current ssc ON sr.id = ssc.relationship_id
WHERE oi.is_active = TRUE
GROUP BY oi.id, oi.name, oi.ip_address, oi.latitude, oi.longitude, oi.location_name;

-- Vista de detalle para drill-down
CREATE OR REPLACE VIEW v_snapmirror_detail AS
SELECT 
    oi.name as instance_name,
    oi.ip_address,
    oi.location_name,
    sr.source_path,
    sr.destination_path,
    sr.policy,
    ssc.state,
    ssc.health_status,
    ssc.lag_seconds,
    ssc.lag_minutes,
    ssc.alert_level,
    ssc.error_message,
    ssc.collected_at,
    CASE 
        WHEN ssc.lag_seconds IS NULL THEN 'No Data'
        WHEN ssc.lag_seconds < 900 THEN 'Healthy'
        WHEN ssc.lag_seconds < 3600 THEN 'Warning'
        ELSE 'Critical'
    END as status_text
FROM snapmirror_relationships sr
INNER JOIN ontap_instances oi ON sr.instance_id = oi.id
LEFT JOIN snapmirror_status_current ssc ON sr.id = ssc.relationship_id
WHERE oi.is_active = TRUE;

-- Índices adicionales para performance
CREATE INDEX idx_status_lag ON snapmirror_status_current(lag_seconds);
CREATE INDEX idx_history_lag ON snapmirror_status_history(lag_seconds);
