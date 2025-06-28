import os
import time
from llama_cpp import Llama
import torch

# Set environment variable to reduce noise
os.environ["LLAMA_CPP_LOG_LEVEL"] = "INFO"  # Change to INFO for more details

def test_gpu_usage_advanced():
    print("=== Advanced GPU Usage Test for Mistral Model ===")
    
    # Check CUDA availability
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"GPU {i} memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
    
    # Model path - updated to use Mistral
    model_path = "./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    print(f"\nLoading model from: {model_path}")
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"ERROR: Model file not found at {model_path}")
        return
    
    # Test different GPU configurations
    configs = [
        {"n_gpu_layers": -1, "name": "All layers on GPU"},
        {"n_gpu_layers": 32, "name": "32 layers on GPU"},
        {"n_gpu_layers": 16, "name": "16 layers on GPU"},
        {"n_gpu_layers": 8, "name": "8 layers on GPU"},
        {"n_gpu_layers": 0, "name": "CPU only"},
    ]
    
    for config in configs:
        print(f"\n{'='*50}")
        print(f"Testing: {config['name']} (n_gpu_layers={config['n_gpu_layers']})")
        print(f"{'='*50}")
        
        try:
            # Clear GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print(f"GPU memory before loading: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
            
            # Initialize model
            start_time = time.time()
            llm = Llama(
                model_path=model_path,
                n_gpu_layers=config['n_gpu_layers'],
                n_ctx=2048,  # Smaller context for faster testing
                verbose=True  # Enable verbose output
            )
            init_time = time.time() - start_time
            print(f"Model loaded in {init_time:.2f} seconds")
            
            # Check GPU memory after loading
            if torch.cuda.is_available():
                print(f"GPU memory after loading: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
            
            # Test prompt
            test_prompt = "Hello, how are you?"
            print(f"Testing with prompt: '{test_prompt}'")
            
            # Run inference
            start_time = time.time()
            result = llm(test_prompt, max_tokens=50, stop=["\n"])
            inference_time = time.time() - start_time
            
            # Check GPU memory after inference
            if torch.cuda.is_available():
                print(f"GPU memory after inference: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
                print(f"GPU memory peak: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")
            
            print(f"Inference completed in {inference_time:.2f} seconds")
            
            # Extract response
            if hasattr(result, 'choices') and result.choices:
                output = result.choices[0].text
            elif hasattr(result, 'text'):
                output = result.text
            elif isinstance(result, dict) and 'choices' in result:
                output = result['choices'][0]['text']
            else:
                output = str(result)
            
            print(f"Model response: {output}")
            
            # Performance analysis
            if inference_time < 0.5:
                print("✅ VERY FAST inference - likely using GPU acceleration")
            elif inference_time < 1.0:
                print("✅ FAST inference - likely using GPU acceleration")
            else:
                print("⚠️  SLOW inference - likely using CPU only")
                
            print(f"Tokens per second: {len(output.split()) / inference_time:.1f}")
            
            # Clean up
            del llm
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
        except Exception as e:
            print(f"Error with config {config['name']}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_gpu_usage_advanced() 