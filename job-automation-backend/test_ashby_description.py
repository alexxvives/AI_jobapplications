#!/usr/bin/env python3
"""
Test script to fetch and print the first three lines from descriptionHtml for a given Ashby job using the GraphQL endpoint.
"""

import requests
from bs4 import BeautifulSoup

def fetch_ashby_description(job_id, company):
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
    resp = requests.post(graphql_url, headers=headers, json=payload, timeout=15)
    print(f"Status code: {resp.status_code}")
    try:
        data = resp.json()
        print("Full API response:")
        import json as pyjson
        print(pyjson.dumps(data, indent=2))
        html = data.get("data", {}).get("jobPosting", {}).get("descriptionHtml", "")
        if html:
            soup = BeautifulSoup(html, "html.parser")
            lines = []
            for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                text = tag.get_text(strip=True)
                if text:
                    lines.append(text)
            description = "\n".join(lines[:3])
            print(f"First three lines for job {job_id}:")
            print(description)
            return description
        else:
            print("No descriptionHtml found.")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(resp.text)

if __name__ == "__main__":
    # Example job ID and company
    fetch_ashby_description("2ac54814-c586-429f-9bfd-e865c79e97c2", "runway") 