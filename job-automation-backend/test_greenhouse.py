import requests
from bs4 import BeautifulSoup
import re

def fetch_greenhouse_jobs(company: str, title: str) -> list:
    """Fetch jobs from Greenhouse for a specific company using the API if available, otherwise scrape the job board page."""
    jobs = []
    # Try API first
    api_url = f"https://boards.greenhouse.io/embed/job_board?for={company}&format=json"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    try:
        print(f"Trying API for {company}...")
        resp = requests.get(api_url, headers=headers, timeout=10)
        print(f"API response status: {resp.status_code}")
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"API data keys: {list(data.keys())}")
                print(f"Jobs found in API: {len(data.get('jobs', []))}")
                company_logo = ""
                # Try to get logo from the HTML page as before
                try:
                    board_url = f"https://boards.greenhouse.io/{company}"
                    board_resp = requests.get(board_url, headers=headers, timeout=30)
                    if board_resp.status_code == 200:
                        board_soup = BeautifulSoup(board_resp.text, "html.parser")
                        logo_img = board_soup.select_one("img[alt*='logo'], img[alt*='Logo'], .logo img, header img, .company-logo img")
                        if logo_img:
                            logo_src = logo_img.get("src")
                            if isinstance(logo_src, str):
                                if logo_src.startswith("//"):
                                    logo_src = "https:" + logo_src
                                elif logo_src.startswith("/"):
                                    logo_src = f"https://boards.greenhouse.io{logo_src}"
                                company_logo = logo_src
                except Exception as e:
                    print(f"Error fetching Greenhouse logo for {company}: {str(e)}")
                for job in data.get('jobs', []):
                    job_title = job.get('title', '')
                    def normalize(s):
                        return re.sub(r'[^a-z0-9 ]', '', s.lower())
                    if title and normalize(title) not in normalize(job_title):
                        continue
                    job_link = job.get('absolute_url', '')
                    location = job.get('location', '')
                    jobs.append({
                        "title": job_title,
                        "company": company.title(),
                        "location": location,
                        "link": job_link,
                        "logo": company_logo
                    })
                print(f"Found {len(jobs)} jobs for {company} via Greenhouse API")
                return jobs
            except Exception as e:
                print(f"Greenhouse API JSON error for {company}: {e}")
        else:
            print(f"Greenhouse API not available for {company}: {resp.status_code}")
    except Exception as e:
        print(f"Greenhouse API failed for {company}: {e}")
    # Fallback to scraping
    print(f"Falling back to scraping for Greenhouse company: {company}")
    try:
        url = f"https://boards.greenhouse.io/{company}"
        resp = requests.get(url, headers=headers, timeout=30)
        print(f"Scraping response status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Greenhouse job board not accessible for {company}: {resp.status_code}")
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        company_logo = ""
        try:
            logo_img = soup.select_one("img[alt*='logo'], img[alt*='Logo'], .logo img, header img, .company-logo img")
            if logo_img:
                logo_src = logo_img.get("src")
                if isinstance(logo_src, str):
                    if logo_src.startswith("//"):
                        logo_src = "https:" + logo_src
                    elif logo_src.startswith("/"):
                        logo_src = f"https://boards.greenhouse.io{logo_src}"
                    company_logo = logo_src
        except Exception as e:
            print(f"Error fetching Greenhouse logo for {company}: {str(e)}")
        
        # Improved job element detection for Greenhouse
        job_elements = []
        
        # Try multiple selectors for job listings
        selectors = [
            'a[href*="/jobs/"]',  # Links containing /jobs/
            '.job', '.position', '.opening', '.listing',  # Common job classes
            '[data-job-id]',  # Elements with job ID data attribute
            'div[class*="job"]', 'div[class*="position"]',  # Divs with job-related classes
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                job_elements.extend(elements)
                print(f"Found {len(elements)} elements with selector: {selector}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_job_elements = []
        for elem in job_elements:
            elem_id = elem.get('href', '') or elem.get('data-job-id', '') or str(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique_job_elements.append(elem)
        
        print(f"Found {len(unique_job_elements)} unique job elements to parse")
        
        for job_elem in unique_job_elements:
            try:
                # Try multiple approaches to get job title
                job_title = ""
                title_selectors = [
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',  # Headers
                    '[class*="title"]', '[class*="job-title"]',  # Title classes
                    '.job-title', '.position-title',  # Specific title classes
                ]
                
                for selector in title_selectors:
                    title_elem = job_elem.select_one(selector)
                    if title_elem:
                        job_title = title_elem.get_text(strip=True)
                        if job_title:
                            break
                
                # If no title found, try getting text from the element itself
                if not job_title:
                    job_title = job_elem.get_text(strip=True)
                    # Clean up the title (remove extra whitespace, newlines)
                    job_title = re.sub(r'\s+', ' ', job_title).strip()
                
                if not job_title or len(job_title) < 3:
                    continue
                
                # Try to get location
                location = ""
                location_selectors = [
                    '[class*="location"]', '[class*="place"]', '[class*="city"]',
                    '.location', '.job-location', '.position-location'
                ]
                
                for selector in location_selectors:
                    location_elem = job_elem.select_one(selector)
                    if location_elem:
                        location = location_elem.get_text(strip=True)
                        if location:
                            break
                
                # Get job link
                job_link = ""
                if job_elem.name == 'a':
                    job_link = job_elem.get('href', '')
                else:
                    link_elem = job_elem.find('a', href=True)
                    if link_elem:
                        job_link = link_elem.get('href', '')
                
                # Fix relative URLs
                if job_link and not job_link.startswith('http'):
                    if job_link.startswith('/'):
                        job_link = f"https://boards.greenhouse.io{job_link}"
                    else:
                        job_link = f"https://boards.greenhouse.io/{company}/{job_link}"
                
                # Filter by title if provided
                def normalize(s):
                    return re.sub(r'[^a-z0-9 ]', '', s.lower())
                if title and normalize(title) not in normalize(job_title):
                    continue
                
                jobs.append({
                    "title": job_title,
                    "company": company.title(),
                    "location": location,
                    "link": job_link,
                    "logo": company_logo
                })
                
            except Exception as e:
                print(f"Error parsing job element for {company}: {str(e)}")
                continue
        
        print(f"Found {len(jobs)} jobs for {company} via Greenhouse scraping")
        return jobs
    except Exception as e:
        print(f"Error fetching Greenhouse jobs for {company}: {e}")
    return []

if __name__ == "__main__":
    print("Testing Greenhouse for gofundme...")
    jobs = fetch_greenhouse_jobs('gofundme', '')
    print(f"Total jobs found: {len(jobs)}")
    for i, job in enumerate(jobs[:5]):
        print(f"{i+1}. {job['title']} - {job['location']}")
        print(f"   Link: {job['link']}")
        print() 