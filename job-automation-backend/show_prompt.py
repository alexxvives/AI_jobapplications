def show_llm_prompt(resume_text):
    """
    Show the exact prompt that would be sent to the LLM
    """
    prompt = f"""
Extract the following fields from this resume text and return as JSON:
- Name
- Email
- Phone
- Location
- Work Experience (list of jobs: title, company, start date, end date, description)
- Education (list: degree, school, year)
- Skills (list)
- Languages (list)
- Achievements (list)
- Certifications (list)

Resume text:
"""
    prompt += resume_text[:4000]  # Limit to 4000 chars for context window
    prompt += "\nJSON:"
    
    print("\n" + "="*80)
    print("🤖 EXACT PROMPT BEING SENT TO LLM:")
    print("="*80)
    print(prompt)
    print("="*80)
    print("🤖 END OF PROMPT")
    print("="*80)
    print(f"📊 Prompt length: {len(prompt)} characters")
    print(f"📄 Resume text length: {len(resume_text)} characters")
    if len(resume_text) > 4000:
        print(f"⚠️  Resume was truncated from {len(resume_text)} to 4000 characters")

if __name__ == "__main__":
    print("=== Resume Prompt Preview ===")
    print("Paste your resume content below (press Enter twice when done):")
    
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    
    resume_text = "\n".join(lines)
    
    if resume_text.strip():
        show_llm_prompt(resume_text)
    else:
        print("No resume content provided.") 