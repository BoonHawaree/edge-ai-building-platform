from langgraph.graph import StateGraph
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import START
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

def get_zone_current_conditions(zone: str):
    """Get current IAQ and power data for a specific building zone."""
    # Call your LLMBridge API
    resp = httpx.get(f"http://localhost:8000/api/current/iaq/{zone}")
    return resp.json()


def get_building_energy_status(hours: int):
    """Get current energy consumption vs daily targets."""
    resp = httpx.get(f"http://localhost:8000/api/trends/energy/{hours}")
    return resp.json()


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
)
llm_with_tools = llm.bind_tools(TOOLS)
sys_msg = SystemMessage(content=SYSTEM_PROMPT)

def assistant(state: dict):
    # state["messages"] should be a list of messages so far
    messages = state.get("messages", [])
    # Always start with the system prompt
    if not messages or messages[0] != sys_msg:
        messages = [sys_msg] + messages
    # LLM with tools
    result = llm_with_tools.invoke(messages)
    return {"messages": messages + [result]}

# --- LangGraph State Definition ---
from typing import TypedDict, Optional, Dict, Any

builder = StateGraph(dict)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(TOOLS))
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
builder.add_edge("tools", "assistant")
graph = builder.compile()

# Add more nodes for each use case (IAQ, energy, cross-zone, maintenance...)

# --- Entrypoint for LLM requests ---
async def process_building_automation_request(user_query: str):
    # Start with user message
    state = {"messages": [SystemMessage(content=SYSTEM_PROMPT), {"role": "user", "content": user_query}]}
    result = await graph.ainvoke(state)
    return result

# --- Example usage ---
if __name__ == "__main__":
    import asyncio
    user_query = "What is the current CO2 and temperature in zone_2_1? Should I take any action?"
    result = asyncio.run(process_building_automation_request(user_query))
    print(result)