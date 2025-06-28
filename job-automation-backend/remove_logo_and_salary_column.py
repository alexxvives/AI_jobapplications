#!/usr/bin/env python3
"""
Migration script to remove the logo and salary columns from the jobs table.
"""

import sqlite3
import os

def remove_logo_and_salary_column():
    """Remove the logo and salary columns from the jobs table."""
    db_path = "job_automation.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        logo_exists = any(col[1] == 'logo' for col in columns)
        salary_exists = any(col[1] == 'salary' for col in columns)
        
        if not logo_exists and not salary_exists:
            print("Logo and salary columns do not exist. Nothing to do.")
            return
        
        print("Logo and/or salary columns found. Removing them...")
        
        # Create a new table without the logo and salary columns
        cursor.execute("""
            CREATE TABLE jobs_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                company VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                description TEXT,
                link VARCHAR(500) NOT NULL UNIQUE,
                source VARCHAR(50),
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Copy data from old table to new table (excluding logo and salary columns)
        cursor.execute("""
            INSERT INTO jobs_new (id, title, company, location, description, link, source, fetched_at)
            SELECT id, title, company, location, description, link, source, fetched_at
            FROM jobs
        """)
        
        # Drop the old table
        cursor.execute("DROP TABLE jobs")
        
        # Rename the new table to the original name
        cursor.execute("ALTER TABLE jobs_new RENAME TO jobs")
        
        # Commit the changes
        conn.commit()
        
        print("Successfully removed logo and salary columns!")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        logo_exists = any(col[1] == 'logo' for col in columns)
        salary_exists = any(col[1] == 'salary' for col in columns)
        print(f"Logo column still exists: {logo_exists}")
        print(f"Salary column still exists: {salary_exists}")
        
        # Show new structure
        print("\nNew table structure:")
        for col in columns:
            cid, name, type_name, not_null, default_val, pk = col
            print(f"  {cid}: {name} ({type_name}) {'NOT NULL' if not_null else 'NULL'} {'PRIMARY KEY' if pk else ''}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error removing logo and salary columns: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    remove_logo_and_salary_column() 