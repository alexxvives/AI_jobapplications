#!/usr/bin/env python3
"""
Test script to debug Ashby description fetching.
"""

import requests
from bs4 import BeautifulSoup
import json

def test_ashby_description():
    """Test fetching a single Ashby job description."""
    company = "runway"
    job_id = "2ac54814-c586-429f-9bfd-e865c79e97c2"  # From the database
    
    print(f"Testing Ashby description fetch for {company}, job {job_id}")
    
    try:
        graphql_url = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
        payload = {
            "operationName": "ApiJobPosting",
            "variables": {
                "jobPostingId": job_id,
                "organizationHostedJobsPageName": company
            },
            "query": "query ApiJobPosting($jobPostingId: String!, $organizationHostedJobsPageName: String!) { jobPosting(jobPostingId: $jobPostingId, organizationHostedJobsPageName: $organizationHostedJobsPageName) { id title descriptionHtml } }"
        }
        
        print(f"Making request to: {graphql_url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        resp = requests.post(graphql_url, headers=headers, json=payload, timeout=15)
        print(f"Response status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
            
            html = data.get("data", {}).get("jobPosting", {}).get("descriptionHtml", "")
            print(f"Raw HTML length: {len(html)}")
            
            if html:
                soup = BeautifulSoup(html, "html.parser")
                lines = []
                for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                    text = tag.get_text(strip=True)
                    if text:
                        lines.append(text)
                
                description = "\n".join(lines[:3])
                print(f"Extracted description: {description}")
                return description
            else:
                print("No HTML content found")
        else:
            print(f"Request failed with status {resp.status_code}")
            print(f"Response text: {resp.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    return None

if __name__ == "__main__":
    test_ashby_description() 