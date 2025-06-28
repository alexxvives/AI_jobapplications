from fastapi import FastAPI, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Job, Base
import models
from schemas import UserCreate, UserLogin, UserResponse, Token, UserUpdate, JobResult
from auth import get_password_hash, verify_password, create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from pydantic import BaseModel
from urllib.parse import urljoin
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from threading import Lock
import threading
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import os
import shutil
import tempfile
from fastapi.staticfiles import StaticFiles
from llama_cpp import Llama
import json as pyjson
from pdfminer.high_level import extract_text as extract_pdf_text
import docx
import uuid

# Add GPU detection
try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
    if CUDA_AVAILABLE:
        print(f"[GPU] CUDA is available! Found {torch.cuda.device_count()} GPU(s)")
        for i in range(torch.cuda.device_count()):
            print(f"[GPU] GPU {i}: {torch.cuda.get_device_name(i)}")
    else:
        print("[GPU] CUDA is not available, will use CPU")
except ImportError:
    print("[GPU] PyTorch not installed, cannot detect CUDA")
    CUDA_AVAILABLE = False

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

# Create all tables
Base.metadata.create_all(bind=engine)  # type: ignore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(token)
        if payload is None or "sub" not in payload:
            return None
        user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
        if user is None:
            return None
        return user
    except Exception:
        return None

@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        email=user.email, 
        full_name=user.full_name, 
        hashed_password=hashed_password
    )  # type: ignore
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/profile", response_model=UserResponse)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)

@app.put("/profile", response_model=UserResponse)
def update_profile(update: UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if update.full_name is not None:
        current_user.full_name = update.full_name
    if update.location is not None:
        current_user.location = update.location
    if update.visa_status is not None:
        current_user.visa_status = update.visa_status
    db.commit()
    db.refresh(current_user)
    return UserResponse.from_orm(current_user)

@app.get("/")
def read_root():
    return {"message": "Job Automation Backend is running!"}

TOP_ASHBY_COMPANIES = [
    "openai", "ramp", "linear", "runway", "clever", "vanta", "posthog", "replit", "hex", "carta",
    "mercury", "tome", "arc", "tandem", "twelve", "tango", "census", "tigergraph", "turing", "tulip",
    "turingcom", "turinglabs", "turinginc", "turingio", "turingrobotics", "sardine", "kikoff", "eightsleep",
    "notion", "scaleai", "loom", "zapier", "asana", "airbyte", "dbt", "modernhealth", "openstore", "levels",
    "angelist", "substack", "discord", "brex", "benchling", "gem", "whatnot", "instabase", "affinitiv", "airbnb",
    "coinbase", "databricks", "dropbox", "github", "stripe", "gofundme"
]

# Companies that actually use Greenhouse (verified working)
TOP_GREENHOUSE_COMPANIES = [
    "gofundme",  # Verified working
    "stripe",    # Known to use Greenhouse
    "airbnb",    # Known to use Greenhouse
    "coinbase",  # Known to use Greenhouse
    "dropbox",   # Known to use Greenhouse
    "github",    # Known to use Greenhouse
    "databricks", # Known to use Greenhouse
    "strava",
    "xai",
    "newsbreak",  # Added NewsBreak
]

TOP_LEVER_COMPANIES = ["haus", "voleon", "valence", "attentive", "tala"]  # Test only with a known working Lever company
TOP_RIPPLING_COMPANIES = ["momentumcareers", "rippling", "incredible-health", "federated-it", "einc"]  # Add more as needed

CACHE_TTL = 60  # 1 minute for testing

def upsert_job(session: Session, job_dict):
    try:
        # First try to find existing job
        job = session.query(Job).filter_by(link=job_dict["link"]).first()
        if job:
            # Update existing job
            for k, v in job_dict.items():
                setattr(job, k, v)
        else:
            # Try to add new job
            job = Job(**job_dict)
            session.add(job)
            session.flush()  # This will raise an error if there's a unique constraint violation
    except Exception as e:
        # If we get a unique constraint error, try to update the existing job
        if "UNIQUE constraint failed" in str(e) or "IntegrityError" in str(e):
            session.rollback()
            # Try to find and update the existing job
            job = session.query(Job).filter_by(link=job_dict["link"]).first()
            if job:
                for k, v in job_dict.items():
                    setattr(job, k, v)
            else:
                # If we still can't find it, something is wrong - skip this job
                print(f"Warning: Could not upsert job with link {job_dict['link']}")
        else:
            # Re-raise other exceptions
            raise

def background_job_fetcher():
    all_jobs = []
    all_sources = [
        ("Ashby", TOP_ASHBY_COMPANIES, fetch_ashby_jobs),
        ("Greenhouse", TOP_GREENHOUSE_COMPANIES, lambda c: fetch_greenhouse_jobs(c, "")),
        ("Lever", TOP_LEVER_COMPANIES, lambda c: fetch_lever_jobs(c, "")),
        # ("Rippling", TOP_RIPPLING_COMPANIES, lambda c: fetch_rippling_jobs(c, "")),
    ]
    for source, companies, fetch_fn in all_sources:
        print(f"[Fetcher] Starting {source} job collection...")
        total = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch_fn, company): company for company in companies}
            for future in as_completed(futures):
                try:
                    jobs = future.result()
                    total += len(jobs)
                    for job in jobs:
                        job["source"] = source
                        all_jobs.append(job)
                except Exception:
                    pass
        print(f"[Fetcher] {source}: {total} jobs found")

    # Upsert jobs into DB, silently skip jobs with missing or empty link
    session = SessionLocal()
    try:
        for job_dict in all_jobs:
            if not job_dict.get("link"):
                continue
            upsert_job(session, job_dict)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"DB error: {e}")
    finally:
        session.close()

