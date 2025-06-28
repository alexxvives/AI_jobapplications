import sqlite3

conn = sqlite3.connect('job_automation.db')
cursor = conn.cursor()

# Delete all Lever jobs
cursor.execute('DELETE FROM jobs WHERE source = "Lever"')
conn.commit()
print('Deleted all Lever jobs from the database.')

conn.close() 