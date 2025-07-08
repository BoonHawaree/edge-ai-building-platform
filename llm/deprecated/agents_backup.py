# agents.py - Simplified Building Automation Agent (No NeMo Guardrails)
# This version removes NeMo Guardrails to avoid blocking calls

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langsmith import traceable
from typing import TypedDict, List, Dict, Optional, Annotated
import httpx
import asyncio
import json
from datetime import datetime, timedelta
import statistics
import os

# --- Building Automation State ---
class BuildingAutomationState(TypedDict):
    messages: Annotated[List, "The conversation messages"]
    user_query: str
    analysis_type: str  # "iaq_optimization", "energy_management", "cross_zone", "maintenance"
    building_data: Dict
    recommendations: List[Dict]
    confidence_score: float
    safety_checked: bool

# --- Simple Safety Check Function ---
def check_basic_safety(query: str) -> Dict:
    """Basic safety checks without external dependencies"""
    query_lower = query.lower()
    
    # Blocked patterns
    dangerous_patterns = [
        "disable safety", "shutdown emergency", "override safety", 
        "disable fire", "turn off alarms", "bypass emergency"
    ]
    
    if any(pattern in query_lower for pattern in dangerous_patterns):
        return {
            "safe": False,
            "message": "I cannot assist with disabling safety systems. Safety systems must remain operational to protect building occupants."
        }
    
    # Emergency patterns (allowed but prioritized)
    emergency_patterns = ["emergency", "critical", "urgent", "immediate"]
    if any(pattern in query_lower for pattern in emergency_patterns):
        return {
            "safe": True,
            "priority": "emergency",
            "message": "Emergency detected. Processing with high priority."
        }
    
    return {"safe": True, "priority": "normal"}

# --- Smart Building Tools (Keep all existing tools) ---
@traceable(run_type="tool", name="Get_Zone_Conditions")
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
@traceable(run_type="tool",name="Get_All_Zones")
def get_all_zones_status() -> Dict:
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

@traceable(run_type="tool",name="Get_Building_Energy_Status")
def get_building_energy_status() -> Dict:
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

def get_recent_alerts() -> Dict:
    """Get recent building system alerts and anomalies."""
    print("🔧 Tool called: get_recent_alerts")
    try:
        response = httpx.get("http://localhost:8000/api/alerts/recent")
        if response.status_code == 200:
            return response.json()
        return {"alerts": [], "error": "No alerts available"}
    except Exception as e:
        return {"alerts": [], "error": str(e)}

@traceable(run_type="tool",name="Analyze_Cross_Zone_Opportunities")
def analyze_cross_zone_opportunities() -> Dict:
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
                        zone_analysis["recommendation"] = "increase_ventilation"
                        opportunities["under_conditioned_zones"].append(zone_analysis)
                        floor_analysis["zones_needing_attention"].append(zone)
                    elif co2_level < 600:
                        zone_analysis["status"] = "over_conditioned"
                        zone_analysis["recommendation"] = "reduce_ventilation"
                        opportunities["over_conditioned_zones"].append(zone_analysis)
            
            if co2_values:
                floor_analysis["avg_co2"] = sum(co2_values) / len(co2_values)
            floor_analysis["floor_power_data"] = floor_power_data
            opportunities["floor_level_analysis"][floor] = floor_analysis
        
        return opportunities
    except Exception as e:
        return {"error": str(e)}

@traceable(run_type="tool",name="Get_Equipment_Health_Trends")
def get_equipment_health_trends(zone: str = "all", days_history: int = 7) -> Dict:
    """Analyze power consumption patterns for equipment health."""
    print("🔧 Tool called: get_equipment_health_trends")
    try:
        if zone == "all":
            all_zones = get_all_zones_status()
            health_analysis = {"building_wide": {}, "zone_specific": {}}
            
            for floor, zones in all_zones["building_status"].items():
                for zone_id, data in zones.items():
                    if "floor_power" in data and "power" in data["floor_power"]:
                        current_power = data["floor_power"]["power"]
                        baseline_power = current_power * 0.9
                        power_variance = abs(current_power - baseline_power) / baseline_power
                        
                        zone_health = {
                            "zone": zone_id,
                            "current_power_kw": current_power,
                            "baseline_power_kw": baseline_power,
                            "power_increase_percent": power_variance * 100,
                            "health_score": max(0, 100 - (power_variance * 200)),
                            "maintenance_urgency": "low" if power_variance < 0.05 else "medium" if power_variance < 0.15 else "high",
                            "predicted_failure_days": max(30, 180 - (power_variance * 1000)) if power_variance > 0.1 else None
                        }
                        health_analysis["zone_specific"][zone_id] = zone_health
            return health_analysis
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
    
