import time
from llama_cpp import Llama

def simple_test():
    print("🤖 Loading Mistral model...")
    model_path = "./models/mistral-7b-instruct-v0.2.Q5_K_M.gguf"
    
    try:
        # Load the model with minimal settings
        llm = Llama(
            model_path=model_path, 
            n_gpu_layers=0,  # CPU only
            n_ctx=2048,  # Smaller context
            verbose=True  # Enable verbose to see what's happening
        )
        
        print("🚀 Testing with simple prompt...")
        start_time = time.time()
        
        # Very simple prompt
        simple_prompt = "What is 2+2? Answer in one word:"
        
        result = llm(simple_prompt, max_tokens=10, stop=["\n"])
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"⏱️  Simple test completed in {processing_time:.2f} seconds")
        print(f"📝 Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_test() 