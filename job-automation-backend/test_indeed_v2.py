import httpx
import requests
from bs4 import BeautifulSoup
import time

def test_indeed_access():
    """Test different approaches to access Indeed"""
    
    # Test 1: Basic request with different headers
    print("=== Test 1: Basic request ===")
    headers1 = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get("https://www.indeed.com/jobs?q=python&l=remote", headers=headers1)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            if response.status_code == 200:
                print("Success! Page content length:", len(response.text))
                # Look for the mosaic data
                if "mosaic-provider-jobcards" in response.text:
                    print("Found mosaic data in response!")
                else:
                    print("No mosaic data found")
            else:
                print("Response text preview:", response.text[:500])
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test 2: Using requests library ===")
    try:
        response = requests.get("https://www.indeed.com/jobs?q=python&l=remote", headers=headers1, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Success with requests!")
            if "mosaic-provider-jobcards" in response.text:
                print("Found mosaic data!")
        else:
            print("Response text preview:", response.text[:500])
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test 3: Different User-Agent ===")
    headers2 = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get("https://www.indeed.com/jobs?q=python&l=remote", headers=headers2)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("Success with different headers!")
                if "mosaic-provider-jobcards" in response.text:
                    print("Found mosaic data!")
            else:
                print("Response text preview:", response.text[:500])
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test 4: Check if it's a bot detection page ===")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get("https://www.indeed.com/jobs?q=python&l=remote", headers=headers1)
            if response.status_code == 403:
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title')
                if title:
                    print(f"Page title: {title.get_text()}")
                
                # Look for common bot detection indicators
                if "bot" in response.text.lower() or "blocked" in response.text.lower():
                    print("Bot detection detected!")
                if "captcha" in response.text.lower():
                    print("CAPTCHA detected!")
                if "cloudflare" in response.text.lower():
                    print("Cloudflare protection detected!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_indeed_access() 