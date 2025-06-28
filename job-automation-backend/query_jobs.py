import sqlite3

db_path = r'C:\Users\alexx\AI_agent_JobApplications2\job-automation-backend\job_automation.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT id, title, company, source FROM jobs WHERE LOWER(title) LIKE '%data scientist%'")
rows = c.fetchall()
for row in rows:
    print(row)
print(f'Total: {len(rows)}')
conn.close() 