CREATE TABLE IF NOT EXISTS weather_forecast (
    timestamp      TIMESTAMPTZ     NOT NULL,
    site_id        VARCHAR(32)     NOT NULL,
    device_id      VARCHAR(64)     NOT NULL,
    forecast_data  JSONB           NOT NULL,
    PRIMARY KEY (timestamp, site_id, device_id)
);

SELECT create_hypertable(
    'weather_forecast',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'weather_forecast',
    INTERVAL '1 year',
    if_not_exists => TRUE
);