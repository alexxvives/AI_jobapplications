import time
from llama_cpp import Llama
import os

# Set logging to minimal to reduce noise
os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"

def test_cpu_performance():
    print("=== CPU Performance Test ===")
    print("Testing if CPU inference is fast enough for practical use")
    print()
    
    # Model path
    model_path = "./models/mistral-7b-instruct-v0.2.Q5_K_M.gguf"
    print(f"Loading model: {model_path}")
    
    try:
        # Initialize model with CPU only
        print("Initializing model with CPU only (n_gpu_layers=0)...")
        start_time = time.time()
        
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=0,  # CPU only
            n_ctx=2048,
            verbose=False
        )
        
        init_time = time.time() - start_time
        print(f"✅ Model loaded in {init_time:.2f} seconds")
        
        # Test prompts of different lengths
        test_prompts = [
            ("Short prompt", "Hello, how are you?"),
            ("Medium prompt", "Write a brief summary of machine learning in 2-3 sentences."),
            ("Long prompt", "Explain the differences between supervised learning, unsupervised learning, and reinforcement learning. Provide examples of each."),
            ("Very long prompt", "Write a comprehensive guide on how to build a machine learning model from scratch, including data preprocessing, model selection, training, and evaluation. Include code examples and best practices.")
        ]
        
        print("\n" + "="*60)
        print("PERFORMANCE TEST RESULTS")
        print("="*60)
        
        total_tokens = 0
        total_time = 0
        
        for prompt_name, prompt_text in test_prompts:
            print(f"\n📝 Testing: {prompt_name}")
            print(f"Prompt: '{prompt_text[:50]}{'...' if len(prompt_text) > 50 else ''}'")
            
            # Time the inference
            start_time = time.time()
            result = llm(prompt_text, max_tokens=200, stop=["\n\n"])
            inference_time = time.time() - start_time
            
            # Extract response
            if hasattr(result, 'choices') and result.choices:
                output = result.choices[0].text
            elif hasattr(result, 'text'):
                output = result.text
            elif isinstance(result, dict) and 'choices' in result:
                output = result['choices'][0]['text']
            else:
                output = str(result)
            
            # Count tokens (rough estimate)
            input_tokens = len(prompt_text.split())
            output_tokens = len(output.split())
            total_tokens_for_prompt = input_tokens + output_tokens
            
            # Calculate metrics
            tokens_per_second = total_tokens_for_prompt / inference_time
            
            print(f"⏱️  Time: {inference_time:.2f} seconds")
            print(f"📊 Tokens: {total_tokens_for_prompt} (input: {input_tokens}, output: {output_tokens})")
            print(f"🚀 Speed: {tokens_per_second:.1f} tokens/second")
            print(f"📝 Response: {output[:100]}{'...' if len(output) > 100 else ''}")
            
            total_tokens += total_tokens_for_prompt
            total_time += inference_time
        
        # Overall performance
        print("\n" + "="*60)
        print("OVERALL PERFORMANCE SUMMARY")
        print("="*60)
        print(f"⏱️  Total time: {total_time:.2f} seconds")
        print(f"📊 Total tokens: {total_tokens}")
        print(f"🚀 Average speed: {total_tokens/total_time:.1f} tokens/second")
        
        # Performance assessment
        print("\n" + "="*60)
        print("PERFORMANCE ASSESSMENT")
        print("="*60)
        
        avg_speed = total_tokens/total_time
        
        if avg_speed >= 10:
            print("✅ EXCELLENT - CPU performance is very good!")
            print("   This should work well for most use cases.")
        elif avg_speed >= 5:
            print("✅ GOOD - CPU performance is acceptable.")
            print("   This should work for most use cases, though GPU would be faster.")
        elif avg_speed >= 2:
            print("⚠️  SLOW - CPU performance is quite slow.")
            print("   Consider GPU acceleration for better experience.")
        else:
            print("❌ VERY SLOW - CPU performance is too slow for practical use.")
            print("   GPU acceleration is highly recommended.")
        
        print(f"\n💡 For reference: GPU typically achieves 20-100+ tokens/second")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cpu_performance() 