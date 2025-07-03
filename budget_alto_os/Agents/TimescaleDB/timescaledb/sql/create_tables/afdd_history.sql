CREATE TABLE IF NOT EXISTS afdd_history (
	fault_id    VARCHAR(32),
    timestamp   TIMESTAMPTZ,
	site_id     VARCHAR(32),
	fault_name  TEXT,
    "group"     VARCHAR(64),
	priority    VARCHAR(64),
	status      VARCHAR(64),
	PRIMARY KEY (timestamp, site_id)
);

SELECT create_hypertable(
	'afdd_history',
	'timestamp',
	chunk_time_interval => INTERVAL '30 day',
	if_not_exists => TRUE
);

SELECT add_retention_policy(
	'afdd_history',
	INTERVAL '3 year',
	if_not_exists => TRUE
);
