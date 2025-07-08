# budget_alto_os/Agents/LLMBridge/llmbridge/agent.py

import threading
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from volttron.platform.vip.agent import Agent, Core
from volttron.platform.agent import utils
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from . import helper

# --- Data Models for POST endpoints ---
class IAQAnalysisRequest(BaseModel):
    zone: str
    # Add more fields as needed

class EnergyAnalysisRequest(BaseModel):
    hours: int
    # Add more fields as needed

# --- FastAPI App ---
app = FastAPI(title="LLM Bridge Agent API")

@app.get("/api/current/iaq/{zone}")
async def get_current_iaq(zone: str):
    agent = app.state.agent
    data = agent.realtime_cache["iaq"].get(zone)
    if data:
        return {"zone": zone, **data}
    # Fallback: query TimescaleDB
    db_data = helper.get_latest_iaq_for_zone(zone)
    if db_data:
        return {"zone": zone, **db_data}
    return {"zone": zone, "error": "No data available"}

@app.get("/api/current/power/{meter}")
async def get_current_power(meter: str):
    agent = app.state.agent
    data = agent.realtime_cache["power"].get(meter)
    if data:
        return {"meter": meter, **data}
    # Fallback: query TimescaleDB
    db_data = helper.get_latest_power_for_meter(meter)
    if db_data:
        return {"meter": meter, **db_data}
    return {"meter": meter, "error": "No data available"}

@app.get("/api/alerts/recent")
async def get_recent_alerts():
    agent = app.state.agent
    return {"alerts": agent.realtime_cache["alerts"][-10:]}  # Last 10 alerts
    
@app.get("/api/historical/energy_consumption")
async def get_historical_energy_consumption(hours_ago: int = 24):
    """
    Calculates total energy consumption from historical data since a given number of hours ago.
    """
    if hours_ago <= 0:
        raise HTTPException(status_code=400, detail="hours_ago must be a positive integer.")
    
    db_data = helper.get_total_consumption_for_period(hours_ago)
    return {"hours_ago": hours_ago, **db_data}


@app.post("/api/analyze/iaq")
async def analyze_iaq(req: IAQAnalysisRequest):
    # TODO: Run LLM analysis on IAQ data for the given zone
    return {"zone": req.zone, "recommendation": "Increase ventilation in zone."}

@app.post("/api/analyze/energy")
async def analyze_energy(req: EnergyAnalysisRequest):
    # TODO: Run LLM analysis on energy data for the given hours
    return {"hours": req.hours, "recommendation": "Reduce overnight HVAC usage."}

# --- Volttron Agent that runs FastAPI ---
class LLMBridgeAgent(Agent):
    def __init__(self, config_path=None, **kwargs):
        super().__init__(**kwargs)
        self.realtime_cache = {
            "iaq": {},
            "power": {},
            "alerts": []
        }
        app.state.agent = self

        # DB connection info (customize as needed)
        self.db_host = os.environ.get("TSDB_HOST", "timescaledb")
        self.db_port = int(os.environ.get("TSDB_PORT", 5432))
        self.db_name = os.environ.get("TSDB_NAME", "postgres")
        self.db_user = os.environ.get("TSDB_USER", "postgres")
        self.db_password = os.environ.get("TSDB_PASSWORD", "Magicalmint@636")

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        # Subscribe to IAQ and powermeter topics
        self.vip.pubsub.subscribe(peer="pubsub", prefix="iaq", callback=self.on_iaq_update)
        self.vip.pubsub.subscribe(peer="pubsub", prefix="powermeter", callback=self.on_power_update)
        # Start FastAPI in a background thread
        def run_api():
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        threading.Thread(target=run_api, daemon=True).start()

    def on_iaq_update(self, peer, sender, bus, topic, headers, message):
    # topic: "iaq/{zone_id}"
        zone_id = topic.split("/")[1] if "/" in topic else "unknown"
        self.realtime_cache["iaq"][zone_id] = {
            "co2": message.get("co2"),
            "temperature": message.get("temperature"),
            "humidity": message.get("humidity"),
            "timestamp": message.get("timestamp")
        }
        # Example anomaly detection
        if message.get("co2", 0) > 1200:
            self.realtime_cache["alerts"].append({
                "type": "high_co2",
                "zone": zone_id,
                "value": message["co2"],
                "timestamp": message.get("timestamp")
            })
    def on_power_update(self, peer, sender, bus, topic, headers, message):
    # topic: "powermeter/{meter_id}"
        meter_id = topic.split("/")[1] if "/" in topic else "unknown"
        self.realtime_cache["power"][meter_id] = {
            "power": message.get("power"),
            "timestamp": message.get("timestamp")
            }
    
    

def main():
    utils.vip_main(LLMBridgeAgent, version="0.1")

if __name__ == "__main__":
    main()