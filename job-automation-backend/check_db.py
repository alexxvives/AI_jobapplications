import sqlite3

def check_database():
    conn = sqlite3.connect('job_automation.db')
    cursor = conn.cursor()
    
    # Get total jobs
    cursor.execute('SELECT COUNT(*) FROM jobs')
    total_jobs = cursor.fetchone()[0]
    print(f'Total jobs: {total_jobs}')
    
    # Get distinct sources
    cursor.execute('SELECT DISTINCT source FROM jobs WHERE source IS NOT NULL')
    sources = cursor.fetchall()
    print(f'Sources: {[s[0] for s in sources]}')
    
    # Get Greenhouse jobs count
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE source = "Greenhouse"')
    greenhouse_count = cursor.fetchone()[0]
    print(f'Greenhouse jobs: {greenhouse_count}')
    
    # Show some sample Greenhouse jobs
    if greenhouse_count > 0:
        cursor.execute('SELECT title, company, location FROM jobs WHERE source = "Greenhouse" LIMIT 5')
        sample_jobs = cursor.fetchall()
        print('\nSample Greenhouse jobs:')
        for i, job in enumerate(sample_jobs, 1):
            print(f'{i}. {job[0]} - {job[1]} - {job[2]}')

    # Get Lever jobs count
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE source = "Lever"')
    lever_count = cursor.fetchone()[0]
    print(f'Lever jobs: {lever_count}')

    # Show some sample Lever jobs with description
    if lever_count > 0:
        cursor.execute('SELECT title, company, location, description FROM jobs WHERE source = "Lever" LIMIT 5')
        sample_lever_jobs = cursor.fetchall()
        print('\nSample Lever jobs:')
        for i, job in enumerate(sample_lever_jobs, 1):
            desc = job[3] if job[3] else 'No description'
            print(f'{i}. {job[0]} - {job[1]} - {job[2]}')
            print(f'   Description: {desc[:200]}...')
    
    # Check if any Lever job has a non-empty, non-null description
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE source = "Lever" AND description IS NOT NULL AND description != ""')
    lever_with_desc_count = cursor.fetchone()[0]
    if lever_with_desc_count > 0:
        print(f'Lever jobs with non-empty description: {lever_with_desc_count}')
        cursor.execute('SELECT title, company, location, description FROM jobs WHERE source = "Lever" AND description IS NOT NULL AND description != "" LIMIT 3')
        sample_lever_with_desc = cursor.fetchall()
        print('\nSample Lever jobs with description:')
        for i, job in enumerate(sample_lever_with_desc, 1):
            print(f'{i}. {job[0]} - {job[1]} - {job[2]}')
            print(f'   Description: {job[3][:200]}...')
    else:
        print('No Lever jobs with non-empty description found.')
    
    conn.close()

if __name__ == "__main__":
    check_database() 