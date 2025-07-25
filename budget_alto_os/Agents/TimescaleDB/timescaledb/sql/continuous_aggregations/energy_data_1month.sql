-- Create a continuous aggregate for the energy_data_1month materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS energy_data_1month
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 month', timestamp, 'timezone_placeholder') AS timestamp,
    min(timestamp) AS start_datetime,
    max(timestamp) AS end_datetime,
    site_id,
    model,
    device_id,
    CASE
        WHEN datapoint = 'cumulative_energy' THEN 'monthly_energy'
        WHEN datapoint = 'cumulative_cooling_energy' THEN 'monthly_cooling_energy'
    END AS datapoint,
    -- Calculate hourly energy difference for each datapoint type
    CASE
        WHEN datapoint = 'cumulative_energy' THEN 
            (last(value, timestamp) - first(value, timestamp))
        WHEN datapoint = 'cumulative_cooling_energy' THEN 
            (last(value, timestamp) - first(value, timestamp))
    END AS value,
    first(value, timestamp) AS first_value,
    last(value, timestamp) AS last_value
FROM raw_data
WHERE datapoint IN ('cumulative_energy', 'cumulative_cooling_energy')
GROUP BY
    time_bucket('1 month', timestamp, 'timezone_placeholder'),
    model,
    site_id,
    device_id,
    datapoint
WITH NO DATA;

-- Add refresh policy that runs every 1 day
SELECT add_continuous_aggregate_policy('energy_data_1month',
    start_offset => INTERVAL 'retention_interval_placeholder',
    end_offset => INTERVAL '1 minutes',
    schedule_interval => INTERVAL '1 day',
    initial_start => 'initial_start_placeholder',
    timezone => 'timezone_placeholder',
    if_not_exists => true
);