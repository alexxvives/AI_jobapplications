#!/usr/bin/env python3
"""
Test script to debug and improve Ashby logo fetching.
"""

import requests
from bs4 import BeautifulSoup
import os
import json

def test_ashby_logo_fetching():
    """Test fetching logo from an Ashby job board."""
    company = "runway"
    board_url = f"https://jobs.ashbyhq.com/{company}"
    
    print(f"Testing Ashby logo fetch for {company}")
    print(f"Board URL: {board_url}")
    
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    
    try:
        board_resp = requests.get(board_url, headers=headers, timeout=30)
        print(f"Response status: {board_resp.status_code}")
        
        if board_resp.status_code == 200:
            board_soup = BeautifulSoup(board_resp.text, "html.parser")
            
            # Try multiple logo selectors with more comprehensive coverage
            logo_selectors = [
                # Ashby-specific selectors
                "[data-testid='organization-logo']",
                ".organization-logo img",
                ".company-logo img",
                ".logo img",
                "header img",
                "nav img",
                # General selectors
                "img[alt*='logo']",
                "img[alt*='Logo']", 
                "img[alt*='company']",
                "img[alt*='Company']",
                "img[src*='logo']",
                "img[src*='Logo']",
                "[class*='logo'] img",
                "[class*='Logo'] img",
                # More specific selectors
                "img[alt*='runway']",
                "img[alt*='Runway']",
                # First few images in header/nav
                "header img:first-child",
                "nav img:first-child",
                ".header img:first-child",
                ".navbar img:first-child"
            ]
            
            print(f"Trying {len(logo_selectors)} logo selectors...")
            
            for i, selector in enumerate(logo_selectors):
                print(f"  {i+1}. Trying selector: {selector}")
                logo_img = board_soup.select_one(selector)
                
                if logo_img:
                    logo_src = logo_img.get("src")
                    alt_text = logo_img.get("alt", "")
                    print(f"     Found image! src: {logo_src}, alt: {alt_text}")
                    
                    if isinstance(logo_src, str) and logo_src:
                        # Fix relative URLs
                        if logo_src.startswith("//"):
                            logo_src = "https:" + logo_src
                        elif logo_src.startswith("/"):
                            logo_src = "https://jobs.ashbyhq.com" + logo_src
                        
                        print(f"     Final logo URL: {logo_src}")
                        
                        # Download logo
                        os.makedirs("logos", exist_ok=True)
                        ext = os.path.splitext(logo_src)[1].split("?")[0] or ".png"
                        logo_path = os.path.join("logos", f"{company}{ext}")
                        
                        try:
                            with requests.get(logo_src, stream=True, timeout=10) as r:
                                if r.status_code == 200:
                                    with open(logo_path, 'wb') as f:
                                        f.write(r.content)
                                    print(f"     Successfully downloaded to: {logo_path}")
                                    return logo_path
                                else:
                                    print(f"     Failed to download: status {r.status_code}")
                        except Exception as e:
                            print(f"     Download error: {e}")
                    else:
                        print(f"     Invalid src attribute: {logo_src}")
                else:
                    print(f"     No image found")
            
            print("No logo found with any selector!")
            
            # Let's also check what images are actually on the page
            print("\nAll images on the page:")
            all_images = board_soup.find_all("img")
            for i, img in enumerate(all_images[:10]):  # Show first 10 images
                src = img.get("src", "")
                alt = img.get("alt", "")
                classes = " ".join(img.get("class", []))
                print(f"  {i+1}. src: {src}, alt: {alt}, classes: {classes}")
            
            # Try to get logo from GraphQL API
            print("\nTrying GraphQL API for logo...")
            try:
                graphql_url = "https://jobs.ashbyhq.com/api/non-user-graphql"
                query = """
                query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
                  jobBoard: jobBoardWithTeams(
                    organizationHostedJobsPageName: $organizationHostedJobsPageName
                  ) {
                    teams { id name parentTeamId __typename }
                    jobPostings {
                      id title teamId locationId locationName workplaceType employmentType secondaryLocations { locationId locationName __typename } compensationTierSummary __typename }
                    __typename
                  }
                }
                """
                headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
                payload = {"operationName": "ApiJobBoardWithTeams", "query": query, "variables": {"organizationHostedJobsPageName": company}}
                
                resp = requests.post(graphql_url, headers=headers, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"GraphQL response keys: {list(data.keys())}")
                    if 'data' in data and 'jobBoard' in data['data']:
                        job_board = data['data']['jobBoard']
                        print(f"Job board keys: {list(job_board.keys())}")
                        # Check if there's any logo-related field
                        for key, value in job_board.items():
                            if 'logo' in key.lower() or 'image' in key.lower():
                                print(f"Found potential logo field: {key} = {value}")
                else:
                    print(f"GraphQL request failed: {resp.status_code}")
            except Exception as e:
                print(f"GraphQL error: {e}")
            
            # Check for any logo references in the HTML source
            print("\nSearching for logo references in HTML source...")
            html_text = board_resp.text.lower()
            logo_keywords = ['logo', 'brand', 'image', 'icon']
            for keyword in logo_keywords:
                if keyword in html_text:
                    print(f"Found '{keyword}' in HTML source")
            
        else:
            print(f"Failed to fetch page: {board_resp.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    return None

if __name__ == "__main__":
    test_ashby_logo_fetching() 