import requests
import json

def test_resume_upload():
    print("=== Testing Resume Upload with LLM Prompt Logging ===")
    
    # Backend URL
    backend_url = "http://localhost:8000"
    
    # Test if backend is running
    try:
        response = requests.get(f"{backend_url}/")
        print(f"✅ Backend is running: {response.json()}")
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return
    
    # Create a simple test resume text
    test_resume_text = """
    JOHN DOE
    Software Engineer
    john.doe@email.com
    (555) 123-4567
    San Francisco, CA
    
    SUMMARY
    Experienced software engineer with 5+ years in full-stack development, specializing in Python, JavaScript, and cloud technologies.
    
    WORK EXPERIENCE
    Senior Software Engineer | TechCorp Inc. | 2021-Present
    - Led development of microservices architecture serving 1M+ users
    - Implemented CI/CD pipelines reducing deployment time by 60%
    - Mentored 3 junior developers and conducted code reviews
    
    Software Engineer | StartupXYZ | 2019-2021
    - Built RESTful APIs using Python Flask and Django
    - Developed frontend components with React and TypeScript
    - Collaborated with product team to deliver features on time
    
    EDUCATION
    Bachelor of Science in Computer Science | University of California | 2019
    
    SKILLS
    Programming: Python, JavaScript, TypeScript, Java, SQL
    Frameworks: React, Django, Flask, Node.js, Express
    Cloud: AWS, Docker, Kubernetes, CI/CD
    Tools: Git, VS Code, Jira, Postman
    
    LANGUAGES
    English (Native), Spanish (Conversational)
    
    CERTIFICATIONS
    AWS Certified Developer Associate
    Google Cloud Professional Developer
    """
    
    print(f"\n📄 Test Resume Content:")
    print("="*50)
    print(test_resume_text)
    print("="*50)
    
    # Create a test file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_resume_text)
        temp_file_path = f.name
    
    try:
        print(f"\n📤 Uploading resume file: {temp_file_path}")
        
        # Upload the file
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('test_resume.txt', f, 'text/plain')}
            
            print("🚀 Sending POST request to /upload_resume_llm...")
            response = requests.post(f"{backend_url}/upload_resume_llm", files=files)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success! Response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception during upload: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
    
    print("\n🔍 Check the backend logs above to see the LLM prompt!")

if __name__ == "__main__":
    test_resume_upload() 