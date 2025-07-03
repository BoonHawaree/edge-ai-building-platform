CREATE TABLE IF NOT EXISTS chiller_prediction (
    timestamp      TIMESTAMPTZ     NOT NULL,
    site_id        VARCHAR(32)     NOT NULL,
    device_id      VARCHAR(64)     NOT NULL,
    prediction_timestamp JSONB     NOT NULL,
    prediction_load      JSONB     NOT NULL,
    prediction_cds       JSONB     NOT NULL,
    prediction_wetbulb    JSONB     NOT NULL,
    PRIMARY KEY (timestamp, site_id, device_id)
);

SELECT create_hypertable(
    'chiller_prediction',
    'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'chiller_prediction',
    INTERVAL '2 year',
    if_not_exists => TRUE
);
