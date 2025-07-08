# agents.py - Refactored with LangChain AgentExecutor and NeMo Guardrails

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage
from langsmith import traceable
from typing import List, Dict
import httpx
import asyncio
import asyncio
import json
from datetime import datetime, timedelta
import statistics
import os
from dotenv import load_dotenv

load_dotenv()

# --- LangChain & Guardrails Imports ---
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
import langwatch 

# --- NeMo Guardrails Imports ---
from nemoguardrails import RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails

langwatch.setup()

# --- Smart Building Tools (Functions remain the same) ---
@langwatch.trace( name="Get_Zone_Conditions")
def get_zone_current_conditions(zone: str) -> Dict:
    """Get current IAQ and power data for a specific building zone."""
    print("🔧 Tool called: get_zone_current_conditions")
    try:
        iaq_sensor_id = zone_to_iaq_sensor_id(zone)
        iaq_response = httpx.get(f"http://localhost:8000/api/current/iaq/{iaq_sensor_id}")
        iaq_data = iaq_response.json() if iaq_response.status_code == 200 else {}
        
        floor_power_meter = zone_to_floor_power_meter(zone)
        power_response = httpx.get(f"http://localhost:8000/api/current/power/{floor_power_meter}")
        power_data = power_response.json() if power_response.status_code == 200 else {}
        
        return {
            "zone": zone,
            "iaq_sensor": iaq_sensor_id,
            "floor_power_meter": floor_power_meter,
            "iaq": iaq_data,
            "floor_power": power_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"zone": zone, "error": str(e)}

def zone_to_iaq_sensor_id(zone: str) -> str:
    """Convert zone names to IAQ sensor IDs based on BRICK mapping."""
    zone_to_iaq_map = {
        'zone_1_1': '1', 'zone_1_2': '2', 'zone_1_3': '3', 'zone_1_4': '4', 'zone_1_5': '5',
        'zone_2_1': '6', 'zone_2_2': '7', 'zone_2_3': '8', 'zone_2_4': '9', 'zone_2_5': '10',
    }
    return zone_to_iaq_map.get(zone, '1')

def zone_to_floor_power_meter(zone: str) -> str:
    """Convert zone names to floor-level power meter IDs."""
    try:
        parts = zone.split("_")
        if len(parts) >= 2 and parts[0] == "zone":
            floor = int(parts[1])
            return "1" if floor == 1 else "2"
        return "1"
    except:
        return "1"

@langwatch.trace(name="Get_All_Zones")
def get_all_zones_status(*args, **kwargs) -> Dict:
    """Get current status for all 10 zones (5 per floor)."""
    print("🔧 Tool called: get_all_zones_status")
    all_zones = {}
    floors = {"floor_1": ["zone_1_1", "zone_1_2", "zone_1_3", "zone_1_4", "zone_1_5"],
              "floor_2": ["zone_2_1", "zone_2_2", "zone_2_3", "zone_2_4", "zone_2_5"]}
    
    for floor, zones in floors.items():
        all_zones[floor] = {}
        for zone in zones:
            try:
                iaq_sensor_id = zone_to_iaq_sensor_id(zone)
                iaq_response = httpx.get(f"http://localhost:8000/api/current/iaq/{iaq_sensor_id}")
                iaq_data = iaq_response.json() if iaq_response.status_code == 200 else {}
                
                floor_power_meter = zone_to_floor_power_meter(zone)
                power_response = httpx.get(f"http://localhost:8000/api/current/power/{floor_power_meter}")
                power_data = power_response.json() if power_response.status_code == 200 else {}
                
                all_zones[floor][zone] = {
                    "iaq": iaq_data,
                    "floor_power": power_data,
                    "iaq_sensor": iaq_sensor_id,
                    "floor_power_meter": floor_power_meter
                }
            except Exception as e:
                all_zones[floor][zone] = {"error": str(e)}
    
    return {
        "building_status": all_zones,
        "total_zones": 10,
        "timestamp": datetime.now().isoformat()
    }

