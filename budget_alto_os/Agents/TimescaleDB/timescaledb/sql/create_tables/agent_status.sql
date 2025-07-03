CREATE TABLE IF NOT EXISTS agent_status (
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    site_id VARCHAR(32) NOT NULL,
    agent_id VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    context TEXT
);

SELECT create_hypertable(
	'agent_status',
	'timestamp',
	chunk_time_interval => INTERVAL '1 day',
	if_not_exists => TRUE
);

SELECT add_retention_policy(
	'agent_status',
	INTERVAL '1 week',
	if_not_exists => TRUE
);
