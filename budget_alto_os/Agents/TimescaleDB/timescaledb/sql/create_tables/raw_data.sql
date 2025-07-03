CREATE TABLE IF NOT EXISTS raw_data (
	timestamp   TIMESTAMPTZ,
	site_id   	VARCHAR(32),
	device_id   VARCHAR(64),
	model       VARCHAR(64),
	datapoint   VARCHAR(64),
	value       REAL,
	PRIMARY KEY (timestamp, site_id, device_id, model, datapoint)
);

SELECT create_hypertable(
	'raw_data',
	'timestamp',
	chunk_time_interval => INTERVAL '1 day',
	if_not_exists => TRUE
);

SELECT add_retention_policy(
	'raw_data',
	INTERVAL 'retention_interval_placeholder',
	if_not_exists => TRUE
);
