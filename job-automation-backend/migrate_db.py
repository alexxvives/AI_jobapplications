import sqlite3

def migrate_database():
    """Add new columns to existing database"""
    conn = sqlite3.connect('job_automation.db')
    cursor = conn.cursor()
    
    try:
        # Add salary column if it doesn't exist
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'salary' not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN salary TEXT")
            print("Added salary column")
        
        if 'description' not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN description TEXT")
            print("Added description column")
        
        # Update source based on URL patterns, only if source is NULL or empty
        source_patterns = [
            ('LinkedIn', '%linkedin.com%'),
            ('Indeed', '%indeed.com%'),
            ('Glassdoor', '%glassdoor.com%'),
            ('ZipRecruiter', '%ziprecruiter.com%'),
            ('Dice', '%dice.com%'),
            ('Lever', '%lever.co%'),
            ('SimplyHired', '%simplyhired.com%'),
            ('Greenhouse', '%greenhouse.io%'),
            ('Ashby', '%ashbyhq.com%'),
        ]
        
        for source, pattern in source_patterns:
            cursor.execute(
                """
                UPDATE jobs
                SET source = ?
                WHERE (source IS NULL OR source = '')
                AND url LIKE ?
                """,
                (source, pattern)
            )
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 