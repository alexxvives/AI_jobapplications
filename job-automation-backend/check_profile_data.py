import sqlite3
import json
from pprint import pprint

def check_profile_data():
    db_path = "job_automation.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all profiles
        cursor.execute("SELECT * FROM profiles")
        profiles = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(profiles)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Total profiles in database: {len(profiles)}")
        print(f"Profile table columns: {columns}")
        print("\n" + "="*50)
        
        for i, profile in enumerate(profiles):
            print(f"\nProfile {i+1}:")
            profile_dict = dict(zip(columns, profile))
            
            # Print basic info
            print(f"  ID: {profile_dict.get('id')}")
            print(f"  User ID: {profile_dict.get('user_id')}")
            print(f"  Title: {profile_dict.get('title')}")
            print(f"  Full Name: {profile_dict.get('full_name')}")
            print(f"  Email: {profile_dict.get('email')}")
            print(f"  Phone: {profile_dict.get('phone')}")
            print(f"  Location: {profile_dict.get('location')}")
            print(f"  Address: {profile_dict.get('address')}")
            print(f"  City: {profile_dict.get('city')}")
            print(f"  State: {profile_dict.get('state')}")
            print(f"  Zip Code: {profile_dict.get('zip_code')}")
            print(f"  Country: {profile_dict.get('country')}")
            print(f"  Citizenship: {profile_dict.get('citizenship')}")
            print(f"  Gender: {profile_dict.get('gender')}")
            print(f"  Image URL: {profile_dict.get('image_url')}")
            
            # Check JSON fields
            print(f"  Skills: {profile_dict.get('skills')}")
            print(f"  Languages: {profile_dict.get('languages')}")
            print(f"  Work Experience: {profile_dict.get('work_experience')}")
            print(f"  Education: {profile_dict.get('education')}")
            print(f"  Job Preferences: {profile_dict.get('job_preferences')}")
            print(f"  Achievements: {profile_dict.get('achievements')}")
            print(f"  Certificates: {profile_dict.get('certificates')}")
            
            print(f"  Created At: {profile_dict.get('created_at')}")
            print(f"  Updated At: {profile_dict.get('updated_at')}")
            
            # Try to parse JSON fields
            try:
                if profile_dict.get('skills'):
                    skills = json.loads(profile_dict['skills'])
                    print(f"  Parsed Skills: {len(skills) if isinstance(skills, list) else 'Not a list'}")
                
                if profile_dict.get('languages'):
                    languages = json.loads(profile_dict['languages'])
                    print(f"  Parsed Languages: {len(languages) if isinstance(languages, list) else 'Not a list'}")
                
                if profile_dict.get('work_experience'):
                    work_exp = json.loads(profile_dict['work_experience'])
                    print(f"  Parsed Work Experience: {len(work_exp) if isinstance(work_exp, list) else 'Not a list'}")
                
                if profile_dict.get('education'):
                    education = json.loads(profile_dict['education'])
                    print(f"  Parsed Education: {len(education) if isinstance(education, list) else 'Not a list'}")
                    
            except json.JSONDecodeError as e:
                print(f"  JSON Parse Error: {e}")
            
            print("-" * 30)
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking profile data: {e}")

if __name__ == "__main__":
    check_profile_data() 