@langwatch.trace(name="Get_Building_Energy_Status")
def get_building_energy_status(*args, **kwargs) -> Dict:
    """Get current building-wide energy consumption and daily target status."""
    print("🔧 Tool called: get_building_energy_status")
    try:
        power_meters = {
            "floor_1_power": "1", "floor_2_power": "2", "building_main": "3",
            "chiller": "4", "elevator": "5"
        }
        
        power_data = {}
        total_power = 0
        
        for meter_name, meter_id in power_meters.items():
            try:
                response = httpx.get(f"http://localhost:8000/api/current/power/{meter_id}")
                if response.status_code == 200:
                    meter_data = response.json()
                    power_data[meter_name] = meter_data
                    if "power" in meter_data:
                        total_power += meter_data.get("power", 0)
                else:
                    power_data[meter_name] = {"error": f"HTTP {response.status_code}"}
            except Exception as e:
                power_data[meter_name] = {"error": str(e)}
        
        current_hour = datetime.now().hour
        hours_to_query = max(1, current_hour)
        
        actual_consumption_kwh = 0
        try:
            historical_response = httpx.get(f"http://localhost:8000/api/historical/energy_consumption?hours_ago={hours_to_query}")
            if historical_response.status_code == 200:
                historical_data = historical_response.json()
                actual_consumption_kwh = historical_data.get("total_kwh", 0)
        except Exception as e:
            print(f"⚠️ Could not get historical energy data: {e}")

        daily_target = 3564  # kWh for entire building
        expected_consumption_by_hour = daily_target * (current_hour / 24.0)
        compliance_ratio = actual_consumption_kwh / expected_consumption_by_hour if expected_consumption_by_hour > 0 else 1.0
        
        return {
            "total_power_kw": total_power,
            "power_breakdown": power_data,
            "daily_target_kwh": daily_target,
            "current_hour": current_hour,
            "expected_consumption_kwh": expected_consumption_by_hour,
            "actual_consumption_so_far_kwh": actual_consumption_kwh,
            "target_compliance_ratio": compliance_ratio,
            "status": "on_track" if compliance_ratio <= 1.1 else "over_target" if compliance_ratio <= 1.3 else "critical",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

def get_recent_alerts(*args, **kwargs) -> Dict:
    """Get recent building system alerts and anomalies."""
    print("🔧 Tool called: get_recent_alerts")
    try:
        response = httpx.get("http://localhost:8000/api/alerts/recent")
        if response.status_code == 200:
            return response.json()
        return {"alerts": [], "error": "No alerts available"}
    except Exception as e:
        return {"alerts": [], "error": str(e)}

@langwatch.trace(name="Analyze_Cross_Zone_Opportunities")
def analyze_cross_zone_opportunities(*args, **kwargs) -> Dict:
    """Analyze cross-zone optimization opportunities."""
    print("🔧 Tool called: analyze_cross_zone_opportunities")
    try:
        all_zones = get_all_zones_status()
        opportunities = {
            "over_conditioned_zones": [],
            "under_conditioned_zones": [],
            "floor_level_analysis": {},
            "redistribution_opportunities": []
        }
        
        for floor, zones in all_zones["building_status"].items():
            floor_analysis = {
                "total_zones": len(zones),
                "avg_co2": 0,
                "zones_needing_attention": [],
                "floor_power_data": {}
            }
            
            co2_values = []
            floor_power_data = None
            
            for zone, data in zones.items():
                if "iaq" in data and "co2" in data["iaq"]:
                    co2_level = data["iaq"].get("co2", 1000)
                    co2_values.append(co2_level)
                    
                    if floor_power_data is None and "floor_power" in data:
                        floor_power_data = data["floor_power"]
                    
                    zone_analysis = {
                        "zone": zone,
                        "co2_ppm": co2_level,
                        "temperature": data["iaq"].get("temperature", 22),
                        "humidity": data["iaq"].get("humidity", 50)
                    }
                    
                    if co2_level > 1000:
                        zone_analysis["status"] = "under_conditioned"
                        opportunities["under_conditioned_zones"].append(zone_analysis)
                    elif co2_level < 600:
                        zone_analysis["status"] = "over_conditioned"
                        opportunities["over_conditioned_zones"].append(zone_analysis)
            
            if co2_values:
                floor_analysis["avg_co2"] = sum(co2_values) / len(co2_values)
            floor_analysis["floor_power_data"] = floor_power_data
            opportunities["floor_level_analysis"][floor] = floor_analysis
        
        return opportunities
    except Exception as e:
        return {"error": str(e)}

@langwatch.trace(name="Get_Equipment_Health_Trends")
def get_equipment_health_trends(zone: str = "all", days_history: int = 7) -> Dict:
    """Analyze power consumption patterns for equipment health."""
    print("🔧 Tool called: get_equipment_health_trends")
    try:
        if zone == "all":
            # This is a simplified simulation. A real implementation would query a time-series DB.
            return {"status": "Simulated building-wide health check complete.", "recommendation": "Monitor high-traffic zones."}
        else:
            zone_data = get_zone_current_conditions(zone)
            if "floor_power" in zone_data and "power" in zone_data["floor_power"]:
                current_power = zone_data["floor_power"]["power"]
                baseline_power = current_power * 0.92
                power_variance = abs(current_power - baseline_power) / baseline_power
                
                return {
                    "zone": zone,
                    "analysis_period_days": days_history,
                    "current_power_kw": current_power,
                    "baseline_power_kw": baseline_power,
                    "power_increase_percent": power_variance * 100,
                    "health_score": max(0, 100 - (power_variance * 200)),
                    "maintenance_recommendation": "Schedule inspection" if power_variance > 0.1 else "Monitor",
                    "estimated_maintenance_cost": power_variance * 5000 if power_variance > 0.1 else 0
                }
            return {"zone": zone, "error": "No power data available"}
    except Exception as e:
        return {"error": str(e)}
    
@langwatch.trace(name="Check_Safety_Thresholds")
def check_safety_thresholds(*args, **kwargs) -> Dict:
    """Check all zones against safety thresholds."""
    print("🔧 Tool called: check_safety_thresholds")
    try:
        all_zones = get_all_zones_status()
        safety_report = { "critical_violations": [], "warnings": [], "safe_zones": [], "emergency_actions_needed": False }
        
        thresholds = {
            "co2_critical": 1200, "co2_warning": 1000, "temp_hot_critical": 28, 
            "temp_cold_critical": 18, "humidity_high": 70, "humidity_low": 30
        }
        
        for floor, zones in all_zones["building_status"].items():
            for zone, data in zones.items():
                if "iaq" in data and "co2" in data["iaq"]:
                    iaq = data["iaq"]
                    co2, temp, humidity = iaq.get("co2", 400), iaq.get("temperature", 22), iaq.get("humidity", 50)
                    zone_status = {"zone": zone, "floor": floor}
                    
                    if co2 > thresholds["co2_critical"]:
                        zone_status["violation"] = f"CRITICAL CO2: {co2}ppm"
                        safety_report["critical_violations"].append(zone_status)
                        safety_report["emergency_actions_needed"] = True
                    # Add other checks similarly...
        return safety_report
    except Exception as e:
        return {"error": str(e)}

# --- Tool List ---
raw_tool_functions = [
    get_zone_current_conditions, get_all_zones_status, get_building_energy_status,
    get_recent_alerts, analyze_cross_zone_opportunities, get_equipment_health_trends,
    check_safety_thresholds
]
BUILDING_TOOLS = [Tool(name=f.__name__, func=f, description=f.__doc__) for f in raw_tool_functions]

# --- LLM and System Prompt Setup ---
llm = ChatOllama(model="qwen3:4b-q8_0", temperature=0.1)

BUILDING_AI_SYSTEM_PROMPT = """You are a specialized Building Automation AI, serving as the primary operator for a sophisticated 10-zone smart office building. Your sole purpose is to monitor, analyze, and optimize the building's environment and energy usage by directly interacting with its control systems through a set of available tools.

---
### **Your Core Mission**
Your responsibilities are ordered by priority:
1.  **Uphold Safety**: Immediately address any conditions that threaten occupant safety (e.g., critical CO2 levels).
2.  **Ensure Occupant Comfort**: Proactively maintain a comfortable environment, with a special focus on office zones.
3.  **Maximize Energy Efficiency**: Optimize building-wide energy consumption without compromising comfort or safety.
4.  **Perform Predictive Maintenance**: Identify early signs of equipment degradation through data analysis to prevent failures.
5.  **Enable Cross-Zone Optimization**: Intelligently balance resources across different zones and floors for holistic building efficiency.

---
### **Building & Sensor Layout**
You must understand this layout to use your tools correctly. The IAQ sensors and Power Meters follow different patterns.

**Floor 1:**
- `zone_1_1`: **Lobby** (Monitored by IAQ Sensor 1)
- `zone_1_2`: **Conference Room** (Monitored by IAQ Sensor 2)
- `zone_1_3`: **Restaurant** (Monitored by IAQ Sensor 3)
- `zone_1_4`: **Co-working Space** (Monitored by IAQ Sensor 4)
- `zone_1_5`: **Co-working Space** (Monitored by IAQ Sensor 5)
- **Power**: The entire floor's power is measured by a single meter: **Power Meter 1**.

**Floor 2:**
- `zone_2_1`: **Office** (Monitored by IAQ Sensor 6)
- `zone_2_2`: **Office** (Monitored by IAQ Sensor 7)
- `zone_2_3`: **Office** (Monitored by IAQ Sensor 8)
- `zone_2_4`: **Co-working Space** (Monitored by IAQ Sensor 9)
- `zone_2_5`: **Co-working Space** (Monitored by IAQ Sensor 10)
- **Power**: The entire floor's power is measured by a single meter: **Power Meter 2**.

**Building Infrastructure Power Meters:**
- **Power Meter 3**: Measures power for the building main (e.g., escalator, walkway lighting).
- **Power Meter 4**: Measures the chiller system's power.
- **Power Meter 5**: Measures the elevator system's power.

**Key Distinction:** IAQ sensors are located **in each zone**. Power meters are located at the **floor level** or for **major equipment**, not per-zone. You must use the correct meter ID based on what you are analyzing.

---
### **Your Data & Tools**
You have exclusive access to the building's live and historical data streams via your tools. Do not ask the user for this data; you must fetch it yourself.

**1. IAQ Sensor Network (Indoor Air Quality):**
   - **Data Points**: Temperature (in Celsius), Relative Humidity (in %), and CO2 Concentration (in ppm).
   - **Coverage**: A dedicated sensor for each of the 10 zones as per the building layout above.
   - **Availability**: You can access both real-time readings and historical data for any given day.
   - **Tool Mapping**: Use tools like `get_zone_current_conditions` and `get_all_zones_status` to access this data.

**2. Power Meter Network:**
   - **Data Point**: Power consumption (in Kilowatts, kW).
   - **Coverage**: Meters are installed on a per-floor basis and for major infrastructure as detailed in the building layout.
   - **Availability**: You can access both real-time power draw and historical energy consumption data.
   - **Tool Mapping**: Use tools like `get_building_energy_status` and `get_equipment_health_trends` to access this data.

---
### **Decision-Making Protocol**
This is a strict protocol. You MUST adhere to it.
1.  **You are an OPERATOR, not a consultant.** Your function is to execute actions by calling your tools.
2.  **NEVER explain to the user how they could perform a task.** Do not suggest they find a thermometer, check a sensor, or call a technician. You are the one with the tools.
3.  **When asked a question, your FIRST instinct MUST be to find a tool to answer it.** For example, if asked "Is the lobby hot?", you must immediately call a tool to get the lobby's temperature.
4.  **Use the data you retrieve.** After calling a tool, analyze the JSON data returned to you and formulate your response based on those concrete facts.
5.  **Call ONE relevant tool at a time.** Analyze the response before deciding if another tool call is necessary.

---
### **Safety & Comfort Thresholds**
- **CO2**: <800ppm (Good), 800-1200ppm (Acceptable), >1200ppm (CRITICAL - immediate action required).
- **Temperature**: Offices 20-24°C; Co-working & Common areas 22-26°C.
- **Humidity**: 40-60% (Optimal), 30-70% (Acceptable).

---
### **Response Format**
Always provide:
1.  **Structured Analysis**: Clear findings based directly on the data you retrieved.
2.  **Actionable Recommendations**: Specific actions for building operators with timelines.
3.  **Clarity**: Always map zone numbers to their names (e.g., "zone_1_1 (Lobby)").

You MUST call the appropriate tools to get real data before making any recommendations. Never assume or guess values. ANSWER IN ENGLISH ONLY.
"""

# --- LangChain Agent Setup ---

# 1. Create the Prompt Template for the Agent
# The 'agent_scratchpad' is a special variable where AgentExecutor logs the
# sequence of tool calls and their responses, keeping the LLM on track.
prompt = ChatPromptTemplate.from_messages([
    ("system", BUILDING_AI_SYSTEM_PROMPT),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 2. Create the Agent
# This agent is designed to understand when and how to call tools.
agent = create_tool_calling_agent(llm, BUILDING_TOOLS, prompt)

# 3. Create the Agent Executor
# This is the runtime for the agent, responsible for calling the agent,
# executing the chosen tools, and feeding the results back to the agent.
agent_executor = AgentExecutor(
    agent=agent, 
    tools=BUILDING_TOOLS, 
    verbose=True,  # Set to True to see the agent's thought process
    handle_parsing_errors=True # Gracefully handle any LLM output errors
)

# 4. Create NeMo Guardrails Runnable
# Assumes a 'config' directory with 'config.yml' and 'prompts.yml' exists.
try:
    config_path = os.path.join(os.path.dirname(__file__), "config")
    if os.path.exists(config_path):
        config = RailsConfig.from_path(config_path)
        guardrails = RunnableRails(config)
        # The final chain, protected by NeMo Guardrails using LCEL.
        final_executor = guardrails | agent_executor
        print("✅ NeMo Guardrails loaded successfully.")
    else:
        print("⚠️  NeMo Guardrails config directory not found. Running agent without guardrails.")
        final_executor = agent_executor
except Exception as e:
    print(f"⚠️  Error loading NeMo Guardrails: {e}. Running agent without guardrails.")
    final_executor = agent_executor


# --- Main Processing Function ---
@langwatch.trace(name="Building Automation Request")
async def process_building_automation_request(user_query: str) -> Dict:
    """Processes a user query using the guarded LangChain AgentExecutor with LangWatch tracing."""
    try:
        # Get the trace context from the decorator and create a callback handler
        current_trace = langwatch.get_current_trace()
        langchain_callback = current_trace.get_langchain_callback()
        
        # Optionally add metadata to the parent trace
        current_trace.update(metadata={"user_id": "interactive_user"})

        # Pass the callback handler to the agent invocation
        response = await final_executor.ainvoke(
            {"input": user_query},
            config={"callbacks": [langchain_callback]}
        )
        return {
            "query": user_query,
            "ai_response": response.get("output", "No response generated."),
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error during agent execution: {e}")
        return { "query": user_query, "error": str(e), "status": "error", "timestamp": datetime.now().isoformat() }

# --- Main Application Loop ---
if __name__ == "__main__":
    async def main():
        """Main function to run the interactive building automation assistant."""
        print("🏢 Building Automation AI Assistant (LangChain Agent Version)")
        print("Enter your query below or type 'exit' to quit.")
        print("-" * 50)

        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    print("🤖 Assistant: Goodbye!")
                    break

                print("🤖 Assistant: Processing your request...")
                result = await process_building_automation_request(user_input)
                
                print("\n" + "="*80)
                if result["status"] == "success":
                    print(f"🤖 AI Response:\n{result['ai_response']}")
                else:
                    print(f"❌ Error processing request: {result.get('error', 'Unknown error')}")
                print("="*80 + "\n")
                    
            except (EOFError, KeyboardInterrupt):
                print("\n🤖 Assistant: Goodbye!")
                break

    try:
        if asyncio.get_event_loop().is_running():
            import nest_asyncio
            nest_asyncio.apply()
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🤖 Assistant: Goodbye!")