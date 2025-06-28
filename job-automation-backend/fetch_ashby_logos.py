#!/usr/bin/env python3
"""
Utility script to fetch logos for all Ashby companies using the Ashby GraphQL API.
"""

import requests
import os

TOP_ASHBY_COMPANIES = [
    "openai", "ramp", "linear", "runway", "clever", "vanta", "posthog", "replit", "hex", "carta",
    "mercury", "tome", "arc", "tandem", "twelve", "tango", "census", "tigergraph", "turing", "tulip",
    "turingcom", "turinglabs", "turinginc", "turingio", "turingrobotics", "sardine", "kikoff", "eightsleep",
    "notion", "scaleai", "loom", "zapier", "asana", "airbyte", "dbt", "modernhealth", "openstore", "levels",
    "angelist", "substack", "discord", "brex", "benchling", "gem", "whatnot", "instabase", "affinitiv", "airbnb",
    "coinbase", "databricks", "dropbox", "github", "stripe", "gofundme"
]

def fetch_ashby_logo(company: str) -> str:
    print(f"Fetching Ashby logo for {company}...")
    graphql_url = "https://jobs.ashbyhq.com/api/non-user-graphql"
    query = """
    query ApiOrganizationFromHostedJobsPageName($organizationHostedJobsPageName: String!, $searchContext: OrganizationSearchContext) {
      organization: organizationFromHostedJobsPageName(
        organizationHostedJobsPageName: $organizationHostedJobsPageName
        searchContext: $searchContext
      ) {
        name
        theme {
          logoWordmarkImageUrl
          logoSquareImageUrl
        }
      }
    }
    """
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    payload = {
        "operationName": "ApiOrganizationFromHostedJobsPageName",
        "query": query,
        "variables": {
            "organizationHostedJobsPageName": company,
            "searchContext": "JobPosting"
        }
    }
    try:
        resp = requests.post(graphql_url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            org = data.get("data", {}).get("organization", {})
            theme = org.get("theme", {})
            logo_url = theme.get("logoSquareImageUrl") or theme.get("logoWordmarkImageUrl")
            if logo_url:
                print(f"  Found logo URL: {logo_url}")
                # Download logo
                os.makedirs("logos", exist_ok=True)
                ext = os.path.splitext(logo_url)[1].split("?")[0] or ".png"
                logo_path = os.path.join("logos", f"{company}{ext}")
                try:
                    with requests.get(logo_url, stream=True, timeout=10) as r:
                        if r.status_code == 200:
                            with open(logo_path, 'wb') as f:
                                f.write(r.content)
                            print(f"  Successfully downloaded: {logo_path}")
                            return logo_path
                        else:
                            print(f"  Failed to download logo: status {r.status_code}")
                except Exception as e:
                    print(f"  Download error: {e}")
            else:
                print(f"  No logo URL found for {company}")
        else:
            print(f"  GraphQL request failed: {resp.status_code}")
    except Exception as e:
        print(f"  Error fetching logo for {company}: {e}")
    return ""

def main():
    print("=== Fetching Ashby Logos for All Companies ===\n")
    os.makedirs("logos", exist_ok=True)
    for company in TOP_ASHBY_COMPANIES:
        fetch_ashby_logo(company)
    print("\n=== Ashby Logo Fetching Complete ===")
    print("Check the 'logos' folder for downloaded images.")

if __name__ == "__main__":
    main() 