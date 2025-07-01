import sqlite3

def list_profile_fields():
    db_path = "job_automation.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get column names
        cursor.execute("PRAGMA table_info(profiles)")
        columns = cursor.fetchall()
        
        print("=== PROFILE TABLE FIELDS ===")
        print(f"Total fields: {len(columns)}")
        print()
        
        for i, col in enumerate(columns, 1):
            field_name = col[1]
            field_type = col[2]
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            default = col[4]
            primary_key = "PRIMARY KEY" if col[5] == 1 else ""
            
            print(f"{i:2d}. {field_name:<20} ({field_type:<10}) {nullable} {primary_key}")
            if default:
                print(f"     Default: {default}")
        
        print()
        print("=== FIELD CATEGORIES ===")
        
        # Categorize fields
        basic_fields = ['id', 'user_id', 'title', 'full_name', 'email', 'phone']
        location_fields = ['location', 'address', 'city', 'state', 'zip_code', 'country']
        personal_fields = ['citizenship', 'gender', 'image_url']
        json_fields = ['skills', 'languages', 'work_experience', 'education', 'job_preferences', 'achievements', 'certificates']
        timestamp_fields = ['created_at', 'updated_at']
        
        print(f"Basic Info ({len(basic_fields)}): {', '.join(basic_fields)}")
        print(f"Location ({len(location_fields)}): {', '.join(location_fields)}")
        print(f"Personal ({len(personal_fields)}): {', '.join(personal_fields)}")
        print(f"JSON Data ({len(json_fields)}): {', '.join(json_fields)}")
        print(f"Timestamps ({len(timestamp_fields)}): {', '.join(timestamp_fields)}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_profile_fields() 