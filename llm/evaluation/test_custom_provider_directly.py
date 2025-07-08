import asyncio
import json
import time
import sys
import concurrent.futures
from pathlib import Path

# Add the parent directory (llm/) to the Python path
# This allows us to import the 'agents' module
sys.path.append(str(Path(__file__).parent.parent))

from agents import process_building_automation_request

def call_agent(prompt, options, context):
    """
    This function is called by promptfoo for each test case.
    It acts as a bridge to our LangGraph agent.
    """
    model_type = options.get('config', {}).get('model_type', 'baseline')
    
    # Debug: Print what we received (Windows-safe, no emojis)
    print("=== CUSTOM PROVIDER DEBUG ===")
    print(f"Received prompt: '{prompt}'")
    print(f"Model type: {model_type}")
    print(f"Context vars: {context.get('vars', {})}")
    
    # Check if prompt is the placeholder or actual query
    actual_query = prompt
    
    # If we got the placeholder, try to get the actual query from context
    if prompt == "{{prompt}}" or prompt == "{{query}}":
        if 'vars' in context and 'query' in context['vars']:
            actual_query = context['vars']['query']
            print(f"Using query from context: '{actual_query}'")
        else:
            print("ERROR: Received placeholder but no query in context!")
            return {
                'output': 'Error: No actual query provided',
                'meta': {'error': 'missing_query', 'model_type': model_type}
            }
    
    print(f"Final query to process: '{actual_query}'")
    print("=" * 40)

    # Measure latency
    start_time = time.time()
    
    # SIMPLIFIED APPROACH: Always use the ThreadPoolExecutor method
    # This avoids the event loop detection issues
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            print(f"Starting {model_type} model execution...")
            
            future = executor.submit(
                asyncio.run,
                process_building_automation_request(actual_query, model_type=model_type)
            )
            
            # Extended timeout for your slow agent
            # 600 seconds = 10 minutes should be enough
            print("Waiting for agent response (timeout: 600 seconds)...")
            result = future.result(timeout=600)
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Add latency and other metadata to the result
        result['latency_ms'] = latency_ms
        result['model_type'] = model_type
        
        # Windows-safe output (no emojis)
        print(f"SUCCESS: Model response generated in {latency_ms:.2f}ms ({latency_ms/1000:.1f} seconds)")
        print(f"Response preview: {result.get('ai_response', 'No response')[:150]}...")

        # The 'output' is the main AI response text
        # The 'meta' dictionary passes all other data to the assertion scripts
        return {
            'output': result.get('ai_response', 'Error: No response generated.'),
            'meta': result
        }
        
    except concurrent.futures.TimeoutError:
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        print(f"TIMEOUT: Agent took longer than 600 seconds ({latency_ms/1000:.1f} seconds elapsed)")
        
        return {
            'output': 'Error: Request timed out after 600 seconds. The building automation agent may be experiencing issues.',
            'meta': {
                'error': 'timeout',
                'model_type': model_type,
                'latency_ms': latency_ms,
                'status': 'timeout'
            }
        }
        
    except Exception as e:
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        print(f"ERROR during agent execution: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        return {
            'output': f'Error: {str(e)}',
            'meta': {
                'error': str(e),
                'model_type': model_type,
                'latency_ms': latency_ms,
                'status': 'error'
            }
        }