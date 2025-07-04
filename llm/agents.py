# agents.py - Complete Building Automation Agent for Day 3 Sprint

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from typing import TypedDict, List, Dict, Optional, Annotated
import httpx
import asyncio
import json
from datetime import datetime, timedelta
import statistics

# --- Building Automation State ---
class BuildingAutomationState(TypedDict):
    messages: Annotated[List, "The conversation messages"]
    user_query: str
    analysis_type: str  # "iaq_optimization", "energy_management", "cross_zone", "maintenance"
    building_data: Dict
    recommendations: List[Dict]
    confidence_score: float

# --- Smart Building Tools ---

def get_zone_current_conditions(zone: str) -> Dict:
    """
    Get current IAQ and power data for a specific building zone.
    
    Args:
        zone: Zone ID (e.g., "zone_1_1", "zone_2_3")
    
    Returns:
        Dict containing current IAQ and power data for the zone
    """
    print("🔧 Tool called: get_zone_current_conditions")
    try:
        # Convert zone to IAQ sensor ID (zone_1_1 -> iaq_001, zone_2_3 -> iaq_008)
        iaq_sensor_id = zone_to_iaq_sensor_id(zone)
        iaq_response = httpx.get(f"http://localhost:8000/api/current/iaq/{iaq_sensor_id}")
        iaq_data = iaq_response.json() if iaq_response.status_code == 200 else {}
        
        # Get floor-level power data (zone_1_x -> pm_001, zone_2_x -> pm_002)
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
    """
    Convert zone names to IAQ sensor IDs based on BRICK mapping.
    
    Args:
        zone: Zone name like "zone_1_1", "zone_2_3"
    
    Returns:
        IAQ sensor ID as string like "1", "8"
    """
    zone_to_iaq_map = {
        'zone_1_1': '1',  # iaq_001
        'zone_1_2': '2',  # iaq_002
        'zone_1_3': '3',  # iaq_003
        'zone_1_4': '4',  # iaq_004
        'zone_1_5': '5',  # iaq_005
        'zone_2_1': '6',  # iaq_006
        'zone_2_2': '7',  # iaq_007
        'zone_2_3': '8',  # iaq_008
        'zone_2_4': '9',  # iaq_009
        'zone_2_5': '10', # iaq_010
    }
    return zone_to_iaq_map.get(zone, '1')  # Default to sensor 1 if not found

def zone_to_floor_power_meter(zone: str) -> str:
    """
    Convert zone names to floor-level power meter IDs based on BRICK mapping.
    
    Args:
        zone: Zone name like "zone_1_1", "zone_2_3"
    
    Returns:
        Power meter ID as string like "1", "2"
    """
    try:
        # Extract floor number from zone name
        parts = zone.split("_")
        if len(parts) >= 2 and parts[0] == "zone":
            floor = int(parts[1])
            if floor == 1:
                return "1"  # pm_001 feeds floor_1
            elif floor == 2:
                return "2"  # pm_002 feeds floor_2
        return "1"  # Default to floor 1 power meter
    except:
        return "1"

def get_all_zones_status() -> Dict:
    """
    Get current status for all 10 zones (5 per floor).
    
    Returns:
        Dict containing status for all zones organized by floor
    """
    print("🔧 Tool called: get_all_zones_status")
    all_zones = {}
    floors = {"floor_1": ["zone_1_1", "zone_1_2", "zone_1_3", "zone_1_4", "zone_1_5"],
              "floor_2": ["zone_2_1", "zone_2_2", "zone_2_3", "zone_2_4", "zone_2_5"]}
    
    for floor, zones in floors.items():
        all_zones[floor] = {}
        for zone in zones:
            try:
                # Get IAQ data with correct sensor mapping
                iaq_sensor_id = zone_to_iaq_sensor_id(zone)
                iaq_response = httpx.get(f"http://localhost:8000/api/current/iaq/{iaq_sensor_id}")
                iaq_data = iaq_response.json() if iaq_response.status_code == 200 else {}
                
                # Get floor-level power data
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

