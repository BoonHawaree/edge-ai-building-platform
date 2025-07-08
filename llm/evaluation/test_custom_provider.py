#!/usr/bin/env python3
"""
Quick test script to verify custom_provider.py works correctly
before running the full promptfoo evaluation.

Place this file in: edge-ai-building-platform/llm/evaluation/test_custom_provider.py
"""

import sys
from pathlib import Path

# Add the evaluation directory to Python path
evaluation_dir = Path(__file__).parent
sys.path.append(str(evaluation_dir))

# Import the custom provider
from custom_provider import call_agent

def test_baseline_model():
    """Test the baseline model with a sample query"""
    print("=" * 60)
    print("🧪 TESTING BASELINE MODEL")
    print("=" * 60)
    
    test_query = "Zone 2_3 has CO2 at 1350ppm, temperature 26.5°C, with 22 people. What should I do immediately?"
    
    print(f"📝 Test Query: {test_query}")
    print("\n🔄 Calling baseline model...")
    
    try:
        result = call_agent(
            test_query,
            {"config": {"model_type": "baseline"}},
            {}
        )
        
        print(f"\n✅ SUCCESS!")
        print(f"📤 Model Output: {result['output'][:200]}...")
        print(f"📊 Metadata Keys: {list(result.get('meta', {}).keys())}")
        
        if 'meta' in result and 'latency_ms' in result['meta']:
            print(f"⏱️  Latency: {result['meta']['latency_ms']:.2f}ms")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

def test_finetuned_model():
    """Test the fine-tuned model with a sample query"""
    print("\n" + "=" * 60)
    print("🧪 TESTING FINE-TUNED MODEL")
    print("=" * 60)
    
    test_query = "Zone 2_3 has CO2 at 1350ppm, temperature 26.5°C, with 22 people. What should I do immediately?"
    
    print(f"📝 Test Query: {test_query}")
    print("\n🔄 Calling fine-tuned model...")
    print("⚠️  Note: This requires your PEFT server to be running on localhost:8080")
    
    try:
        result = call_agent(
            test_query,
            {"config": {"model_type": "finetuned"}},
            {}
        )
        
        print(f"\n✅ SUCCESS!")
        print(f"📤 Model Output: {result['output'][:200]}...")
        print(f"📊 Metadata Keys: {list(result.get('meta', {}).keys())}")
        
        if 'meta' in result and 'latency_ms' in result['meta']:
            print(f"⏱️  Latency: {result['meta']['latency_ms']:.2f}ms")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("💡 Make sure your PEFT server is running: python finetuning/run_peft_server.py")
        return False

def test_both_models():
    """Test both models and compare outputs"""
    print("🚀 CUSTOM PROVIDER QUICK TEST")
    print("This will test if your promptfoo setup is working correctly.\n")
    
    # Test baseline first (should always work if Ollama is running)
    baseline_success = test_baseline_model()
    
    # Test fine-tuned model (might fail if server not running)
    finetuned_success = test_finetuned_model()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Baseline Model: {'PASS' if baseline_success else 'FAIL'}")
    print(f"✅ Fine-tuned Model: {'PASS' if finetuned_success else 'FAIL'}")
    
    if baseline_success and finetuned_success:
        print("\n🎉 Both models working! You can now run the full promptfoo evaluation.")
        print("💡 Run: npx promptfoo eval -c promptfooconfig.yaml")
    elif baseline_success:
        print("\n⚠️  Baseline working, but fine-tuned model failed.")
        print("💡 Start your PEFT server first: python finetuning/run_peft_server.py")
    else:
        print("\n❌ Both models failed. Check your setup:")
        print("💡 1. Is your building data API running? (localhost:8000)")
        print("💡 2. Is Ollama running with qwen3:4b-q8_0?")
        print("💡 3. Are you in the correct directory?")

if __name__ == "__main__":
    test_both_models()