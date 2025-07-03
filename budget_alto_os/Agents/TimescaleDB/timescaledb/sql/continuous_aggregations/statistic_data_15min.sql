-- Create a continuous aggregate for the statistic_data_15min materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS statistic_data_15min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', timestamp, 'timezone_placeholder') AS timestamp,
    min(timestamp) AS start_datetime,
    max(timestamp) AS end_datetime,
    site_id,
    model,
    device_id,
    datapoint,
    avg(value) AS mean_value,
    min(value) AS min_value,
    max(value) AS max_value,
    first(value, timestamp) AS first_value,
    last(value, timestamp) AS last_value
FROM raw_data
WHERE datapoint NOT IN ('cumulative_energy', 'cumulative_cooling_energy')
GROUP BY
    time_bucket('15 minutes', timestamp, 'timezone_placeholder'),
    model,
    site_id,
    device_id,
    datapoint
WITH NO DATA;

-- Add refresh policy that runs every 5 minutes
SELECT add_continuous_aggregate_policy('statistic_data_15min',
    start_offset => INTERVAL 'retention_interval_placeholder',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    initial_start => 'initial_start_placeholder',
    timezone => 'timezone_placeholder',
    if_not_exists => true
);
