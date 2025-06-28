import sqlite3

def print_jobs_table_schema():
    db_path = "job_automation.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:")
    for t in tables:
        print(f"  {t[0]}")
    # Print jobs table schema
    print("\nSchema for jobs table:")
    cursor.execute("PRAGMA table_info(jobs)")
    columns = cursor.fetchall()
    if not columns:
        print("  (No columns found or table does not exist)")
    else:
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    conn.close()

if __name__ == "__main__":
    print_jobs_table_schema() 