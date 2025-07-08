# budget_alto_os/Agents/LLMBridge/llmbridge/helper.py

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "Magicalmint@636",
    "host": "timescaledb",  # Use service name from docker-compose
    "port": 5432
}

def get_latest_iaq_for_zone(zone_id):
    """
    Returns the latest CO2, temperature, humidity for a given zone.
    """
    query = """
    SELECT s1.point_id, s1.value, s1.timestamp
    FROM sensor_data s1
    JOIN brick_points bp ON s1.point_id = bp.point_id
    JOIN brick_entities be ON bp.device_id = be.entity_id
    JOIN brick_relationships br ON be.entity_id = br.subject_id
    WHERE br.predicate = 'brick:hasLocation'
      AND br.object_id = %s
      AND bp.point_type IN ('co2', 'temperature', 'humidity')
      AND s1.timestamp = (
          SELECT MAX(s2.timestamp)
          FROM sensor_data s2
          WHERE s2.point_id = s1.point_id
      )
    """
    result = {}
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (zone_id,))
            for row in cur.fetchall():
                if row["point_id"].endswith("_co2"):
                    result["co2"] = row["value"]
                elif row["point_id"].endswith("_temperature"):
                    result["temperature"] = row["value"]
                elif row["point_id"].endswith("_humid"):
                    result["humidity"] = row["value"]
                result["timestamp"] = row["timestamp"]
    return result

def get_latest_power_for_meter(meter_id):
    """
    Returns the latest power value for a given meter.
    """
    query = """
    SELECT s.value, s.timestamp
    FROM sensor_data s
    WHERE s.point_id = %s
    ORDER BY s.timestamp DESC
    LIMIT 1
    """
    point_id = f"pm_{int(meter_id):03d}_power"
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (point_id,))
            row = cur.fetchone()
            if row:
                return {"power": row["value"], "timestamp": row["timestamp"]}
    return {}

def get_total_consumption_for_period(hours_ago: int) -> dict:
    """
    Calculates total energy consumption (kWh) from all power meters over a given period.
    This query assumes that the `value` column for power is in kW and readings are
    taken hourly. Therefore, summing the values provides an approximation of kWh.
    """
    point_ids = [f"pm_{i:03d}_power" for i in range(1, 6)]
    query = """
    SELECT SUM(value) as total_kwh
    FROM sensor_data
    WHERE point_id = ANY(%s)
    AND timestamp >= (NOW() - %s * INTERVAL '1 hour')
    """
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (point_ids, hours_ago))
            result = cur.fetchone()
            if result and result.get('total_kwh') is not None:
                return {"total_kwh": result['total_kwh']}
    return {"total_kwh": 0}

# Add more helpers as needed (trends, historical, etc.)