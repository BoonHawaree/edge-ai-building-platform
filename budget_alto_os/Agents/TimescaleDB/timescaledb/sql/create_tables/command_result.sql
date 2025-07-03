-- Create the table
CREATE TABLE IF NOT EXISTS command_result (
    timestamp           TIMESTAMPTZ,
    site_id             VARCHAR(32),
    device_id           VARCHAR(64),
    datapoint           VARCHAR(64),
    value               DOUBLE PRECISION,
    command_type        VARCHAR(32),
    priority            VARCHAR(32),
    source              VARCHAR(32),
    status              VARCHAR(32),
    PRIMARY KEY (timestamp, site_id, device_id, datapoint)
);

-- Convert the table into a hypertable
SELECT create_hypertable(
    'command_result',
    'timestamp',
    chunk_time_interval => INTERVAL '30 day',
    if_not_exists => TRUE
);

-- Add a retention policy to the hypertable
SELECT add_retention_policy(
    'command_result',
    INTERVAL '2 year',
    if_not_exists => TRUE
);