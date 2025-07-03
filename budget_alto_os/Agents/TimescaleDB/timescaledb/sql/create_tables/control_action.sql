-- Create the table
CREATE TABLE IF NOT EXISTS control_action (
    timestamp           TIMESTAMPTZ,
    site_id             VARCHAR(32),
    agent_id            VARCHAR(32),
    device_id           VARCHAR(64),
    model               VARCHAR(64),
    datapoint           VARCHAR(64),
    value               DOUBLE PRECISION,
    previous_value      DOUBLE PRECISION,
    status              VARCHAR(32),
    remark              TEXT,
    PRIMARY KEY (timestamp, site_id, agent_id, model, device_id, datapoint)
);

-- Convert the table into a hypertable
SELECT create_hypertable(
    'control_action',
    'timestamp',
    chunk_time_interval => INTERVAL '30 day',
    if_not_exists => TRUE
);

-- Add a retention policy to the hypertable
SELECT add_retention_policy(
    'control_action',
    INTERVAL '2 year',
    if_not_exists => TRUE
);
