from llama_cpp import Llama
import os

# Set verbose logging to see all details
os.environ["LLAMA_CPP_LOG_LEVEL"] = "INFO"

print("=== GPU Support Diagnostic Test ===")
print("This will check if your llama-cpp-python build actually supports GPU")
print()

# Model path
model_path = "./models/mistral-7b-instruct-v0.2.Q5_K_M.gguf"

print(f"Loading model: {model_path}")
print("Watch for these key messages:")
print("- 'llama_model_quantize_internal: applying GPU layers'")
print("- 'llama_backend_init: found CUDA device'")
print("- 'ggml_cuda_assign_buffers: allocating memory on GPU'")
print("- 'ggml_backend_cuda not found' (this would indicate NO GPU support)")
print()

try:
    print("Initializing Llama with n_gpu_layers=20...")
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=20,  # Force 20 layers to GPU
        verbose=True
    )
    
    print("\n✅ Model loaded successfully!")
    print("Check the logs above for GPU-related messages.")
    
    # Test a simple prompt
    print("\nTesting with a simple prompt...")
    result = llm("Hello", max_tokens=10)
    
    if hasattr(result, 'choices') and result.choices:
        output = result.choices[0].text
    elif hasattr(result, 'text'):
        output = result.text
    elif isinstance(result, dict) and 'choices' in result:
        output = result['choices'][0]['text']
    else:
        output = str(result)
    
    print(f"Response: {output}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Diagnostic Complete ===")
print("If you saw 'ggml_backend_cuda not found' or no GPU layer messages,")
print("then your llama-cpp-python build does NOT support GPU.") 