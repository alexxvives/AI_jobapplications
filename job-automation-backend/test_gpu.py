import os
import time
from llama_cpp import Llama
import torch

# Set environment variable to reduce noise
os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"

def test_gpu_usage():
    print("=== GPU Usage Test for Mistral Model ===")
    
    # Check CUDA availability
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    
    # Model path - updated to use Mistral
    model_path = "./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    print(f"\nLoading model from: {model_path}")
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"ERROR: Model file not found at {model_path}")
        return
    
    try:
        # Initialize model with GPU support
        print("\nInitializing Mistral model...")
        start_time = time.time()
        
        if torch.cuda.is_available():
            n_gpu_layers = -1  # Use all layers on GPU
            print("Using GPU acceleration with n_gpu_layers=-1")
        else:
            n_gpu_layers = 0  # Use CPU only
            print("Using CPU only with n_gpu_layers=0")
        
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=4096,
            verbose=False
        )
        
        init_time = time.time() - start_time
        print(f"Model loaded in {init_time:.2f} seconds")
        
        # Test prompt
        test_prompt = "Write a short summary of what machine learning is in 2-3 sentences."
        print(f"\nTesting with prompt: '{test_prompt}'")
        
        # Check GPU memory before inference
        if torch.cuda.is_available():
            print(f"GPU memory before inference: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
        
        # Run inference
        start_time = time.time()
        result = llm(test_prompt, max_tokens=100, stop=["\n\n"])
        inference_time = time.time() - start_time
        
        # Check GPU memory after inference
        if torch.cuda.is_available():
            print(f"GPU memory after inference: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
            print(f"GPU memory peak: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")
        
        print(f"\nInference completed in {inference_time:.2f} seconds")
        
        # Extract response
        if hasattr(result, 'choices') and result.choices:
            output = result.choices[0].text
        elif hasattr(result, 'text'):
            output = result.text
        elif isinstance(result, dict) and 'choices' in result:
            output = result['choices'][0]['text']
        else:
            output = str(result)
        
        print(f"\nModel response: {output}")
        
        # Performance analysis
        if inference_time < 1.0:
            print("\n✅ FAST inference - likely using GPU acceleration")
        else:
            print("\n⚠️  SLOW inference - likely using CPU only")
            
        print(f"\nTokens per second: {len(output.split()) / inference_time:.1f}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gpu_usage() 