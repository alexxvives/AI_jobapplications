#!/usr/bin/env python3
"""
Utility script to fetch logos for all Greenhouse and Lever companies.
This script will download logos even if there are no open jobs.
"""

import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin

# Company lists from main.py
TOP_GREENHOUSE_COMPANIES = [
    "gofundme",  # Verified working
    "stripe",    # Known to use Greenhouse
    "airbnb",    # Known to use Greenhouse
    "coinbase",  # Known to use Greenhouse
    "dropbox",   # Known to use Greenhouse
    "github",    # Known to use Greenhouse
    "databricks" # Known to use Greenhouse
]

TOP_LEVER_COMPANIES = ["haus"]  # Test only with a known working Lever company

def fetch_greenhouse_logo(company: str) -> str:
    """Fetch logo from Greenhouse job board."""
    print(f"Fetching Greenhouse logo for {company}...")
    
    url = f"https://boards.greenhouse.io/{company}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"  Failed to fetch page: {resp.status_code}")
            return ""
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Try multiple logo selectors
        logo_selectors = [
            "img[alt*='logo']", "img[alt*='Logo']", ".logo img", "header img", ".company-logo img",
            "img[src*='logo']", "img[src*='Logo']", "[class*='logo'] img",
            ".header img:first-child", ".navbar img:first-child",
            "img[alt*='company']", "img[alt*='Company']"
        ]
        
        for selector in logo_selectors:
            logo_img = soup.select_one(selector)
            if logo_img:
                logo_src = logo_img.get("src")
                if isinstance(logo_src, str) and logo_src:
                    # Fix relative URLs
                    if logo_src.startswith("//"):
                        logo_src = "https:" + logo_src
                    elif logo_src.startswith("/"):
                        logo_src = f"https://boards.greenhouse.io{logo_src}"
                    
                    # Download logo
                    os.makedirs("logos", exist_ok=True)
                    ext = os.path.splitext(logo_src)[1].split("?")[0] or ".png"
                    logo_path = os.path.join("logos", f"{company}{ext}")
                    
                    try:
                        with requests.get(logo_src, stream=True, timeout=10) as r:
                            if r.status_code == 200:
                                with open(logo_path, 'wb') as f:
                                    f.write(r.content)
                                print(f"  Successfully downloaded: {logo_path}")
                                return logo_path
                            else:
                                print(f"  Failed to download logo: status {r.status_code}")
                    except Exception as e:
                        print(f"  Download error: {e}")
                break
        
        print(f"  No logo found for {company}")
        return ""
        
    except Exception as e:
        print(f"  Error fetching logo for {company}: {e}")
        return ""

def fetch_lever_logo(company: str) -> str:
    """Fetch logo from Lever job board."""
    print(f"Fetching Lever logo for {company}...")
    
    url = f"https://jobs.lever.co/{company}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"  Failed to fetch page: {resp.status_code}")
            return ""
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Try multiple logo selectors for Lever
        logo_selectors = [
            ".logo img", "header img", ".company-logo img",
            "img[alt*='logo']", "img[alt*='Logo']", 
            "img[src*='logo']", "img[src*='Logo']",
            "[class*='logo'] img", ".header img:first-child",
            "img[alt*='company']", "img[alt*='Company']"
        ]
        
        for selector in logo_selectors:
            logo_img = soup.select_one(selector)
            if logo_img:
                logo_src = logo_img.get("src")
                if isinstance(logo_src, str) and logo_src:
                    # Fix relative URLs
                    if logo_src.startswith("//"):
                        logo_src = "https:" + logo_src
                    elif logo_src.startswith("/"):
                        logo_src = f"https://jobs.lever.co{logo_src}"
                    
                    # Download logo
                    os.makedirs("logos", exist_ok=True)
                    ext = os.path.splitext(logo_src)[1].split("?")[0] or ".png"
                    logo_path = os.path.join("logos", f"{company}{ext}")
                    
                    try:
                        with requests.get(logo_src, stream=True, timeout=10) as r:
                            if r.status_code == 200:
                                with open(logo_path, 'wb') as f:
                                    f.write(r.content)
                                print(f"  Successfully downloaded: {logo_path}")
                                return logo_path
                            else:
                                print(f"  Failed to download logo: status {r.status_code}")
                    except Exception as e:
                        print(f"  Download error: {e}")
                break
        
        print(f"  No logo found for {company}")
        return ""
        
    except Exception as e:
        print(f"  Error fetching logo for {company}: {e}")
        return ""

def main():
    """Fetch logos for all companies."""
    print("=== Fetching Logos for All Companies ===\n")
    
    # Create logos directory
    os.makedirs("logos", exist_ok=True)
    
    # Fetch Greenhouse logos
    print("--- Greenhouse Companies ---")
    for company in TOP_GREENHOUSE_COMPANIES:
        fetch_greenhouse_logo(company)
        time.sleep(1)  # Be nice to servers
    
    print("\n--- Lever Companies ---")
    for company in TOP_LEVER_COMPANIES:
        fetch_lever_logo(company)
        time.sleep(1)  # Be nice to servers
    
    print("\n=== Logo Fetching Complete ===")
    print("Check the 'logos' folder for downloaded images.")

if __name__ == "__main__":
    main() 