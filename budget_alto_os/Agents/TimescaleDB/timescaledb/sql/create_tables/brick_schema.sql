-- Entities (building, floor, zone, sensor, meter)
CREATE TABLE IF NOT EXISTS brick_entities (
    entity_id VARCHAR(50) PRIMARY KEY,
    entity_type VARCHAR(20),
    brick_class VARCHAR(100),
    name VARCHAR(100),
    parent_id VARCHAR(50),
    properties JSONB
);

-- Relationships (hasLocation, isPartOf, feeds, etc.)
CREATE TABLE IF NOT EXISTS brick_relationships (
    subject_id VARCHAR(50),
    predicate VARCHAR(50),
    object_id VARCHAR(50),
    PRIMARY KEY (subject_id, predicate, object_id)
);

-- Measurement points (CO2, temp, humidity, power, etc.)
CREATE TABLE IF NOT EXISTS brick_points (
    point_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(50),
    point_type VARCHAR(30),
    brick_class VARCHAR(100),
    unit VARCHAR(20),
    min_value FLOAT,
    max_value FLOAT
);

-- Time-series data (all sensor/meter readings)
CREATE TABLE IF NOT EXISTS sensor_data (
    timestamp TIMESTAMPTZ NOT NULL,
    point_id VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    quality VARCHAR(10) DEFAULT 'good',
    PRIMARY KEY (timestamp, point_id)
);

-- Make sensor_data a hypertable for TimescaleDB
SELECT create_hypertable(
    'sensor_data',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Add retention policy (customize interval as needed)
SELECT add_retention_policy(
    'sensor_data',
    INTERVAL '90 days',
    if_not_exists => TRUE
);