#!/usr/bin/env python3
"""
Migration script to remove the summary column from the jobs table.
"""

import sqlite3
import os

def remove_summary_column():
    """Remove the summary column from the jobs table."""
    db_path = "job_automation.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if summary column exists
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        summary_exists = any(col[1] == 'summary' for col in columns)
        
        if not summary_exists:
            print("Summary column does not exist. Nothing to do.")
            return
        
        print("Summary column found. Removing it...")
        
        # Create a new table without the summary column
        cursor.execute("""
            CREATE TABLE jobs_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                company VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                salary VARCHAR(255),
                description TEXT,
                link VARCHAR(500) NOT NULL UNIQUE,
                logo VARCHAR(500),
                source VARCHAR(50),
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Copy data from old table to new table (excluding summary column)
        cursor.execute("""
            INSERT INTO jobs_new (id, title, company, location, salary, description, link, logo, source, fetched_at)
            SELECT id, title, company, location, salary, description, link, logo, source, fetched_at
            FROM jobs
        """)
        
        # Drop the old table
        cursor.execute("DROP TABLE jobs")
        
        # Rename the new table to the original name
        cursor.execute("ALTER TABLE jobs_new RENAME TO jobs")
        
        # Commit the changes
        conn.commit()
        
        print("Successfully removed summary column!")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        summary_exists = any(col[1] == 'summary' for col in columns)
        print(f"Summary column still exists: {summary_exists}")
        
        # Show new structure
        print("\nNew table structure:")
        for col in columns:
            cid, name, type_name, not_null, default_val, pk = col
            print(f"  {cid}: {name} ({type_name}) {'NOT NULL' if not_null else 'NULL'} {'PRIMARY KEY' if pk else ''}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error removing summary column: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    remove_summary_column() 