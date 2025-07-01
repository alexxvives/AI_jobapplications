import sqlite3

def remove_location_column():
    """Remove the location column from the profiles table"""
    db_path = "job_automation.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if location column exists
        cursor.execute("PRAGMA table_info(profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'location' in columns:
            print("Removing location column from profiles table...")
            
            # Create a new table without the location column
            cursor.execute("""
                CREATE TABLE profiles_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR,
                    full_name VARCHAR,
                    email VARCHAR,
                    phone VARCHAR,
                    skills JSON,
                    languages JSON,
                    work_experience JSON,
                    education JSON,
                    created_at DATETIME,
                    updated_at DATETIME,
                    image_url VARCHAR,
                    address VARCHAR,
                    city VARCHAR,
                    state VARCHAR,
                    zip_code VARCHAR,
                    country VARCHAR,
                    citizenship VARCHAR,
                    gender VARCHAR,
                    job_preferences JSON,
                    achievements JSON,
                    certificates JSON,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Copy data from old table to new table (excluding location)
            cursor.execute("""
                INSERT INTO profiles_new (
                    id, user_id, title, full_name, email, phone, skills, languages,
                    work_experience, education, created_at, updated_at, image_url,
                    address, city, state, zip_code, country, citizenship, gender,
                    job_preferences, achievements, certificates
                )
                SELECT 
                    id, user_id, title, full_name, email, phone, skills, languages,
                    work_experience, education, created_at, updated_at, image_url,
                    address, city, state, zip_code, country, citizenship, gender,
                    job_preferences, achievements, certificates
                FROM profiles
            """)
            
            # Drop the old table
            cursor.execute("DROP TABLE profiles")
            
            # Rename the new table to the original name
            cursor.execute("ALTER TABLE profiles_new RENAME TO profiles")
            
            # Recreate indexes
            cursor.execute("CREATE INDEX ix_profiles_id ON profiles (id)")
            cursor.execute("CREATE INDEX ix_profiles_user_id ON profiles (user_id)")
            
            conn.commit()
            print("✅ Location column removed successfully!")
            
        else:
            print("Location column does not exist in profiles table.")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error removing location column: {e}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    remove_location_column() 