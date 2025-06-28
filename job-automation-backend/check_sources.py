import sqlite3

conn = sqlite3.connect('job_automation.db')
cursor = conn.cursor()

# Check jobs by source
cursor.execute('SELECT source, COUNT(*) FROM jobs GROUP BY source')
print('Jobs by source:')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

# Check total jobs
cursor.execute('SELECT COUNT(*) FROM jobs')
total = cursor.fetchone()[0]
print(f'\nTotal jobs: {total}')

# Check a few sample jobs from each source
cursor.execute('SELECT title, company, source FROM jobs LIMIT 10')
print('\nSample jobs:')
for row in cursor.fetchall():
    print(f'{row[0]} at {row[1]} ({row[2]})')

# Print the number of jobs with NULL or empty source
cursor.execute('SELECT COUNT(*) FROM jobs WHERE source IS NULL OR source = ""')
count = cursor.fetchone()[0]
print(f"\nJobs with NULL or empty source: {count}")

# Print a few examples of jobs with NULL or empty source
if count > 0:
    cursor.execute('SELECT title, company, url FROM jobs WHERE source IS NULL OR source = "" LIMIT 5')
    print("\nSample jobs with NULL or empty source:")
    for row in cursor.fetchall():
        print(row)

# Print the source, title, company, and url for the first 5 jobs
print("\nFirst 5 jobs and their source values:")
cursor.execute('SELECT source, title, company, url FROM jobs LIMIT 5')
for row in cursor.fetchall():
    print(row)

conn.close() 