#!/usr/bin/env python3
# test_finetuned_model.py - Quick validation of PEFT fine-tuned model

import asyncio
from agents import process_building_automation_request

async def test_building_scenarios():
    """Test the fine-tuned model with building automation scenarios"""
    
    test_cases = [
        "Zone 2_3 (Office space) has CO2 at 1180 ppm and temperature at 26 degrees C. What should I do?",
        "It's 2 PM and we've used 2100 kWh out of 3564 kWh daily target. Are we on track?",
        "Conference room is empty but using high energy, while the lobby needs more cooling. How do we optimize?"
    ]
    
    print("Testing Fine-tuned Building Automation Model")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case}")
        print("-" * 40)
        
        result = await process_building_automation_request(test_case)
        
        if result["status"] == "success":
            print(f"Model: {result['model_used']}")
            print(f"Confidence: {result['confidence_score']:.2f}")
            print(f"Response: {result['ai_response'][:200]}...")
        else:
            print(f"Error: {result['error']}")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_building_scenarios())
