-- Create a continuous aggregate for the hourly_data materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_data
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp, 'timezone_placeholder') AS timestamp,
    min(timestamp) AS start_datetime,
    max(timestamp) AS end_datetime,
    model,
    site_id,
    device_id,
    datapoint,
    avg(value) AS value
FROM raw_data
WHERE
    device_id IN ('plant', 'air_distribution_system')
    AND datapoint IN ('power', 'cooling_rate')
GROUP BY
    time_bucket('1 hour', timestamp, 'timezone_placeholder'),
    model,
    site_id,
    device_id,
    datapoint
WITH NO DATA;

-- Add refresh policy that runs every hour
SELECT add_continuous_aggregate_policy('hourly_data',
    start_offset => INTERVAL '1 year',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => true,
    timezone => 'timezone_placeholder'
);
