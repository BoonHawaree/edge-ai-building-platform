CREATE TABLE IF NOT EXISTS chiller_mpc (
    timestamp      TIMESTAMPTZ     NOT NULL,
    site_id        VARCHAR(128)     NOT NULL,
    device_id      VARCHAR(128)     NOT NULL,
    mode           VARCHAR(128)     NOT NULL,
    solution       JSONB            NOT NULL,
    PRIMARY KEY (timestamp, device_id)
);

SELECT create_hypertable(
    'chiller_mpc',
    'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'chiller_mpc',
    INTERVAL '3 months',
    if_not_exists => TRUE
);