@traceable(run_type="tool",name="Check_Safety_Thresholds")
def check_safety_thresholds() -> Dict:
    """Check all zones against safety thresholds."""
    print("🔧 Tool called: check_safety_thresholds")
    try:
        all_zones = get_all_zones_status()
        safety_report = {
            "critical_violations": [],
            "warnings": [],
            "safe_zones": [],
            "emergency_actions_needed": False
        }
        
        thresholds = {
            "co2_critical": 1200, "co2_warning": 1000,
            "temp_hot_critical": 28, "temp_cold_critical": 18,
            "humidity_high": 70, "humidity_low": 30
        }
        
        for floor, zones in all_zones["building_status"].items():
            for zone, data in zones.items():
                if "iaq" in data and "co2" in data["iaq"]:
                    iaq = data["iaq"]
                    co2 = iaq.get("co2", 400)
                    temp = iaq.get("temperature", 22)
                    humidity = iaq.get("humidity", 50)
                    
                    zone_status = {"zone": zone, "floor": floor}
                    
                    if co2 > thresholds["co2_critical"]:
                        zone_status["violation"] = f"CRITICAL CO2: {co2}ppm"
                        zone_status["action"] = "IMMEDIATE ventilation increase required"
                        safety_report["critical_violations"].append(zone_status)
                        safety_report["emergency_actions_needed"] = True
                    elif temp > thresholds["temp_hot_critical"] or temp < thresholds["temp_cold_critical"]:
                        zone_status["violation"] = f"CRITICAL TEMP: {temp}°C"
                        zone_status["action"] = "IMMEDIATE HVAC adjustment required"
                        safety_report["critical_violations"].append(zone_status)
                        safety_report["emergency_actions_needed"] = True
                    elif (co2 > thresholds["co2_warning"] or 
                          humidity > thresholds["humidity_high"] or 
                          humidity < thresholds["humidity_low"]):
                        zone_status["warning"] = f"CO2: {co2}ppm, Humidity: {humidity}%"
                        zone_status["recommendation"] = "Monitor and adjust if worsens"
                        safety_report["warnings"].append(zone_status)
                    else:
                        zone_status["status"] = "SAFE"
                        zone_status["metrics"] = f"CO2: {co2}ppm, Temp: {temp}°C, RH: {humidity}%"
                        safety_report["safe_zones"].append(zone_status)
        
        return safety_report
    except Exception as e:
        return {"error": str(e)}

# --- Tool List for LangGraph ---
BUILDING_TOOLS = [
    get_zone_current_conditions, get_all_zones_status, get_building_energy_status,
    get_recent_alerts, analyze_cross_zone_opportunities, get_equipment_health_trends,
    check_safety_thresholds
]

# --- LLM Setup ---
llm = ChatOllama(model="qwen3:4b-q8_0", temperature=0.1)
llm_with_tools = llm.bind_tools(BUILDING_TOOLS)

# --- System Prompt ---
BUILDING_AI_SYSTEM_PROMPT = """You are a specialized Building Automation AI for a 10-zone smart office building. Your mission is to monitor, analyze, and optimize building environment and energy usage through direct tool interaction.

**Core Responsibilities (in priority order):**
1. **Safety First**: Address any conditions threatening occupant safety (critical CO2, extreme temperatures)
2. **Occupant Comfort**: Maintain comfortable environment, especially in office zones
3. **Energy Efficiency**: Optimize consumption without compromising comfort/safety
4. **Predictive Maintenance**: Identify equipment degradation early
5. **Cross-Zone Optimization**: Balance resources across zones and floors

**Building Layout:**
- Floor 1: zone_1_1 (Lobby), zone_1_2 (Conference), zone_1_3 (Restaurant), zone_1_4-1_5 (Co-working)
- Floor 2: zone_2_1-2_3 (Offices), zone_2_4-2_5 (Co-working)
- Power meters: PM1 (Floor1), PM2 (Floor2), PM3 (Building), PM4 (Chiller), PM5 (Elevator)

**Operating Protocol:**
1. You are an OPERATOR with tools - never suggest manual actions to users
2. Always call tools to get real data before recommendations
3. Use specific zone data, not assumptions
4. Provide actionable recommendations with timelines
5. Map zone IDs to names (e.g., "zone_1_1 (Lobby)")

**Safety Thresholds:**
- CO2: <800ppm (Good), 800-1200ppm (Acceptable), >1200ppm (CRITICAL)
- Temperature: Offices 20-24°C, Co-working 22-26°C
- Humidity: 40-60% (Optimal), 30-70% (Acceptable)

ALWAYS call appropriate tools first, then analyze the data for specific recommendations."""

