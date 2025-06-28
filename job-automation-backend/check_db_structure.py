#!/usr/bin/env python3
"""
Script to check the database structure and see if the summary field has been deleted.
"""

import sqlite3
import os

def check_database_structure():
    """Check the current database structure."""
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
        
        print("=== Database Structure ===")
        print(f"Database: {db_path}")
        print(f"Table: jobs")
        print("\nColumns:")
        for col in columns:
            cid, name, type_name, not_null, default_val, pk = col
            print(f"  {cid}: {name} ({type_name}) {'NOT NULL' if not_null else 'NULL'} {'PRIMARY KEY' if pk else ''}")
        
        # Check if summary column exists
        summary_exists = any(col[1] == 'summary' for col in columns)
        print(f"\nSummary column exists: {summary_exists}")
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM jobs")
        row_count = cursor.fetchone()[0]
        print(f"Total jobs in database: {row_count}")
        
        # Sample some jobs to see the data structure
        cursor.execute("SELECT * FROM jobs LIMIT 3")
        sample_jobs = cursor.fetchall()
        
        if sample_jobs:
            print(f"\n=== Sample Jobs (first 3) ===")
            for i, job in enumerate(sample_jobs, 1):
                print(f"\nJob {i}:")
                for j, col in enumerate(columns):
                    print(f"  {col[1]}: {job[j]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database_structure() 