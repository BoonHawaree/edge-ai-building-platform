#!/usr/bin/env python3
"""
Minimal test of the agents.py workflow to isolate issues
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to import agents
sys.path.append(str(Path(__file__).parent.parent))

async def test_minimal_agent():
    """Test the agent workflow with minimal setup"""
    
    print("🧪 Testing minimal agent workflow...")
    print("=" * 50)
    
    try:
        # Import agents
        from agents import process_building_automation_request
        
        print("✅ Successfully imported agents module")
        
        # Test query
        test_query = "Zone 2_3 has CO2 at 1350ppm. What should I do immediately?"
        print(f"📝 Test query: {test_query}")
        
        print("\n🔄 Calling agent with baseline model...")
        
        # Add timeout to prevent hanging
        result = await asyncio.wait_for(
            process_building_automation_request(test_query, model_type="baseline"),
            timeout=300.0  # 30 second timeout
        )
        
        print("\n✅ Agent completed successfully!")
        print(f"📤 AI Response: {result.get('ai_response', 'No response')[:200]}...")
        print(f"📊 Analysis Type: {result.get('analysis_type', 'Unknown')}")
        print(f"⏱️  Status: {result.get('status', 'Unknown')}")
        
        return True
        
    except asyncio.TimeoutError:
        print("\n⏰ TIMEOUT: Agent took longer than 30 seconds")
        print("💡 This suggests the building API is slow or hanging")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"📍 Error type: {type(e).__name__}")
        return False

async def test_ollama_directly():
    """Test if Ollama is responding quickly"""
    
    print("\n🦙 Testing Ollama directly...")
    print("=" * 30)
    
    try:
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(
            model="qwen3:4b-q8_0",
            temperature=0.1,
        )
        
        # Simple test without tools
        response = await asyncio.wait_for(
            llm.ainvoke("What is 2+2?"),
            timeout=300.0
        )
        
        print("✅ Ollama responding correctly")
        print(f"📤 Response: {response.content[:100]}...")
        return True
        
    except asyncio.TimeoutError:
        print("⏰ Ollama is slow or hanging")
        return False
        
    except Exception as e:
        print(f"❌ Ollama error: {str(e)}")
        return False

async def main():
    """Run all tests"""
    
    print("🚀 DEBUGGING LANGGRAPH WORKFLOW")
    print("=" * 60)
    
    # Test 1: Ollama
    ollama_ok = await test_ollama_directly()
    
    # Test 2: Full agent
    agent_ok = await test_minimal_agent()
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY:")
    print(f"🦙 Ollama: {'✅ PASS' if ollama_ok else '❌ FAIL'}")
    print(f"🤖 Agent: {'✅ PASS' if agent_ok else '❌ FAIL'}")
    
    if ollama_ok and agent_ok:
        print("\n🎉 Everything working! The issue might be with Promptfoo integration.")
    elif ollama_ok and not agent_ok:
        print("\n⚠️  Ollama works but agent fails. Check your building API.")
    else:
        print("\n❌ Basic Ollama failing. Check your Ollama installation.")

if __name__ == "__main__":
    asyncio.run(main())