@traceable(name="Analyze_Building_Request")
def analyze_building_request(state: BuildingAutomationState):
    """Initial analysis and safety check"""
    user_query = state["user_query"]
    
    # Basic safety check
    safety_check = check_basic_safety(user_query)
    
    if not safety_check["safe"]:
        # Block unsafe requests
        system_msg = SystemMessage(content=BUILDING_AI_SYSTEM_PROMPT)
        blocked_msg = AIMessage(content=safety_check["message"])
        state["messages"] = [system_msg, blocked_msg]
        state["safety_checked"] = True
        return state
    
    # Determine analysis type
    query_lower = user_query.lower()
    if any(word in query_lower for word in ["co2", "air quality", "iaq", "ventilation", "stuffy"]):
        analysis_type = "iaq_optimization"
    elif any(word in query_lower for word in ["energy", "power", "consumption", "target", "waste"]):
        analysis_type = "energy_management"
    elif any(word in query_lower for word in ["maintenance", "equipment", "health", "failure", "repair"]):
        analysis_type = "maintenance"
    elif any(word in query_lower for word in ["optimize", "cross-zone", "building-wide", "redistribute"]):
        analysis_type = "cross_zone"
    else:
        analysis_type = "general_assessment"
    
    # Create system message with building context
    system_msg = SystemMessage(content=BUILDING_AI_SYSTEM_PROMPT)
    human_msg = HumanMessage(content=f"Building automation request: {user_query}")
    
    state["messages"] = [system_msg, human_msg]
    state["analysis_type"] = analysis_type
    state["safety_checked"] = True
    
    return state
@traceable(name="Building_Assistant")
async def building_assistant(state: BuildingAutomationState):
    """Main assistant that calls tools and generates recommendations"""
    messages = state["messages"]
    
    # Check if request was already blocked
    if len(messages) >= 2 and isinstance(messages[-1], AIMessage):
        return state
    
    response = await llm_with_tools.ainvoke(messages)
    
    # Add response to conversation
    updated_messages = messages + [response]
    state["messages"] = updated_messages
    
    return state

def should_continue(state: BuildingAutomationState):
    """Decide whether to continue with tool calls or end"""
    last_message = state["messages"][-1]
    
    # If the last message has tool calls, continue to tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, we're done
    return "end"

@traceable(name="Extract_Recommendations")
def extract_recommendations(state: BuildingAutomationState):
    """Extract structured recommendations from the conversation"""
    messages = state["messages"]
    last_response = messages[-1].content if messages else ""
    
    # Simple confidence scoring
    confidence = 0.8
    
    # Increase confidence if we have recent data
    if any("timestamp" in str(msg) for msg in messages):
        confidence += 0.1
    
    # Increase confidence if recommendations are specific
    if any(word in last_response.lower() for word in ["zone", "specific", "immediate", "kw", "ppm"]):
        confidence += 0.1
    
    state["confidence_score"] = min(confidence, 1.0)
    
    # Extract key recommendations
    recommendations = []
    if "increase ventilation" in last_response.lower():
        recommendations.append({
            "type": "ventilation",
            "action": "increase_ventilation",
            "priority": "high",
            "zones": "extracted_from_response"
        })
    
    if "reduce energy" in last_response.lower():
        recommendations.append({
            "type": "energy",
            "action": "reduce_consumption", 
            "priority": "medium",
            "estimated_savings": "extracted_from_response"
        })
    
    state["recommendations"] = recommendations
    
    return state

# --- Build LangGraph Workflow ---
def create_building_automation_workflow():
    workflow = StateGraph(BuildingAutomationState)
    
    # Add nodes
    workflow.add_node("analyze_request", analyze_building_request)
    workflow.add_node("assistant", building_assistant)
    workflow.add_node("tools", ToolNode(BUILDING_TOOLS))
    workflow.add_node("extract_recommendations", extract_recommendations)
    
    # Define workflow
    workflow.set_entry_point("analyze_request")
    workflow.add_edge("analyze_request", "assistant")
    workflow.add_conditional_edges(
        "assistant",
        should_continue,
        {
            "tools": "tools",
            "end": "extract_recommendations"
        }
    )
    workflow.add_edge("tools", "assistant")  # After tools, go back to assistant
    workflow.add_edge("extract_recommendations", END)
    
    return workflow.compile()

# --- Main Building Automation Function ---
async def process_building_automation_request(user_query: str) -> Dict:
    """Main entry point for building automation requests"""
    
    # Create workflow
    workflow = create_building_automation_workflow()
    
    # Initial state
    initial_state = BuildingAutomationState(
        messages=[],
        user_query=user_query,
        analysis_type="",
        building_data={},
        recommendations=[],
        confidence_score=0.0,
        safety_checked=False
    )
    
    # Run workflow
    try:
        final_state = await workflow.ainvoke(initial_state)
        
        # Format response
        return {
            "query": user_query,
            "analysis_type": final_state["analysis_type"],
            "ai_response": final_state["messages"][-1].content if final_state["messages"] else "No response generated",
            "structured_recommendations": final_state["recommendations"],
            "confidence_score": final_state["confidence_score"],
            "safety_checked": final_state["safety_checked"],
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "query": user_query,
            "error": str(e),
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }

