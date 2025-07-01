import sqlite3
import os

def check_database():
    db_path = "job_automation.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist!")
        return
    
    print(f"Database file {db_path} exists!")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables in database: {tables}")
        
        # Check jobs table structure if it exists
        if ('jobs',) in tables:
            cursor.execute("PRAGMA table_info(jobs)")
            columns = cursor.fetchall()
            print("\nJobs table columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        
        # Check users table structure if it exists
        if ('users',) in tables:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            print("\nUsers table columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        
        # Check profiles table structure if it exists
        if ('profiles',) in tables:
            cursor.execute("PRAGMA table_info(profiles)")
            columns = cursor.fetchall()
            print("\nProfiles table columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database() 