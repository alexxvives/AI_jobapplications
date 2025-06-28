import httpx
import re
import json
import asyncio
from urllib.parse import urlencode
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import time
import random

class IndeedScraperV2:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Connection": "keep-alive",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    def parse_search_page(self, html_content: str) -> Dict:
        """Extract job data from embedded JSON in Indeed search page"""
        try:
            # Pattern to find the mosaic provider data
            regex_pattern = r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]=((\[[^\}]+)?\{[^\}]+:[^\}]+\}([^\{]+\])?);'
            match = re.search(regex_pattern, html_content)
            
            if not match:
                print("[Indeed V2] No mosaic provider data found in page")
                return {"results": [], "meta": []}
            
            json_string = match.group(1)
            data = json.loads(json_string)
            
            return {
                "results": data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", []),
                "meta": data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("tierSummaries", []),
            }
        except Exception as e:
            print(f"[Indeed V2] Error parsing search page: {e}")
            return {"results": [], "meta": []}
    
    def extract_job_data(self, job_result: Dict) -> Dict:
        """Extract relevant job information from Indeed job result"""
        try:
            # Extract basic job info
            job_title = job_result.get("jobTitle", "")
            company = job_result.get("companyName", "")
            location = job_result.get("formattedLocation", "")
            
            # Get job link
            job_link = ""
            if "jobKey" in job_result:
                job_key = job_result["jobKey"]
                job_link = f"https://www.indeed.com/viewjob?jk={job_key}"
            
            # Get job description (if available)
            description = ""
            if "sanitizedJobDescription" in job_result:
                desc_data = job_result["sanitizedJobDescription"]
                if "content" in desc_data:
                    # Parse HTML content to get text
                    soup = BeautifulSoup(desc_data["content"], "html.parser")
                    # Get first few paragraphs
                    paragraphs = soup.find_all(["p", "div", "li"])[:3]
                    description = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            return {
                "title": job_title,
                "company": company,
                "location": location,
                "description": description,
                "link": job_link,
                "source": "Indeed"
            }
        except Exception as e:
            print(f"[Indeed V2] Error extracting job data: {e}")
            return {}
    
    def search_jobs(self, query: str, location: str = "", max_pages: int = 3) -> List[Dict]:
        """Search for jobs on Indeed"""
        all_jobs = []
        
        try:
            # Build search URL
            params = {"q": query}
            if location:
                params["l"] = location
            
            base_url = "https://www.indeed.com/jobs"
            
            for page in range(max_pages):
                try:
                    # Add page parameter for pagination
                    if page > 0:
                        params["start"] = page * 10
                    
                    url = f"{base_url}?{urlencode(params)}"
                    print(f"[Indeed V2] Searching page {page + 1}: {url}")
                    
                    # Add random delay to avoid rate limiting
                    if page > 0:
                        time.sleep(random.uniform(2, 5))
                    
                    response = self.client.get(url, headers=self.headers)
                    
                    if response.status_code != 200:
                        print(f"[Indeed V2] HTTP {response.status_code} for page {page + 1}")
                        break
                    
                    # Parse the page
                    parsed_data = self.parse_search_page(response.text)
                    jobs = parsed_data.get("results", [])
                    
                    if not jobs:
                        print(f"[Indeed V2] No jobs found on page {page + 1}")
                        break
                    
                    # Extract job data
                    for job_result in jobs:
                        job_data = self.extract_job_data(job_result)
                        if job_data and job_data.get("title"):
                            all_jobs.append(job_data)
                    
                    print(f"[Indeed V2] Found {len(jobs)} jobs on page {page + 1}")
                    
                except Exception as e:
                    print(f"[Indeed V2] Error on page {page + 1}: {e}")
                    break
            
            print(f"[Indeed V2] Total jobs found: {len(all_jobs)}")
            return all_jobs
            
        except Exception as e:
            print(f"[Indeed V2] Error in search_jobs: {e}")
            return []

def fetch_indeed_jobs_v2(query: str, location: str = "") -> List[Dict]:
    """Main function to fetch Indeed jobs using the new scraper"""
    scraper = IndeedScraperV2()
    return scraper.search_jobs(query, location)

# Test function
if __name__ == "__main__":
    print("Testing Indeed Scraper V2...")
    jobs = fetch_indeed_jobs_v2("python developer", "remote")
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:3]:  # Show first 3 jobs
        print(f"- {job['title']} at {job['company']} ({job['location']})")
        print(f"  Link: {job['link']}")
        print(f"  Description: {job['description'][:100]}...")
        print() 