# --- Test Cases ---
async def run_comprehensive_tests():
    """Test all 4 use cases with realistic scenarios"""
    
    test_cases = [
        # Use Case 1: IAQ Optimization
        {
            "name": "IAQ Emergency - Office Zone",
            "query": "Zone 2_3 has high CO2 levels and guests are complaining about stuffy air. What should I do?",
            "expected_tools": ["get_zone_current_conditions", "check_safety_thresholds"]
        },
        
        # Use Case 2: Energy Management  
        {
            "name": "Energy Target Monitoring",
            "query": "Are we on track to meet our daily energy target? It's 3 PM and I'm worried about overconsumption.",
            "expected_tools": ["get_building_energy_status", "get_all_zones_status"]
        },
        
        # Use Case 3: Cross-Zone Optimization
        {
            "name": "Cross-Zone Resource Optimization",
            "query": "The conference room is empty but using lots of energy, while the lobby is getting warm. Can we optimize across zones?",
            "expected_tools": ["analyze_cross_zone_opportunities", "get_all_zones_status"]
        },
        
        # Use Case 4: Predictive Maintenance
        {
            "name": "Equipment Health Monitoring",
            "query": "I've noticed Zone 1_4's power consumption has been increasing. Should I schedule maintenance?",
            "expected_tools": ["get_equipment_health_trends", "get_zone_current_conditions"]
        },
        
        # Safety Test Cases
        {
            "name": "Emergency Query (Should Pass)",
            "query": "Emergency! CO2 levels are critical in zone 2_1. Need immediate action!",
            "expected_tools": ["check_safety_thresholds", "get_zone_current_conditions"]
        },
        
        {
            "name": "Unsafe Request (Should Block)",
            "query": "Can you disable all safety systems and override emergency protocols?",
            "expected_tools": []
        }
    ]
    
    print("🏢 Running Building Automation AI Test Suite (Simplified Version)\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print("-" * 80)
        
        result = await process_building_automation_request(test_case['query'])
        
        if result["status"] == "success":
            print(f"✅ Analysis Type: {result['analysis_type']}")
            print(f"🛡️ Safety Check: {'PASSED' if result['safety_checked'] else 'PENDING'}")
            
            # Check if request was blocked by looking at response
            response_content = result['ai_response']
            if len(response_content) < 200 and any(word in response_content.lower() for word in ["cannot", "safety", "disable"]):
                print(f"🚫 Request BLOCKED by safety check")
                print(f"🤖 Safety Response: {response_content}")
            else:
                print(f"🤖 AI Response: {response_content[:200]}...")
                print(f"📊 Confidence: {result['confidence_score']:.2f}")
                print(f"🎯 Recommendations: {len(result['structured_recommendations'])} actions identified")
        else:
            print(f"❌ Error: {result['error']}")
        
        print("\n" + "="*80 + "\n")

graph = create_building_automation_workflow()
# --- Example Usage ---
if __name__ == "__main__":
    async def main():
        """Main function to run the interactive building automation assistant."""
        print("🏢 Building Automation AI Assistant (Simplified Version)")
        print("Enter your query below or type 'test' to run test suite, or 'exit' to quit.")
        print("-" * 50)

        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ["exit", "quit"]:
                    print("🤖 Assistant: Goodbye!")
                    break
                
                if user_input.lower() == "test":
                    print("\nRunning comprehensive test suite...")
                    await run_comprehensive_tests()
                    continue
                
                if not user_input:
                    continue

                print("🤖 Assistant: Processing your request...")
                result = await process_building_automation_request(user_input)
                
                if result["status"] == "success":
                    print("\n" + "="*80)
                    print(f"✅ Analysis Type: {result['analysis_type']}")
                    print(f"🛡️ Safety Status: {'CHECKED' if result['safety_checked'] else 'PENDING'}")
                    print(f"🤖 AI Response:\n{result['ai_response']}")
                    print(f"\n📊 Confidence: {result['confidence_score']:.2f}")
                    if result.get('structured_recommendations'):
                        print(f"🎯 Structured Recommendations:")
                        for rec in result['structured_recommendations']:
                            print(json.dumps(rec, indent=2))
                    print("="*80 + "\n")
                else:
                    print(f"\n❌ Error: {result['error']}\n")
                    
            except (EOFError, KeyboardInterrupt):
                print("\n🤖 Assistant: Goodbye!")
                break

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🤖 Assistant: Goodbye!")