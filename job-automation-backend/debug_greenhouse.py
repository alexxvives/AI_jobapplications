#!/usr/bin/env python3
"""
Debug script to examine Greenhouse job scraping issues.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import sys

def debug_greenhouse_company(company: str):
    """Debug a specific Greenhouse company to understand the structure."""
    print(f"=== Debugging Greenhouse for {company} ===")
    
    # Try API first
    api_url = f"https://boards.greenhouse.io/embed/job_board?for={company}&format=json"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    
    print(f"1. Testing API: {api_url}")
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        print(f"   API Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   API Jobs found: {len(data.get('jobs', []))}")
            if data.get('jobs'):
                sample_job = data['jobs'][0]
                print(f"   Sample job from API:")
                print(f"     Title: {sample_job.get('title', 'N/A')}")
                print(f"     Location: {sample_job.get('location', 'N/A')}")
                print(f"     URL: {sample_job.get('absolute_url', 'N/A')}")
                
                # Test description fetching
                if sample_job.get('absolute_url'):
                    print(f"   Testing description fetch...")
                    try:
                        detail_resp = requests.get(sample_job['absolute_url'], headers=headers, timeout=10)
                        print(f"     Detail page status: {detail_resp.status_code}")
                        if detail_resp.status_code == 200:
                            detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                            
                            # Try multiple description selectors
                            desc_selectors = [
                                '.content', '.job-description', '[class*="description"]',
                                '.posting-content', '.job-content', '.description',
                                'div[class*="content"]', 'div[class*="description"]'
                            ]
                            
                            for selector in desc_selectors:
                                desc_elem = detail_soup.select_one(selector)
                                if desc_elem:
                                    text = desc_elem.get_text(separator=" ", strip=True)
                                    if text and len(text) > 50:
                                        print(f"     Found description with selector '{selector}':")
                                        print(f"       Length: {len(text)} chars")
                                        print(f"       Preview: {text[:200]}...")
                                        break
                            else:
                                print(f"     No description found with any selector")
                                # Save HTML for inspection
                                with open(f"{company}_detail.html", "w", encoding="utf-8") as f:
                                    f.write(detail_resp.text)
                                print(f"     Saved detail page HTML to {company}_detail.html")
                    except Exception as e:
                        print(f"     Error fetching description: {e}")
        else:
            print(f"   API not available")
    except Exception as e:
        print(f"   API error: {e}")
    
    # Test scraping
    print(f"\n2. Testing scraping: https://boards.greenhouse.io/{company}")
    try:
        url = f"https://boards.greenhouse.io/{company}"
        resp = requests.get(url, headers=headers, timeout=30)
        print(f"   Scraping Status: {resp.status_code}")
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Save HTML for inspection
            with open(f"{company}_board.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"   Saved board page HTML to {company}_board.html")
            
            # Look for job elements using the correct structure
            print(f"   Analyzing page structure...")
            
            # Based on the HTML analysis, jobs are in table rows with class "job-post"
            job_rows = soup.select('tr.job-post')
            print(f"   Found {len(job_rows)} job rows")
            
            for i, job_row in enumerate(job_rows[:3]):  # Show first 3 jobs
                print(f"   Job {i+1}:")
                
                # Get the link element
                link_elem = job_row.select_one('a[href*="/jobs/"]')
                if link_elem:
                    job_link = link_elem.get('href', '')
                    print(f"     Link: {job_link}")
                    
                    # Get title (first p with class "body body--medium")
                    title_elem = link_elem.select_one('p.body.body--medium')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        print(f"     Title: {title}")
                    
                    # Get location (second p with class "body body__secondary body--metadata")
                    location_elem = link_elem.select_one('p.body.body__secondary.body--metadata')
                    if location_elem:
                        location = location_elem.get_text(strip=True)
                        print(f"     Location: {location}")
                    
                    # Test description fetch
                    if job_link:
                        try:
                            detail_resp = requests.get(job_link, headers=headers, timeout=10)
                            if detail_resp.status_code == 200:
                                detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                                
                                # Look for description in the content field
                                content_elem = detail_soup.select_one('[class*="content"]')
                                if content_elem:
                                    text = content_elem.get_text(separator=" ", strip=True)
                                    if text and len(text) > 50:
                                        print(f"     Description length: {len(text)} chars")
                                        print(f"     Description preview: {text[:150]}...")
                                    else:
                                        print(f"     No description found")
                                else:
                                    print(f"     No content element found")
                        except Exception as e:
                            print(f"     Error fetching description: {e}")
                
                print()
            
            # Also check for any other job-related elements
            print(f"   Checking for other job elements...")
            other_selectors = [
                'a[href*="/jobs/"]',
                '.job-post',
                '[class*="job"]',
                '[class*="position"]'
            ]
            
            for selector in other_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"     Selector '{selector}': {len(elements)} elements")
        else:
            print(f"   Scraping failed")
    except Exception as e:
        print(f"   Scraping error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        company = sys.argv[1]
    else:
        company = "gofundme"
    debug_greenhouse_company(company) 