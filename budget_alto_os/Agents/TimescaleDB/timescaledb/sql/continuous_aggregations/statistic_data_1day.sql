-- Create a continuous aggregate for the statistic_data_1day materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS statistic_data_1day
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp, 'timezone_placeholder') AS timestamp,
    min(timestamp) AS start_datetime,
    max(timestamp) AS end_datetime,
    site_id,
    model,
    device_id,
    datapoint,
    avg(value) AS mean_value,
    max(value) AS max_value,
    min(value) AS min_value,
    first(value, timestamp) AS first_value,
    last(value, timestamp) AS last_value
FROM raw_data
WHERE datapoint NOT IN ('cumulative_energy', 'cumulative_cooling_energy')
GROUP BY
    time_bucket('1 day', timestamp, 'timezone_placeholder'),
    model,
    site_id,
    device_id,
    datapoint
WITH NO DATA;

-- Add refresh policy that runs every 1 hours
SELECT add_continuous_aggregate_policy('statistic_data_1day',
    start_offset => INTERVAL 'retention_interval_placeholder',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 hours',
    initial_start => 'initial_start_placeholder',
    timezone => 'timezone_placeholder',
    if_not_exists => true
);
