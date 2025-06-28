import httpx
import re
import json
import time
import random
from urllib.parse import urlencode
from typing import List, Dict
from bs4 import BeautifulSoup

class IndeedScraperV3:
    def __init__(self):
        # Create a session with better headers and settings
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            http2=True,  # Enable HTTP/2
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate", 
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Cache-Control": "max-age=0",
            }
        )
    
    def get_homepage_first(self):
        """Get the homepage first to establish a session"""
        try:
            print("[Indeed V3] Getting homepage first...")
            response = self.client.get("https://www.indeed.com/")
            print(f"[Indeed V3] Homepage status: {response.status_code}")
            if response.status_code == 200:
                print("[Indeed V3] Successfully accessed homepage")
                return True
            else:
                print(f"[Indeed V3] Homepage failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[Indeed V3] Homepage error: {e}")
            return False
    
    def parse_search_page(self, html_content: str) -> Dict:
        """Extract job data from embedded JSON in Indeed search page"""
        try:
            # Try multiple regex patterns for the mosaic data
            patterns = [
                r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]=((\[[^\}]+)?\{[^\}]+:[^\}]+\}([^\{]+\])?);',
                r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]=(\{.*?\});',
                r'mosaic-provider-jobcards.*?=(\{.*?\});',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_content, re.DOTALL)
                if match:
                    try:
                        json_string = match.group(1)
                        data = json.loads(json_string)
                        
                        results = data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", [])
                        meta = data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("tierSummaries", [])
                        
                        print(f"[Indeed V3] Found {len(results)} jobs in mosaic data")
                        return {"results": results, "meta": meta}
                    except json.JSONDecodeError:
                        continue
            
            print("[Indeed V3] No mosaic provider data found in page")
            return {"results": [], "meta": []}
            
        except Exception as e:
            print(f"[Indeed V3] Error parsing search page: {e}")
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
            print(f"[Indeed V3] Error extracting job data: {e}")
            return {}
    
    def search_jobs(self, query: str, location: str = "", max_pages: int = 2) -> List[Dict]:
        """Search for jobs on Indeed with session management"""
        all_jobs = []
        
        try:
            # First get the homepage to establish a session
            if not self.get_homepage_first():
                print("[Indeed V3] Failed to establish session, trying direct search...")
            
            # Wait a bit before making the search request
            time.sleep(random.uniform(2, 4))
            
            # Build search URL
            params = {"q": query}
            if location:
                params["l"] = location
            
            base_url = "https://www.indeed.com/jobs"
            
            for page in range(max_pages):
                try:
                    # Add page parameter for pagination
                    if page > 0:
                        params["start"] = str(page * 10)
                    
                    url = f"{base_url}?{urlencode(params)}"
                    print(f"[Indeed V3] Searching page {page + 1}: {url}")
                    
                    # Add random delay to avoid rate limiting
                    if page > 0:
                        time.sleep(random.uniform(3, 6))
                    
                    response = self.client.get(url)
                    
                    print(f"[Indeed V3] Page {page + 1} status: {response.status_code}")
                    
                    if response.status_code != 200:
                        print(f"[Indeed V3] HTTP {response.status_code} for page {page + 1}")
                        if response.status_code == 403:
                            print("[Indeed V3] Blocked by Cloudflare protection")
                        break
                    
                    # Parse the page
                    parsed_data = self.parse_search_page(response.text)
                    jobs = parsed_data.get("results", [])
                    
                    if not jobs:
                        print(f"[Indeed V3] No jobs found on page {page + 1}")
                        break
                    
                    # Extract job data
                    for job_result in jobs:
                        job_data = self.extract_job_data(job_result)
                        if job_data and job_data.get("title"):
                            all_jobs.append(job_data)
                    
                    print(f"[Indeed V3] Found {len(jobs)} jobs on page {page + 1}")
                    
                except Exception as e:
                    print(f"[Indeed V3] Error on page {page + 1}: {e}")
                    break
            
            print(f"[Indeed V3] Total jobs found: {len(all_jobs)}")
            return all_jobs
            
        except Exception as e:
            print(f"[Indeed V3] Error in search_jobs: {e}")
            return []
        finally:
            self.client.close()

def fetch_indeed_jobs_v3(query: str, location: str = "") -> List[Dict]:
    """Main function to fetch Indeed jobs using the new scraper"""
    scraper = IndeedScraperV3()
    return scraper.search_jobs(query, location)

# Test function
if __name__ == "__main__":
    print("Testing Indeed Scraper V3...")
    jobs = fetch_indeed_jobs_v3("python developer", "remote")
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:3]:  # Show first 3 jobs
        print(f"- {job['title']} at {job['company']} ({job['location']})")
        print(f"  Link: {job['link']}")
        print(f"  Description: {job['description'][:100]}...")
        print() 