import asyncio
import time
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import numpy as np

# --- Configuration ---
# The name of the Qwen model you have running in Ollama
MODEL_NAME = "qwen3:4b-q8_0" 
# Number of concurrent requests to send to the model
NUM_REQUESTS = 1
# The prompt to use for inference
PROMPT_TEXT = "Tell me a short story about a robot exploring a new planet in exactly 100 words."

async def run_inference(llm: ChatOllama, prompt: ChatPromptTemplate):
    """
    Runs a single inference request and returns performance metrics.

    Args:
        llm: The ChatOllama instance.
        prompt: The prompt template to send to the model.

    Returns:
        A dictionary containing latency, output tokens, throughput, and the response text.
    """
    start_time = time.perf_counter()

    # Use 'agenerate' to get detailed output, including token usage
    result = await llm.agenerate([prompt.format_messages()])
    
    end_time = time.perf_counter()
    latency = end_time - start_time

    # Extract token usage and output text from the result
    generation = result.generations[0][0]
    output_text = generation.text
    token_usage = result.llm_output.get("token_usage", {})
    output_tokens = token_usage.get("completion_tokens", 0)
    
    # Fallback for calculating tokens if not in the response metadata
    if output_tokens == 0 and output_text:
        output_tokens = llm.get_num_tokens(output_text)

    throughput = (output_tokens / latency) if latency > 0 else 0
        
    return {
        "latency": latency,
        "output_tokens": output_tokens,
        "throughput_tps": throughput,
        "output_text": output_text
    }

async def main():
    """
    Main function to initialize the model and run the benchmark.
    """
    print(f"Initializing model: {MODEL_NAME}...")
    try:
        llm = ChatOllama(model=MODEL_NAME, temperature=0.1)
    except Exception as e:
        print(f"❌ Failed to initialize Ollama model. Ensure Ollama is running and the model '{MODEL_NAME}' is available.")
        print(f"Error: {e}")
        return

    prompt = ChatPromptTemplate.from_template(PROMPT_TEXT)
    
    print(f"🚀 Running benchmark with {NUM_REQUESTS} concurrent requests...")
    
    # Run all inference tasks concurrently
    tasks = [run_inference(llm, prompt) for _ in range(NUM_REQUESTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out any exceptions that may have occurred
    successful_results = [r for r in results if not isinstance(r, Exception)]
    failed_count = len(results) - len(successful_results)

    if not successful_results:
        print("\n❌ All requests failed. Cannot calculate statistics.")
        print("Errors encountered:", [str(e) for e in results if isinstance(e, Exception)])
        return

    latencies = [r["latency"] for r in successful_results]
    throughputs = [r["throughput_tps"] for r in successful_results]
    total_tokens = sum(r["output_tokens"] for r in successful_results)
    
    print("\n" + "="*50)
    print("📊 Benchmark Results")
    print("="*50)
    print(f"Total Successful Requests: {len(successful_results)}")
    if failed_count > 0:
        print(f"Total Failed Requests: {failed_count}")
    print(f"Total Output Tokens Generated: {total_tokens}")
    
    print("\nLatency (seconds):")
    print(f"  - Average: {np.mean(latencies):.4f}")
    print(f"  - Median:  {np.median(latencies):.4f}")
    print(f"  - Min:     {np.min(latencies):.4f}")
    print(f"  - Max:     {np.max(latencies):.4f}")
    print(f"  - Std Dev: {np.std(latencies):.4f}")

    print("\nThroughput (tokens/sec):")
    print(f"  - Average: {np.mean(throughputs):.4f}")
    print(f"  - Median:  {np.median(throughputs):.4f}")
    print(f"  - Min:     {np.min(throughputs):.4f}")
    print(f"  - Max:     {np.max(throughputs):.4f}")
    print(f"  - Std Dev: {np.std(throughputs):.4f}")
    
    print("\n" + "="*50)
    print("📝 Sample Response")
    print("="*50)
    print(successful_results[0]['output_text'])
    print("="*50)

if __name__ == "__main__":
    # Handle environments where an asyncio event loop is already running
    try:
        if asyncio.get_event_loop().is_running():
            import nest_asyncio
            nest_asyncio.apply()
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBenchmark cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}") 