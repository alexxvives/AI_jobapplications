import sqlite3

def print_jobs_table_schema():
    db_path = "job_automation.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(jobs)")
    columns = cursor.fetchall()
    print("Current columns in jobs table:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    conn.close()

if __name__ == "__main__":
    print_jobs_table_schema() 