def get_building_energy_status() -> Dict:
    """
    Get current building-wide energy consumption and daily target status.
    Includes floor-level and building infrastructure power consumption.
    
    Returns:
        Dict containing comprehensive energy consumption summary
    """
    print("🔧 Tool called: get_building_energy_status")
    try:
        # Get power data from all meters based on BRICK mapping
        power_meters = {
            "floor_1_power": "1",      # pm_001 feeds floor_1
            "floor_2_power": "2",      # pm_002 feeds floor_2  
            "building_main": "3",      # pm_003 feeds building_main
            "chiller": "4",           # pm_004 feeds chiller
            "elevator": "5"           # pm_005 feeds elevator
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
                        total_power += meter_data["power"]
                else:
                    power_data[meter_name] = {"error": f"HTTP {response.status_code}"}
            except Exception as e:
                power_data[meter_name] = {"error": str(e)}
        
        # Calculate daily target compliance
        current_hour = datetime.now().hour
        daily_target = 2400  # kWh for entire building
        expected_consumption_by_hour = daily_target * (current_hour / 24)
        current_consumption_estimate = total_power * current_hour  # Simplified calculation
        
        compliance_ratio = current_consumption_estimate / expected_consumption_by_hour if expected_consumption_by_hour > 0 else 1.0
        
        return {
            "total_power_kw": total_power,
            "power_breakdown": power_data,
            "daily_target_kwh": daily_target,
            "current_hour": current_hour,
            "expected_consumption_kwh": expected_consumption_by_hour,
            "estimated_consumption_kwh": current_consumption_estimate,
            "target_compliance_ratio": compliance_ratio,
            "status": "on_track" if compliance_ratio <= 1.1 else "over_target" if compliance_ratio <= 1.3 else "critical",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

def get_recent_alerts() -> Dict:
    """
    Get recent building system alerts and anomalies.
    
    Returns:
        Dict containing recent alerts from the building systems
    """
    print("🔧 Tool called: get_recent_alerts")
    try:
        response = httpx.get("http://localhost:8000/api/alerts/recent")
        if response.status_code == 200:
            return response.json()
        return {"alerts": [], "error": "No alerts available"}
    except Exception as e:
        return {"alerts": [], "error": str(e)}

def analyze_cross_zone_opportunities() -> Dict:
    """
    Analyze cross-zone optimization opportunities for energy and comfort redistribution.
    Now considers floor-level power constraints and zone-level IAQ data.
    
    Returns:
        Dict containing cross-zone optimization analysis and recommendations
    """
    print("🔧 Tool called: analyze_cross_zone_opportunities")
    try:
        all_zones = get_all_zones_status()
        opportunities = {
            "over_conditioned_zones": [],
            "under_conditioned_zones": [],
            "floor_level_analysis": {},
            "redistribution_opportunities": []
        }
        
        # Analyze each floor separately since power is measured at floor level
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
                    
                    # Get floor power data (same for all zones on same floor)
                    if floor_power_data is None and "floor_power" in data:
                        floor_power_data = data["floor_power"]
                    
                    # Zone-level analysis
                    zone_analysis = {
                        "zone": zone,
                        "co2_ppm": co2_level,
                        "temperature": data["iaq"].get("temperature", 22),
                        "humidity": data["iaq"].get("humidity", 50)
                    }
                    
                    # Determine if zone needs attention
                    if co2_level > 1000:  # Poor air quality
                        zone_analysis["status"] = "under_conditioned"
                        zone_analysis["recommendation"] = "increase_ventilation"
                        opportunities["under_conditioned_zones"].append(zone_analysis)
                        floor_analysis["zones_needing_attention"].append(zone)
                    elif co2_level < 600:  # Excellent air quality
                        zone_analysis["status"] = "over_conditioned"
                        zone_analysis["recommendation"] = "reduce_ventilation"
                        opportunities["over_conditioned_zones"].append(zone_analysis)
            
            # Floor-level summary
            if co2_values:
                floor_analysis["avg_co2"] = sum(co2_values) / len(co2_values)
            floor_analysis["floor_power_data"] = floor_power_data
            opportunities["floor_level_analysis"][floor] = floor_analysis
        
        # Generate cross-floor redistribution opportunities
        floor1_analysis = opportunities["floor_level_analysis"].get("floor_1", {})
        floor2_analysis = opportunities["floor_level_analysis"].get("floor_2", {})
        
        if floor1_analysis and floor2_analysis:
            floor1_avg_co2 = floor1_analysis.get("avg_co2", 800)
            floor2_avg_co2 = floor2_analysis.get("avg_co2", 800)
            
            if abs(floor1_avg_co2 - floor2_avg_co2) > 200:  # Significant difference
                source_floor = "floor_1" if floor1_avg_co2 < floor2_avg_co2 else "floor_2"
                target_floor = "floor_2" if source_floor == "floor_1" else "floor_1"
                
                opportunities["redistribution_opportunities"].append({
                    "type": "cross_floor_optimization",
                    "source_floor": source_floor,
                    "target_floor": target_floor,
                    "co2_difference": abs(floor1_avg_co2 - floor2_avg_co2),
                    "recommendation": f"Reduce ventilation on {source_floor}, increase on {target_floor}"
                })
        
        return opportunities
    except Exception as e:
        return {"error": str(e)}

def get_equipment_health_trends(zone: str = "all", days_history: int = 7) -> Dict:
    """
    Analyze power consumption patterns for equipment health and maintenance prediction.
    
    Args:
        zone: Specific zone to analyze or "all" for building-wide analysis
        days_history: Number of days of historical data to analyze
    
    Returns:
        Dict containing equipment health analysis and maintenance predictions
    """
    print("🔧 Tool called: get_equipment_health_trends")
    try:
        # In a real system, this would query historical data from TimescaleDB
        # For now, we'll simulate based on current data + trends
        if zone == "all":
            all_zones = get_all_zones_status()
            health_analysis = {"building_wide": {}, "zone_specific": {}}
            
            for floor, zones in all_zones["building_status"].items():
                for zone_id, data in zones.items():
                    if "power" in data and "power" in data["power"]:
                        current_power = data["power"]["power"]
                        
                        # Simulate trend analysis (would be real historical data)
                        # Generate realistic power trend simulation
                        baseline_power = current_power * 0.9  # Assume 10% degradation
                        power_variance = abs(current_power - baseline_power) / baseline_power
                        
                        zone_health = {
                            "zone": zone_id,
                            "current_power_kw": current_power,
                            "baseline_power_kw": baseline_power,
                            "power_increase_percent": power_variance * 100,
                            "health_score": max(0, 100 - (power_variance * 200)),  # 0-100 scale
                            "maintenance_urgency": "low" if power_variance < 0.05 else "medium" if power_variance < 0.15 else "high",
                            "predicted_failure_days": max(30, 180 - (power_variance * 1000)) if power_variance > 0.1 else None
                        }
                        
                        health_analysis["zone_specific"][zone_id] = zone_health
            
            return health_analysis
        else:
            # Single zone analysis
            zone_data = get_zone_current_conditions(zone)
            if "power" in zone_data and "power" in zone_data["power"]:
                current_power = zone_data["power"]["power"]
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

def check_safety_thresholds() -> Dict:
    """
    Check all zones against safety thresholds for CO2, temperature, and humidity.
    
    Returns:
        Dict containing safety threshold violations and emergency recommendations
    """
    print("🔧 Tool called: check_safety_thresholds")
    try:
        all_zones = get_all_zones_status()
        safety_report = {
            "critical_violations": [],
            "warnings": [],
            "safe_zones": [],
            "emergency_actions_needed": False
        }
        
        # Safety thresholds
        thresholds = {
            "co2_critical": 1200,  # ppm
            "co2_warning": 1000,
            "temp_hot_critical": 28,  # Celsius
            "temp_cold_critical": 18,
            "humidity_high": 70,  # %
            "humidity_low": 30
        }
        
        for floor, zones in all_zones["building_status"].items():
            for zone, data in zones.items():
                if "iaq" in data and "co2" in data["iaq"]:
                    iaq = data["iaq"]
                    co2 = iaq.get("co2", 400)
                    temp = iaq.get("temperature", 22)
                    humidity = iaq.get("humidity", 50)
                    
                    zone_status = {"zone": zone, "floor": floor}
                    
                    # Check critical violations
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
                    
                    # Check warnings
                    elif (co2 > thresholds["co2_warning"] or 
                          humidity > thresholds["humidity_high"] or 
                          humidity < thresholds["humidity_low"]):
                        zone_status["warning"] = f"CO2: {co2}ppm, Humidity: {humidity}%"
                        zone_status["recommendation"] = "Monitor and adjust if worsens"
                        safety_report["warnings"].append(zone_status)
                    
                    # Safe zones
                    else:
                        zone_status["status"] = "SAFE"
                        zone_status["metrics"] = f"CO2: {co2}ppm, Temp: {temp}°C, RH: {humidity}%"
                        safety_report["safe_zones"].append(zone_status)
        
        return safety_report
    except Exception as e:
        return {"error": str(e)}

# --- Tool List for LangGraph ---
BUILDING_TOOLS = [
    get_zone_current_conditions,
    get_all_zones_status, 
    get_building_energy_status,
    get_recent_alerts,
    analyze_cross_zone_opportunities,
    get_equipment_health_trends,
    check_safety_thresholds
]

# --- LLM Setup with Tools ---
llm = ChatOllama(
    model="qwen3:4b-q8_0",
    temperature=0.1,
)


llm_with_tools = llm.bind_tools(BUILDING_TOOLS)

# --- Building Automation System Prompt ---
BUILDING_AI_SYSTEM_PROMPT = """You are an expert Building Automation AI for a 10-zones office building with the following layout:

**Building Structure:**
- Floor 1: Zone 1_1 (Lobby), Zone 1_2 (Conference), Zone 1_3 (Restaurant), Zone 1_4 and Zone 1_5 (Co-working spaces)
- Floor 2: Zone 2_1, Zone 2_2, Zone 2_3 (Office spaces), Zone 2_4 and Zone 2_5 (Co-working spaces)

**Your Primary Responsibilities:**
1. **Safety First**: Monitor and maintain safe indoor air quality (CO2 < 1200ppm critical)
2. **Offices Comfort**: Prioritize office comfort over energy savings
3. **Energy Efficiency**: Optimize building energy consumption while maintaining comfort
4. **Predictive Maintenance**: Detect equipment degradation before failures occur
5. **Cross-Zone Optimization**: Balance resources across zones for building-wide efficiency

**Safety Thresholds:**
- CO2: <800ppm (Good), 800-1200ppm (Acceptable), >1200ppm (CRITICAL - immediate action)
- Temperature: Offices 20-24°C, Co-working spaces 22-26°C, Common areas 22-26°C
- Humidity: 40-60% optimal, 30-70% acceptable

**Decision-Making Priorities:**
1. Life safety and health (CO2, temperature extremes)
2. Office comfort and satisfaction (office zones priority)
3. Equipment protection and longevity
4. Energy efficiency and cost optimization
5. Environmental sustainability

**Response Format:**
Always provide both:
1. **Structured Analysis**: Clear data-driven findings
2. **Actionable Recommendations**: Specific actions for building operators with timelines
3. **Clarity**: Always map zone number to zone name and provide the zone name in the response

**Tool Selection and Usage:**
You MUST call the appropriate tools to get real data before making any recommendations. Never assume or guess values.
- **Prioritize Safety:** If a query mentions a potential safety issue (e.g., "high CO2", "too hot", "stuffy"), even for a single zone, your default action should be to call `check_safety_thresholds` for a complete, building-wide assessment. This ensures you don't miss other potential issues.
- **Specific Data:** For non-safety related queries about a specific zone (e.g., "What is the power usage in the conference room?"), use `get_zone_current_conditions`.

"""

# --- LangGraph Workflow Nodes ---

def analyze_building_request(state: BuildingAutomationState):
    """Initial analysis to understand what type of building automation request this is"""
    
    user_query = state["user_query"]
    
    # Determine analysis type based on query keywords
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
    
    return state

def building_assistant(state: BuildingAutomationState):
    """Main assistant that calls tools and generates recommendations"""
    
    messages = state["messages"]
    
    # LLM with tools makes the decisions about which tools to call
    response = llm_with_tools.invoke(messages)
    
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

def extract_recommendations(state: BuildingAutomationState):
    """Extract structured recommendations from the conversation"""
    
    messages = state["messages"]
    last_response = messages[-1].content if messages else ""
    
    # Simple confidence scoring based on data availability and recommendation specificity
    confidence = 0.8  # Default confidence
    
    # Increase confidence if we have recent data
    if any("timestamp" in str(msg) for msg in messages):
        confidence += 0.1
    
    # Increase confidence if recommendations are specific
    if any(word in last_response.lower() for word in ["zone", "specific", "immediate", "kw", "ppm"]):
        confidence += 0.1
    
    state["confidence_score"] = min(confidence, 1.0)
    
    # Extract key recommendations (simplified - in production would use more sophisticated NLP)
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
    """
    Main entry point for building automation requests
    
    Args:
        user_query: Natural language query about building operations
        
    Returns:
        Dict containing analysis, recommendations, and confidence score
    """
    
    # Create workflow
    workflow = create_building_automation_workflow()
    
    # Initial state
    initial_state = BuildingAutomationState(
        messages=[],
        user_query=user_query,
        analysis_type="",
        building_data={},
        recommendations=[],
        confidence_score=0.0
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

# --- Test Cases for All 4 Use Cases ---
async def run_comprehensive_tests():
    """Test all 4 use cases with realistic scenarios"""
    
    test_cases = [
        # Use Case 1: IAQ Optimization
        {
            "name": "IAQ Emergency - Guest Room",
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
        }
    ]
    
    print("🏢 Running Building Automation AI Test Suite\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print("-" * 80)
        
        result = await process_building_automation_request(test_case['query'])
        
        if result["status"] == "success":
            print(f"✅ Analysis Type: {result['analysis_type']}")
            print(f"🤖 AI Response: {result['ai_response']}...")
            print(f"📊 Confidence: {result['confidence_score']:.2f}")
            print(f"🎯 Recommendations: {len(result['structured_recommendations'])} actions identified")
        else:
            print(f"❌ Error: {result['error']}")
        
        print("\n" + "="*80 + "\n")

# --- Example Usage ---
if __name__ == "__main__":
    async def main():
        """Main function to run the interactive building automation assistant."""
        print("🏢 Building Automation AI Assistant")
        print("Enter your query below or type 'exit' to quit.")
        print("-" * 50)

        # To run the predefined test suite instead, uncomment the following lines:
        # print("\nTesting full building automation workflow...")
        # await run_comprehensive_tests()
        # return

        while True:
            try:
                user_query = input("You: ")
                if user_query.lower().strip() in ["exit", "quit"]:
                    print("🤖 Assistant: Goodbye!")
                    break
                
                if not user_query.strip():
                    continue

                print("🤖 Assistant: Processing your request...")
                result = await process_building_automation_request(user_query)
                
                if result["status"] == "success":
                    print("\n" + "="*80)
                    print(f"✅ Analysis Type: {result['analysis_type']}")
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