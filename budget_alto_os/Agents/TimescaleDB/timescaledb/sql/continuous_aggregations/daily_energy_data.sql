-- Create a continuous aggregate for the daily_energy_data materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_energy_data
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp, 'timezone_placeholder') AS timestamp,
    min(timestamp) AS start_datetime,
    max(timestamp) AS end_datetime,
    site_id,
    device_id,
    CASE
        WHEN datapoint IN ('cumulative_energy', 'power') THEN 'daily_energy'
        WHEN datapoint IN ('cumulative_cooling_energy', 'cooling_rate') THEN 'daily_cooling_energy'
        WHEN datapoint IN ('drybulb_temperature', 'wetbulb_temperature', 'humidity') THEN datapoint
    END AS datapoint,
    CASE
        -- Energy from cumulative_energy
        WHEN MIN(CASE 
            WHEN datapoint = 'cumulative_energy' THEN 1
            WHEN datapoint = 'power' THEN 2
            ELSE 3 
        END) = 1 THEN 
            LAST(value, timestamp) FILTER (WHERE datapoint = 'cumulative_energy') -
            FIRST(value, timestamp) FILTER (WHERE datapoint = 'cumulative_energy')
        -- Cooling energy from cumulative_cooling_energy
        WHEN MIN(CASE 
            WHEN datapoint = 'cumulative_cooling_energy' THEN 1
            WHEN datapoint = 'cooling_rate' THEN 2
            ELSE 3
        END) = 1 THEN
            LAST(value, timestamp) FILTER (WHERE datapoint = 'cumulative_cooling_energy') -
            FIRST(value, timestamp) FILTER (WHERE datapoint = 'cumulative_cooling_energy')
        -- Energy from power
        WHEN MIN(CASE 
            WHEN datapoint = 'power' THEN 1
            ELSE 2
        END) = 1 THEN 
            avg(CASE WHEN datapoint = 'power' THEN value END) * operation_hours
        -- Cooling energy from cooling_rate
        WHEN MIN(CASE 
            WHEN datapoint = 'cooling_rate' THEN 1
            ELSE 2
        END) = 1 THEN 
            avg(CASE WHEN datapoint = 'cooling_rate' THEN value END) * operation_hours
        -- Weather data averages
        WHEN MIN(CASE 
            WHEN datapoint IN ('drybulb_temperature', 'wetbulb_temperature', 'humidity') THEN 1
            ELSE 2
        END) = 1 THEN
            avg(value)
        ELSE NULL
    END AS value
FROM raw_data
WHERE 
    (
        datapoint IN ('cumulative_energy', 'cumulative_cooling_energy', 'power', 'cooling_rate')
        OR (
            device_id = 'outdoor_weather_station' 
            AND datapoint IN ('drybulb_temperature', 'wetbulb_temperature', 'humidity')
        )
    )
    AND (timestamp AT TIME ZONE 'timezone_placeholder')::TIME 
        BETWEEN 'business_hours_start' AND 'business_hours_end'
GROUP BY
    time_bucket('1 day', timestamp, 'timezone_placeholder'),
    site_id,
    device_id,
    CASE
        WHEN datapoint IN ('cumulative_energy', 'power') THEN 'daily_energy'
        WHEN datapoint IN ('cumulative_cooling_energy', 'cooling_rate') THEN 'daily_cooling_energy'
        WHEN datapoint IN ('drybulb_temperature', 'wetbulb_temperature', 'humidity') THEN datapoint
    END
WITH NO DATA;

-- Add refresh policy for final view
SELECT add_continuous_aggregate_policy('daily_energy_data',
    start_offset => INTERVAL '1 year',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => true,
    initial_start => 'initial_start_placeholder',
    timezone => 'timezone_placeholder'
);
