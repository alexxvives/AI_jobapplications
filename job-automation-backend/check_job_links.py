import requests
from database import SessionLocal, Job

def is_valid_job_link(url: str) -> bool:
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def get_fallback_link(source: str, company: str) -> str:
    company_slug = company.lower().replace(' ', '')
    if source and company_slug:
        if source.lower() == 'greenhouse':
            return f'https://boards.greenhouse.io/{company_slug}'
        elif source.lower() == 'ashby':
            return f'https://jobs.ashbyhq.com/{company_slug}'
        elif source.lower() == 'lever':
            return f'https://jobs.lever.co/{company_slug}'
    return ''

def fix_broken_job_links():
    session = SessionLocal()
    jobs = session.query(Job).all()
    updated = 0
    for job in jobs:
        link = str(job.link)
        source = str(getattr(job, 'source', ''))
        company = str(job.company)
        if not is_valid_job_link(link):
            fallback = get_fallback_link(source, company)
            if fallback and fallback != link:
                print(f"Updating broken link for {company}: {link} -> {fallback}")
                job.link = fallback
                updated += 1
    session.commit()
    print(f"Updated {updated} broken job links.")
    session.close()

if __name__ == "__main__":
    fix_broken_job_links() 