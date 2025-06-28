import time
import json
from llama_cpp import Llama

def test_resume_processing():
    # Read the resume from file
    with open("test_resume.txt", "r", encoding="utf-8") as f:
        resume_text = f.read()
    
    # Create a much shorter, more focused prompt
    prompt = f"""Extract from this resume and return as JSON:
- Name
- Email  
- Phone
- Location
- Work Experience (title, company, dates)
- Education (degree, school, year)
- Skills
- Languages

Resume: {resume_text[:2000]}
JSON:"""
    
    print("🤖 Loading Mistral model...")
    model_path = "./models/mistral-7b-instruct-v0.2.Q5_K_M.gguf"
    
    # Load the model with smaller context
    llm = Llama(
        model_path=model_path, 
        n_gpu_layers=0,  # CPU only
        n_ctx=2048,  # Smaller context window
        verbose=False
    )
    
    print("🚀 Starting LLM processing...")
    print(f"📊 Prompt length: {len(prompt)} characters")
    start_time = time.time()
    
    try:
        result = llm(prompt, max_tokens=1500, stop=["\nJSON:"])
        
        # Handle the response
        if hasattr(result, 'choices') and result.choices:
            output = result.choices[0].text
        elif hasattr(result, 'text'):
            output = result.text
        elif isinstance(result, dict) and 'choices' in result:
            output = result['choices'][0]['text']
        else:
            output = str(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n⏱️  Processing completed in {processing_time:.2f} seconds")
        print(f"📊 Output length: {len(output)} characters")
        
        # Try to extract JSON from output
        try:
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                profile_json = json.loads(output[json_start:json_end])
                print("\n" + "="*80)
                print("🎯 EXTRACTED JSON:")
                print("="*80)
                print(json.dumps(profile_json, indent=2))
                print("="*80)
            else:
                print("\n❌ LLM did not return valid JSON format.")
                print("Raw output:")
                print(output)
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON parsing failed: {e}")
            print("Raw output:")
            print(output)
            
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"\n❌ Error during processing: {e}")
        print(f"⏱️  Failed after {processing_time:.2f} seconds")

if __name__ == "__main__":
    test_resume_processing() 