CREATE MATERIALIZED VIEW IF NOT EXISTS daily_weather_data
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp, 'timezone_placeholder') AS timestamp,
    min(timestamp) AS start_datetime,
    max(timestamp) AS end_datetime,
    site_id,
    device_id,
    -- Max values
    max(CASE WHEN datapoint = 'drybulb_temperature' THEN value END) AS max_drybulb_temperature,
    max(CASE WHEN datapoint = 'wetbulb_temperature' THEN value END) AS max_wetbulb_temperature,
    max(CASE WHEN datapoint = 'humidity' THEN value END) AS max_humidity,
    -- Min values
    min(CASE WHEN datapoint = 'drybulb_temperature' THEN value END) AS min_drybulb_temperature,
    min(CASE WHEN datapoint = 'wetbulb_temperature' THEN value END) AS min_wetbulb_temperature,
    min(CASE WHEN datapoint = 'humidity' THEN value END) AS min_humidity,
    -- Mean values
    avg(CASE WHEN datapoint = 'drybulb_temperature' THEN value END) AS mean_drybulb_temperature,
    avg(CASE WHEN datapoint = 'wetbulb_temperature' THEN value END) AS mean_wetbulb_temperature,
    avg(CASE WHEN datapoint = 'humidity' THEN value END) AS mean_humidity,
    -- Median values
    percentile_cont(0.5) WITHIN GROUP (ORDER BY value) FILTER (WHERE datapoint = 'drybulb_temperature') AS median_drybulb_temperature,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY value) FILTER (WHERE datapoint = 'wetbulb_temperature') AS median_wetbulb_temperature,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY value) FILTER (WHERE datapoint = 'humidity') AS median_humidity
FROM raw_data
WHERE 
    device_id = 'outdoor_weather_station' 
    AND datapoint IN ('drybulb_temperature', 'wetbulb_temperature', 'humidity')
    AND (timestamp AT TIME ZONE 'timezone_placeholder')::TIME 
        BETWEEN 'business_hours_start' AND 'business_hours_end'
GROUP BY
    time_bucket('1 day', timestamp, 'timezone_placeholder'),
    site_id,
    device_id
WITH NO DATA;

-- Add refresh policy for final view
SELECT add_continuous_aggregate_policy('daily_weather_data',
    start_offset => INTERVAL '1 year',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => true,
    initial_start => 'initial_start_placeholder',
    timezone => 'timezone_placeholder'
);