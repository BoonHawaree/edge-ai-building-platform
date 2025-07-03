-- Create a continuous aggregate for the aggregated_data_1month materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS aggregated_data_1month
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 month', timestamp, 'timezone_placeholder') AS timestamp,
    model,
    site_id,
    device_id,
    datapoint,
    CASE
        -- Datapoints that should use LAST aggregation
        WHEN datapoint IN (
            'alarm', 'cumulative_carbon_footprint_reduction', 'cumulative_cooling_energy',
            'cumulative_energy', 'cumulative_energy_saving', 'cumulative_flow',
            'efficiency', 'efficiency_annual', 'efficiency_cdp', 'efficiency_cdp_ref',
            'efficiency_ch_ref', 'efficiency_chiller', 'efficiency_ct', 'efficiency_ct_ref',
            'efficiency_pchp', 'efficiency_pchp_ref', 'efficiency_ref', 'efficiency_schp',
            'efficiency_schp_ref', 'energy_recovery_efficiency', 'filter_status',
            'frequency_write', 'heating_valve_write', 'humidity_forecast_1h',
            'humidity_forecast_2h', 'humidity_forecast_3h', 'humidity_forecast_4h',
            'humidity_forecast_5h', 'humidity_forecast_6h', 'humidity_forecast_7h',
            'humidity_forecast_8h', 'humidity_forecast_9h', 'humidity_forecast_10h',
            'humidity_forecast_11h', 'humidity_forecast_12h', 'humidity_forecast_13h',
            'humidity_forecast_14h', 'humidity_forecast_15h', 'humidity_forecast_16h',
            'humidity_forecast_17h', 'humidity_forecast_18h', 'humidity_forecast_19h',
            'humidity_forecast_20h', 'humidity_forecast_21h', 'humidity_forecast_22h',
            'humidity_forecast_23h', 'humidity_forecast_24h', 'last_update_timestamp',
            'maintenance', 'mode', 'number_of_running_cdps', 'number_of_running_chillers',
            'number_of_running_cts', 'number_of_running_pchps', 'number_of_running_schps',
            'return_air_damper_write', 'return_air_temperature_setpoint',
            'return_exhaust_damper_write', 'runtime', 'setpoint_local', 'setpoint_read',
            'setpoint_write', 'speed_max', 'speed_setpoint', 'status', 'status_local',
            'status_read', 'status_write', 'supply_air_temperature_setpoint',
            'target_cdw_setpoint', 'target_chw_setpoint', 'temperature_forecast_1h',
            'temperature_forecast_2h', 'temperature_forecast_3h', 'temperature_forecast_4h',
            'temperature_forecast_5h', 'temperature_forecast_6h', 'temperature_forecast_7h',
            'temperature_forecast_8h', 'temperature_forecast_9h', 'temperature_forecast_10h',
            'temperature_forecast_11h', 'temperature_forecast_12h', 'temperature_forecast_13h',
            'temperature_forecast_14h', 'temperature_forecast_15h', 'temperature_forecast_16h',
            'temperature_forecast_17h', 'temperature_forecast_18h', 'temperature_forecast_19h',
            'temperature_forecast_20h', 'temperature_forecast_21h', 'temperature_forecast_22h',
            'temperature_forecast_23h', 'temperature_forecast_24h', 'trip_status',
            'weather_condition_forecast_1h', 'weather_condition_forecast_2h',
            'weather_condition_forecast_3h', 'weather_condition_forecast_4h',
            'weather_condition_forecast_5h', 'weather_condition_forecast_6h',
            'weather_condition_forecast_7h', 'weather_condition_forecast_8h',
            'weather_condition_forecast_9h', 'weather_condition_forecast_10h',
            'weather_condition_forecast_11h', 'weather_condition_forecast_12h',
            'weather_condition_forecast_13h', 'weather_condition_forecast_14h',
            'weather_condition_forecast_15h', 'weather_condition_forecast_16h',
            'weather_condition_forecast_17h', 'weather_condition_forecast_18h',
            'weather_condition_forecast_19h', 'weather_condition_forecast_20h',
            'weather_condition_forecast_21h', 'weather_condition_forecast_22h',
            'weather_condition_forecast_23h', 'weather_condition_forecast_24h',
            'fan_frequency_write', 'cooling_valve_write', 'supply_air_temperature_setpoint',
            'static_pressure_setpoint', 'uv_status',
            'purge_mode', 'smoke_detection', 'fire_alarm', 'fan_status', 'fan_trip',
            'compressor_status', 'compressor_1_status', 'compressor_2_status',
            'compressor_3_status', 'flow_rate_write', 'fan_speed_write', 'fan_speed',
            'cumulative_energy_sec_1', 'cumulative_energy_sec_2', 'cumulative_energy_sec_3',
            'cumulative_energy_sec_4', 'cumulative_energy_sec_5', 'cumulative_energy_sec_6',
            'solar_pv_cumulative_energy',
            'cumulative_energy_sec_3_1', 'cumulative_energy_sec_3_2',
            'cumulative_energy_sec_4_1', 'cumulative_energy_sec_4_2', 'cumulative_energy_sec_4_3',
            'cumulative_energy_sec_4_4', 'cumulative_energy_sec_4_5', 'cumulative_energy_sec_4_6',
            'cumulative_energy_sec_4_7', 'cumulative_energy_sec_4_8', 'cumulative_energy_sec_4_9',
            'cumulative_energy_sec_4_10',
            'cumulative_energy_sec_5_1', 'cumulative_energy_sec_5_2', 'cumulative_energy_sec_5_3',
            'cumulative_energy_sec_5_4', 'cumulative_energy_sec_5_5', 'cumulative_energy_sec_5_6',
            'cumulative_energy_sec_5_7', 'cumulative_energy_sec_5_8', 'cumulative_energy_sec_5_9',
            'cumulative_energy_sec_5_10', 'cumulative_energy_sec_5_11'
        ) THEN last(value, timestamp)
        -- All other datapoints: use AVG only on numeric values
        ELSE avg(CASE WHEN value IS NOT NULL THEN value ELSE NULL END)
    END AS value
FROM raw_data
GROUP BY
    time_bucket('1 month', timestamp, 'timezone_placeholder'),
    model,
    site_id,
    device_id,
    datapoint
WITH NO DATA;

-- Add refresh policy that runs every 1 day
SELECT add_continuous_aggregate_policy('aggregated_data_1month',
    start_offset => INTERVAL 'retention_interval_placeholder',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 day',
    initial_start => 'initial_start_placeholder',
    timezone => 'timezone_placeholder',
    if_not_exists => true
);