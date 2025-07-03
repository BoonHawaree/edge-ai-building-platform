from langgraph.graph import StateGraph
from langchain_ollama import ChatOllama
from langchain.tools import tool
import httpx
import asyncio


# --- System Prompt ---
SYSTEM_PROMPT = """
You are an expert building automation AI assistant. Your role is to:
1. Monitor building systems (IAQ, energy, HVAC) for optimal performance
2. Detect anomalies and recommend corrective actions
3. Prioritize occupant safety and comfort
4. Optimize energy efficiency while maintaining comfort
5. Provide clear, actionable recommendations for building operators

  You must always call the available tools to get real data before making any recommendations. Never make up or assume values.

Always consider:
- Safety thresholds (CO2 >1200ppm = critical, temp >26°C = too hot)
- Energy efficiency opportunities
- Comfort vs efficiency trade-offs
- Equipment health and maintenance needs
"""

# --- Tool Definitions (function calling) ---
@tool
def get_zone_current_conditions(zone: str):
    """Get current IAQ and power data for a specific building zone."""
    # Call your LLMBridge API
    resp = httpx.get(f"http://localhost:8000/api/current/iaq/{zone}")
    return resp.json()

@tool
def get_building_energy_status(hours: int):
    """Get current energy consumption vs daily targets."""
    resp = httpx.get(f"http://localhost:8000/api/trends/energy/{hours}")
    return resp.json()

@tool
def get_recent_alerts():
    """Get recent building system alerts or anomalies."""
    resp = httpx.get("http://localhost:8000/api/alerts/recent")
    return resp.json()

# Add more tools as needed...

TOOLS = [get_zone_current_conditions, get_building_energy_status, get_recent_alerts]

# --- LLM Setup ---
llm = ChatOllama(
    model="mistral:7b-instruct-v0.3-q4_0",
    temperature=0.1,
    tools=TOOLS
)

# --- LangGraph State Definition ---
from typing import TypedDict, Optional, Dict, Any

class BuildingAutomationState(TypedDict):
    request_type: str
    zone_filter: Optional[str]
    realtime_iaq: Optional[Dict[str, Any]]
    realtime_power: Optional[Dict[str, Any]]
    historical_data: Optional[Dict[str, Any]]
    building_context: str
    analysis_results: Optional[Dict[str, Any]]
    recommendations: Optional[Any]
    confidence_score: Optional[float]

# --- LangGraph Workflow Nodes ---
async def analyze_building_data(state: BuildingAutomationState):
    # Explicitly ask LLM to use tools
    zone = state.get("zone_filter", "all")
    user_msg = (
        f"Use the available tools to get the latest IAQ and power data for zone {zone}. "
        "Then, analyze the data and provide recommendations for building optimization."
    )
    result = await llm.ainvoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg}
    ])
    state["analysis_results"] = result
    return state

# Add more nodes for each use case (IAQ, energy, cross-zone, maintenance...)

# --- Build the LangGraph Workflow ---
def create_building_automation_workflow():
    workflow = StateGraph(BuildingAutomationState)
    workflow.add_node("analyze_building_data", analyze_building_data)
    # Add more nodes and edges as per your sprint plan...
    workflow.set_entry_point("analyze_building_data")
    return workflow.compile()

# --- Entrypoint for LLM requests ---
async def process_building_automation_request(request_type, zone_filter=None):
    initial_state = BuildingAutomationState(
        request_type=request_type,
        zone_filter=zone_filter,
        realtime_iaq=None,
        realtime_power=None,
        historical_data=None,
        building_context="hotel_office_10_zones_2_floors",
        analysis_results=None,
        recommendations=None,
        confidence_score=None
    )
    workflow = create_building_automation_workflow()
    result = await workflow.ainvoke(initial_state)
    return result

# --- Example usage ---
if __name__ == "__main__":
    # For quick test
    result = asyncio.run(process_building_automation_request("iaq_optimization", zone_filter="zone_1_1"))
    print(result)