# Comment out background job fetcher and job extraction for now
# @app.on_event("startup")
# def start_background_fetcher():
#     t = threading.Thread(target=background_job_fetcher, daemon=True)
#     t.start()

@app.get("/search", response_model=List[JobResult])
def search_jobs(title: str, db: Session = Depends(get_db)):
    query = db.query(Job)
    if title:
        query = query.filter(Job.title.ilike(f"%{title}%"))
    jobs = query.order_by(Job.fetched_at.desc()).limit(50).all()
    return [
        JobResult(
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description or "",
            link=job.link,
            source=getattr(job, 'source', None)
        )
        for job in jobs
    ]

@app.get("/search_all", response_model=List[JobResult])
def search_all_jobs(title: str, location: str = "", limit: int = 50):
    """
    Search for jobs across all platforms (database + live scraping of Ashby, Greenhouse, Lever)
    Note: Indeed integration is blocked by anti-scraping measures (403 status)
    """
    all_jobs = []
    
    # Search in database first
    session = SessionLocal()
    try:
        query = session.query(Job)
        if title:
            query = query.filter(Job.title.ilike(f"%{title}%"))
        db_jobs = query.order_by(Job.fetched_at.desc()).limit(limit//2).all()
        for job in db_jobs:
            all_jobs.append(JobResult(
                id=job.id,
                title=str(job.title),
                company=str(job.company),
                location=str(job.location),
                description=str(job.description or ""),
                link=str(job.link),
                source=str(job.source)
            ))
    except Exception as e:
        print(f"[Search] Database error: {e}")
    finally:
        session.close()
    
    # Live scraping of working sources
    try:
        print(f"[Search] Live scraping for: {title}")
        
        # Ashby jobs
        ashby_jobs = fetch_ashby_jobs("openai")  # Test with OpenAI
        for job in ashby_jobs[:limit//6]:
            all_jobs.append(JobResult(
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                description=job.get("description", ""),
                link=job.get("link", ""),
                source=job.get("source", "Ashby")
            ))
        
        # Greenhouse jobs
        greenhouse_jobs = fetch_greenhouse_jobs("stripe", title)
        for job in greenhouse_jobs[:limit//6]:
            all_jobs.append(JobResult(
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                description=job.get("description", ""),
                link=job.get("link", ""),
                source=job.get("source", "Greenhouse")
            ))
            
    except Exception as e:
        print(f"[Search] Live scraping error: {e}")
    
    # Remove duplicates and limit results
    seen_links = set()
    unique_jobs = []
    for job in all_jobs:
        if job.link not in seen_links:
            seen_links.add(job.link)
            unique_jobs.append(job)
        if len(unique_jobs) >= limit:
            break
    
    print(f"[Search] Returning {len(unique_jobs)} unique jobs")
    return unique_jobs

def fetch_ashby_jobs(company: str) -> List[dict]:
    """Fetch jobs from Ashby GraphQL API for a specific company."""
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
    try:
        response = requests.post(graphql_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        job_board = data.get("data", {}).get("jobBoard")
        if not job_board:
            return []
        jobs = job_board.get("jobPostings", [])
        teams = {team["id"]: team["name"] for team in job_board.get("teams", [])}
        # Enhance jobs with team names
        for job in jobs:
            job["teamName"] = teams.get(job.get("teamId"), "")
        # Fetch job descriptions in parallel (first 3 lines only)
        def fetch_ashby_desc(job):
            job_id = job.get("id", "")
            description = ""
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
                resp = requests.post(graphql_url, headers=headers, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    html = data.get("data", {}).get("jobPosting", {}).get("descriptionHtml", "")
                    if html:
                        soup = BeautifulSoup(html, "html.parser")
                        lines = []
                        for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                            text = tag.get_text(strip=True)
                            if text:
                                lines.append(text)
                        description = "\n".join(lines[:3])
            except Exception as e:
                pass
            job["description"] = description
            return job
        with ThreadPoolExecutor(max_workers=8) as executor:
            jobs = list(executor.map(fetch_ashby_desc, jobs))
        # Build job dicts for DB
        job_dicts = []
        for job in jobs:
            job_dicts.append({
                "title": job.get("title", ""),
                "company": company.title(),
                "location": job.get("locationName", ""),
                "description": job.get("description", ""),
                "link": f"https://jobs.ashbyhq.com/{company}/{job.get('id', '')}",
            })
        return job_dicts
    except Exception as e:
        return []

def is_valid_job_link(url: str) -> bool:
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def fetch_greenhouse_jobs(company: str, title: str) -> list:
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    url = f"https://boards.greenhouse.io/{company}"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    job_rows = soup.select('tr.job-post')
    if not job_rows or len(job_rows) < 1:
        print(f"[Greenhouse] Skipping {company}: no job rows found (unexpected layout)")
        return []
    nav_titles = [
        'Life at', 'Benefits', 'University', 'See open roles', 'Current job openings at',
        'Login', 'Why', 'Discover', 'For Executives', 'For Startups', 'Lakehouse Architecture',
        'Mosaic Research', 'Customers', 'Customer Stories', 'Partners', 'Cloud Providers',
        'Contact Us', 'Careers', 'Working at', 'Open Jobs', 'Press', 'Awards and Recognition',
        'Newsroom', 'Security and Trust', 'Ready to get started?', 'Get a Demo', 'Try',
        'About', 'Events', 'Blog', 'Podcast', 'Insights', 'Get Help', 'Documentation',
        'Community', 'Resource Center', 'Demo Center', 'Architecture Center', 'Who We Are',
        'Our Team', 'Ventures', 'Awards', 'Recognition', 'Security', 'Trust', 'Started',
        'Sign in', 'Sign up', 'Apply now', 'Apply for this job', 'FAQ', 'Help', 'Support',
        'Contact', 'Legal', 'Privacy', 'Terms', 'Sitemap', 'Cookie', 'Transparency',
        'Licenses', 'Customer stories', 'Annual conference', 'Stripe Press', 'Stripe Apps',
        'Stripe App Marketplace', 'Stripe', 'Dashboard', 'Sign in', 'Sign up'
    ]
    def is_navigation_title(title: str) -> bool:
        t = title.strip().lower()
        for nav in nav_titles:
            if nav.lower() in t:
                return True
        if len(t) > 120 or sum(1 for nav in nav_titles if nav.lower() in t) > 1:
            return True
        return False
    for job_row in job_rows:
        link_elem = job_row.select_one('a[href*="/jobs/"]')
        if not link_elem:
            continue
        job_link = link_elem.get('href', '')
        if not job_link:
            continue
        if not job_link.startswith('http'):
            if job_link.startswith('/'):
                job_link = f"https://boards.greenhouse.io{job_link}"
            else:
                job_link = f"https://boards.greenhouse.io/{company}/{job_link}"
        m = re.search(r'/jobs/(\d+)', job_link)
        job_id = m.group(1) if m else None
        if not job_id:
            continue
        title_elem = link_elem.select_one('p.body.body--medium')
        job_title = title_elem.get_text(strip=True) if title_elem else ''
        if not job_title or len(job_title) < 3:
            continue
        if is_navigation_title(job_title):
            continue
        location = ''
        description = ''
        if company.lower() == 'stripe':
            try:
                detail_resp = requests.get(job_link, headers=headers, timeout=15)
                if detail_resp.status_code == 200:
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                    location = ''
                    for prop in detail_soup.select('div.JobDetailCardProperty'):
                        title_p = prop.select_one('p.JobDetailCardProperty__title')
                        if title_p and 'Office locations' in title_p.get_text():
                            sibling = title_p
                            while sibling is not None:
                                sibling = sibling.next_sibling
                                if sibling and getattr(sibling, 'name', None) == 'p':
                                    location = sibling.get_text(strip=True)
                                    break
                            if location:
                                break
                    if not location:
                        location_elem = link_elem.select_one('p.body.body__secondary.body--metadata')
                        location = location_elem.get_text(strip=True) if location_elem else ''
                    desc_blocks = []
                    desc_div = detail_soup.select_one('div.ArticleMarkdown')
                    if desc_div:
                        for tag in desc_div.find_all(['p', 'li', 'h2', 'h3', 'h4', 'h5', 'h6']):
                            text = tag.get_text(strip=True)
                            if text:
                                desc_blocks.append(text)
                            if len(desc_blocks) >= 3:
                                break
                        description = '\n'.join(desc_blocks)
            except Exception:
                pass
        else:
            location_elem = link_elem.select_one('p.body.body__secondary.body--metadata')
            location = location_elem.get_text(strip=True) if location_elem else ''
            description = ''
            try:
                api_url = f"https://boards.greenhouse.io/api/v1/boards/{company}/jobs/{job_id}"
                api_resp = requests.get(api_url, headers=headers, timeout=10)
                if api_resp.status_code == 200:
                    data = api_resp.json()
                    html = data.get('content', '')
                    if html:
                        soup_desc = BeautifulSoup(html, "html.parser")
                        lines = []
                        for tag in soup_desc.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                            text = tag.get_text(strip=True)
                            if text:
                                lines.append(text)
                        if lines:
                            description = "\n".join(lines[:3])
            except Exception:
                pass
            if not description:
                try:
                    detail_resp = requests.get(job_link, headers=headers, timeout=10)
                    if detail_resp.status_code == 200:
                        detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                        desc_selectors = [
                            '.content', '.job-description', '[class*="description"]',
                            '.posting-content', '.job-content', '.description',
                            'div[class*="content"]', 'div[class*="description"]',
                            '.main-content', '.section-content', '.job-details',
                            '.job-body', '.job-desc', '.job-details__content',
                        ]
                        for selector in desc_selectors:
                            desc_elem = detail_soup.select_one(selector)
                            if desc_elem:
                                text_blocks = []
                                for tag in desc_elem.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                                    text = tag.get_text(strip=True)
                                    if text:
                                        text_blocks.append(text)
                                    if len(text_blocks) >= 3:
                                        break
                                if text_blocks:
                                    description = "\n".join(text_blocks)
                                    break
                        if not description:
                            for div in detail_soup.find_all('div'):
                                class_attr = div.get('class', [])
                                if any('content' in c or 'description' in c for c in class_attr):
                                    text_blocks = []
                                    for tag in div.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                                        text = tag.get_text(strip=True)
                                        if text:
                                            text_blocks.append(text)
                                        if len(text_blocks) >= 3:
                                            break
                                    if text_blocks:
                                        description = "\n".join(text_blocks)
                                        break
                except Exception:
                    pass
        # Validate job link
        if not is_valid_job_link(job_link):
            job_link = f"https://boards.greenhouse.io/{company}"
        jobs.append({
            "title": job_title,
            "company": company.title(),
            "location": location,
            "description": description,
            "link": job_link,
        })
    return jobs

def fetch_lever_jobs(company: str, title: str) -> list:
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
    # Try API first (existing logic)
    api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                for job in data:
                    job_title = job.get('text', '')
                    def normalize(s):
                        return re.sub(r'[^a-z0-9 ]', '', s.lower())
                    if title and normalize(title) not in normalize(job_title):
                        continue
                    job_link = job.get('hostedUrl', '')
                    location = ', '.join(job.get('categories', {}).get('location', '').split(','))
                    # Fetch description (first 3 lines only)
                    description = ""
                    try:
                        detail_resp = requests.get(job_link, headers=headers, timeout=10)
                        if detail_resp.status_code == 200:
                            detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                            # Description extraction for Lever
                            desc_elem = detail_soup.select_one('div[data-qa="job-description"]')
                            if desc_elem:
                                # Get first three text blocks (split by <div> or <p>)
                                blocks = [b.get_text(strip=True) for b in desc_elem.find_all(['div', 'p']) if b.get_text(strip=True)]
                                description = '\n'.join(blocks[:3]) if blocks else desc_elem.get_text(strip=True)
                            else:
                                # Fallback to previous selectors
                                desc_elem = detail_soup.select_one('.content, .job-description, [class*="description"], .posting-content, .job-content, .description, div[class*="content"], div[class*="description"]')
                                if desc_elem:
                                    blocks = [b.get_text(strip=True) for b in desc_elem.find_all(['div', 'p']) if b.get_text(strip=True)]
                                    description = '\n'.join(blocks[:3]) if blocks else desc_elem.get_text(strip=True)
                                else:
                                    description = ''
                    except Exception:
                        pass
                    jobs.append({
                        "title": job_title,
                        "company": company.title(),
                        "location": location,
                        "description": description,
                        "link": job_link,
                    })
                if company == "haus":
                    print(f"[Lever Debug] Found {len(jobs)} jobs for haus via API")
                return jobs
            except Exception as e:
                pass
    except Exception as e:
        pass
    # Fallback to scraping with improved selectors
    try:
        url = f"https://jobs.lever.co/{company}"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"[Lever Debug] Failed to fetch {url}, status {resp.status_code}")
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Find job postings: links that match /{company}/<job_id>
        job_elements = [elem for elem in soup.find_all('a', href=True) if f'/{company}/' in elem['href'] and len(elem['href'].split('/')) == 4]
        print(f"[Lever Debug] Found {len(job_elements)} job links for {company}")
        for job_elem in job_elements:
            try:
                job_title = job_elem.get_text(strip=True)
                job_link = job_elem.get('href', '')
                if job_link and not job_link.startswith('http'):
                    job_link = f"https://jobs.lever.co{job_link}"
                if not job_title or len(job_title) < 3 or job_title.lower() in ["apply", "apply now", "apply for this job"]:
                    continue
                def normalize(s):
                    return re.sub(r'[^a-z0-9 ]', '', s.lower())
                if title and normalize(title) not in normalize(job_title):
                    continue
                description = ""
                try:
                    detail_resp = requests.get(job_link, headers=headers, timeout=10)
                    if detail_resp.status_code == 200:
                        detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                        desc_elem = detail_soup.select_one('div[data-qa="job-description"]')
                        if desc_elem:
                            blocks = [b.get_text(strip=True) for b in desc_elem.find_all(['div', 'p']) if b.get_text(strip=True)]
                            description = '\n'.join(blocks[:3]) if blocks else desc_elem.get_text(strip=True)
                        else:
                            desc_elem = detail_soup.select_one('.content, .job-description, [class*="description"], .posting-content, .job-content, .description, div[class*="content"], div[class*="description"]')
                            if desc_elem:
                                blocks = [b.get_text(strip=True) for b in desc_elem.find_all(['div', 'p']) if b.get_text(strip=True)]
                                description = '\n'.join(blocks[:3]) if blocks else desc_elem.get_text(strip=True)
                            else:
                                description = ''
                except Exception as e:
                    print(f"[Lever Debug] Error fetching/parsing job detail for {job_link}: {e}")
                jobs.append({
                    "title": job_title,
                    "company": company.title(),
                    "location": "",
                    "description": description,
                    "link": job_link,
                })
            except Exception as e:
                print(f"[Lever Debug] Error processing job element: {e}")
                continue
        print(f"[Lever Debug] Returning {len(jobs)} jobs for {company}")
        return jobs
    except Exception as e:
        print(f"[Lever Debug] Exception in fetch_lever_jobs for {company}: {e}")
    return []

def fetch_rippling_jobs(company: str, title: str) -> list:
    """Fetch jobs from Rippling for a specific company."""
    jobs = []
    try:
        url = f"https://ats.rippling.com/{company}/jobs"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find job postings with improved selectors - only real job postings
        job_elements = []
        
        # More specific selectors for real job listings
        selectors = [
            'a[href*="/jobs/"]',  # Links containing /jobs/
            '.job-card', '.job-listing', '.position-card',  # Common job card classes
            '[data-job-id]',  # Elements with job ID data attribute
            'div[class*="job"]', 'div[class*="position"]',  # Divs with job-related classes
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                job_elements.extend(elements)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_job_elements = []
        for elem in job_elements:
            elem_id = elem.get('href', '') or elem.get('data-job-id', '') or str(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique_job_elements.append(elem)
        
        for job_elem in unique_job_elements:
            try:
                # Extract job title - look for headers or title elements
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
                        if job_title and job_title.lower() != "apply":
                            break
                
                # If no title found, try getting text from the element itself
                if not job_title or job_title.lower() == "apply":
                    job_title = job_elem.get_text(strip=True)
                    # Clean up the title (remove extra whitespace, newlines)
                    job_title = re.sub(r'\s+', ' ', job_title).strip()
                    # Skip if it's just "Apply" or similar
                    if job_title.lower() in ["apply", "apply now", "apply for this job"]:
                        continue
                
                # Skip if not a real job title
                if not job_title or len(job_title) < 3:
                    continue
                
                # Extract location
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
                
                if job_link and not job_link.startswith('http'):
                    job_link = f"https://ats.rippling.com{job_link}"
                
                # Skip if no valid link
                if not job_link or '/jobs/' not in job_link:
                    continue
                
                # Fetch description (first 3 lines only)
                description = None
                try:
                    detail_resp = requests.get(job_link, headers=headers, timeout=10)
                    if detail_resp.status_code == 200:
                        detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                        
                        # Extract description (first 3 lines only)
                        desc_elem = detail_soup.find('div', class_=re.compile(r'description|job-description|posting-description', re.I))
                        if desc_elem:
                            desc_text = desc_elem.get_text(separator=' ', strip=True)
                            # Get first 3 sentences only
                            sentences = re.split(r'[.!?]+', desc_text)
                            description = '. '.join(sentences[:3]).strip() + ('...' if len(sentences) > 3 else '')
                        else:
                            # Fallback: first paragraph
                            p_elem = detail_soup.find('p')
                            if p_elem:
                                desc_text = p_elem.get_text(separator=' ', strip=True)
                                sentences = re.split(r'[.!?]+', desc_text)
                                description = '. '.join(sentences[:3]).strip() + ('...' if len(sentences) > 3 else '')
                
                except Exception as e:
                    pass
                
                # Filter by title if provided
                def normalize(s):
                    return re.sub(r'[^a-z0-9 ]', '', s.lower())
                if title and normalize(title) not in normalize(job_title):
                    continue
                
                jobs.append({
                    "title": job_title,
                    "company": company.title(),
                    "location": location,
                    "description": description,
                    "link": job_link,
                })
            except Exception as e:
                continue
        
        if company == "momentumcareers":
            print(f"[Rippling Debug] Found {len(jobs)} jobs for momentumcareers")
        return jobs
    except Exception as e:
        pass
    return [] 

@app.post("/upload_resume_llm", response_model=UserResponse)
def upload_resume_llm(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Check if filename exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Save uploaded file to a temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix="." + file.filename.split(".")[-1]) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    
    # Extract raw text
    resume_text = extract_text_from_file(tmp_path)
    try:
        os.remove(tmp_path)
    except Exception:
        pass
    
    # Prepare LLM prompt (shorter and more focused)
    prompt = f"""Extract from this resume and return as valid JSON:
- name
- phone
- location
- work_experience (array of objects with title, company, dates)
- education (array of objects with degree, school, year - degree is required)
- skills (array of strings)
- languages (array of strings)

Resume: {resume_text[:2000]}
JSON:"""
    
    # Log the prompt being sent to LLM
    print("\n" + "="*80)
    print("🤖 LLM PROMPT BEING SENT:")
    print("="*80)
    print(prompt)
    print("="*80)
    print("🤖 END OF PROMPT")
    print("="*80)
    
    # Use the Mistral model
    model_path = "./models/mistral-7b-instruct-v0.2.Q5_K_M.gguf"
    print(f"[DEBUG] Attempting to load Mistral model from: {model_path}")
    
    try:
        print("[DEBUG] About to instantiate Llama with CPU optimization...")
        
        # Configure for CPU usage with smaller context
        llm = Llama(
            model_path=model_path, 
            n_gpu_layers=0,  # Use CPU only
            n_ctx=2048,  # Smaller context window
            verbose=False
        )
        print("[DEBUG] Mistral model instantiated successfully")
        
        print("[DEBUG] About to call llm() for generation...")
        result = llm(prompt, max_tokens=1500, stop=["\nJSON:"])
        
        # Handle the response based on the actual structure
        if hasattr(result, 'choices') and result.choices:
            output = result.choices[0].text
        elif hasattr(result, 'text'):
            output = result.text
        elif isinstance(result, dict) and 'choices' in result:
            output = result['choices'][0]['text']
        else:
            output = str(result)
        print(f"[DEBUG] Model generation output received: {output[:500]}...")
        
        # Try to extract JSON from output
        try:
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                profile_json = pyjson.loads(output[json_start:json_end])
            else:
                print("[DEBUG] LLM did not return valid JSON format.")
                raise HTTPException(status_code=500, detail="LLM did not return valid JSON format.")
        except pyjson.JSONDecodeError as e:
            print(f"[DEBUG] LLM did not return valid JSON (JSONDecodeError): {e}. Output was: {output}")
            raise HTTPException(status_code=500, detail="LLM did not return valid JSON.")
        
        # Update user profile fields with extracted data
        if profile_json.get("name"):
            current_user.full_name = profile_json["name"]
        # Don't update email as it's used for authentication
        # if profile_json.get("email"):
        #     current_user.email = profile_json["email"]
        if profile_json.get("phone"):
            current_user.phone = profile_json["phone"]
        if profile_json.get("location"):
            current_user.location = profile_json["location"]
        if profile_json.get("skills"):
            current_user.skills = profile_json["skills"]
        if profile_json.get("languages"):
            current_user.languages = profile_json["languages"]
        if profile_json.get("work_experience"):
            current_user.work_experience = profile_json["work_experience"]
        if profile_json.get("education"):
            # Validate education data before storing
            education_data = profile_json["education"]
            if isinstance(education_data, list):
                # Filter out entries without required fields
                valid_education = []
                for edu in education_data:
                    if isinstance(edu, dict) and edu.get("school"):
                        # Ensure degree field exists, use school name as fallback
                        if not edu.get("degree"):
                            edu["degree"] = "Education at " + edu["school"]
                        valid_education.append(edu)
                current_user.education = valid_education
            else:
                current_user.education = education_data
        
        db.commit()
        db.refresh(current_user)
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        import traceback
        print(f"[DEBUG] Exception while loading or running Llama: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")

@app.post("/test_pdf_parse")
def test_pdf_parse(file: UploadFile = File(...)):
    """Test endpoint to extract and return text from a PDF file."""
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    try:
        text = extract_pdf_text(tmp_path)
    finally:
        os.remove(tmp_path)
    return {"text": text[:1000]}  # Return first 1000 chars for preview

LOGOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos")
app.mount("/logos", StaticFiles(directory=LOGOS_DIR), name="logos")

def extract_text_from_file(file_path):
    ext = file_path.split('.')[-1].lower()
    if ext == 'pdf':
        return extract_pdf_text(file_path)
    elif ext in ('doc', 'docx'):
        doc = docx.Document(file_path)
        return '\n'.join([p.text for p in doc.paragraphs])
    elif ext == 'txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return '' 

# Store active application sessions
application_sessions = {}

class CreateSessionRequest(BaseModel):
    job_ids: List[int]

@app.post("/chrome-extension/create-session")
def create_session(request: CreateSessionRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Create a session for desktop app with selected job IDs.
    Returns a session ID that the desktop app will use to fetch job data.
    """
    if not request.job_ids:
        raise HTTPException(status_code=400, detail="No jobs selected")
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Store the session data with job IDs
    application_sessions[session_id] = {
        "user_id": current_user.id,
        "job_ids": request.job_ids,
        "created_at": datetime.utcnow(),
        "status": "pending"
    }
    
    return {
        "session_id": session_id,
        "message": "Desktop app session created successfully"
    }

@app.post("/chrome-extension/setup")
def setup_chrome_extension(selected_jobs: List[str], db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Setup Chrome extension with selected jobs.
    Returns a session ID that the extension will use to fetch job data.
    """
    if not selected_jobs:
        raise HTTPException(status_code=400, detail="No jobs selected")
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Store the session data
    application_sessions[session_id] = {
        "user_id": current_user.id,
        "selected_jobs": selected_jobs,
        "created_at": datetime.utcnow(),
        "status": "pending"
    }
    
    return {
        "session_id": session_id,
        "message": "Chrome extension session created successfully"
    }

@app.get("/chrome-extension/jobs/{session_id}")
def get_jobs_for_extension(session_id: str):
    """
    Get job data for Chrome extension or desktop app.
    This endpoint is called by the extension/app to get the selected jobs.
    """
    if session_id not in application_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = application_sessions[session_id]
    
    # Get the actual job data from the database
    db = SessionLocal()
    try:
        jobs = []
        
        # Handle both job_ids (for desktop app) and selected_jobs (for chrome extension)
        if "job_ids" in session_data:
            # Desktop app sends job IDs
            for job_id in session_data["job_ids"]:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    jobs.append({
                        "id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "description": job.description,
                        "link": job.link,
                        "source": job.source
                    })
        elif "selected_jobs" in session_data:
            # Chrome extension sends job links
            for job_link in session_data["selected_jobs"]:
                job = db.query(Job).filter(Job.link == job_link).first()
                if job:
                    jobs.append({
                        "id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "description": job.description,
                        "link": job.link,
                        "source": job.source
                    })
        
        return {
            "jobs": jobs,
            "session_id": session_id,
            "total_jobs": len(jobs)
        }
    finally:
        db.close()

@app.post("/chrome-extension/update-status/{session_id}")
def update_application_status(session_id: str, job_id: int, status: str):
    """
    Update application status for a specific job.
    Called by the Chrome extension or desktop app when it completes an application.
    """
    if session_id not in application_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update the job status in the database
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            # You might want to create an Application model to track this
            # For now, we'll just log it
            print(f"Job {job_id} application status updated to: {status}")
        
        return {"message": "Status updated successfully"}
    finally:
        db.close() 