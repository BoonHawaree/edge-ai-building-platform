-- Create action command history table for tracking executed commands
CREATE TABLE IF NOT EXISTS action_command_history (
    -- Primary identification
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Entity identification
    site_id VARCHAR NOT NULL,
    device_id VARCHAR NOT NULL,
    
    -- Command details
    datapoint VARCHAR NOT NULL,
    value DOUBLE PRECISION,
    command_type VARCHAR,
    priority INTEGER,
    
    -- Metadata
    source VARCHAR,
    status VARCHAR NOT NULL
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('action_command_history', 'executed_at', 
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 day'
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_ach_site_device_time 
    ON action_command_history (site_id, device_id, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_ach_source 
    ON action_command_history (source, executed_at DESC);

-- Add compression policy (optional - uncomment if needed)
-- ALTER TABLE action_command_history SET (
--     timescaledb.compress,
--     timescaledb.compress_segmentby = 'site_id,device_id',
--     timescaledb.compress_orderby = 'executed_at DESC'
-- );

-- Create retention policy (optional - uncomment and adjust retention period if needed)
-- SELECT add_retention_policy('action_command_history', INTERVAL '6 months');

-- Create continuous aggregate for daily statistics (optional - uncomment if needed)
-- CREATE MATERIALIZED VIEW action_command_daily_stats
-- WITH (timescaledb.continuous) AS
-- SELECT
--     time_bucket('1 day', executed_at) AS bucket,
--     site_id,
--     device_id,
--     COUNT(*) as total_commands,
--     COUNT(*) FILTER (WHERE status = 'success') as successful_commands,
--     COUNT(*) FILTER (WHERE status = 'failed') as failed_commands
-- FROM action_command_history
-- GROUP BY bucket, site_id, device_id;

-- Add refresh policy for continuous aggregate (uncomment if using the above view)
-- SELECT add_continuous_aggregate_policy('action_command_daily_stats',
--     start_offset => INTERVAL '1 month',
--     end_offset => INTERVAL '1 hour',
--     schedule_interval => INTERVAL '1 hour');

-- Comments for documentation
COMMENT ON TABLE action_command_history IS 'Historical log of executed action commands with timing and status information';
COMMENT ON COLUMN action_command_history.timestamp IS 'Timestamp when the command was executed';
COMMENT ON COLUMN action_command_history.site_id IS 'Site identifier where the command was executed';
COMMENT ON COLUMN action_command_history.device_id IS 'Device identifier that received the command';
COMMENT ON COLUMN action_command_history.datapoint IS 'The specific datapoint that was controlled';
COMMENT ON COLUMN action_command_history.value IS 'The value that was written to the datapoint';
COMMENT ON COLUMN action_command_history.command_type IS 'Type of command that was executed';
COMMENT ON COLUMN action_command_history.priority IS 'Priority level of the command';
COMMENT ON COLUMN action_command_history.source IS 'Source system or component that initiated the command';
COMMENT ON COLUMN action_command_history.status IS 'Execution status of the command (success/failed/etc)';
COMMENT ON COLUMN action_command_history.remark IS 'Additional notes or remarks about the command';