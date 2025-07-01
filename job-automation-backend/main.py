from fastapi import FastAPI, Depends, HTTPException, status, Query, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Job, Base
import models
from schemas import UserCreate, UserLogin, UserResponse, Token, UserUpdate, JobResult, ProfileCreate, ProfileUpdate, ProfileResponse
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
import json as pyjson
from pdfminer.high_level import extract_text as extract_pdf_text
import docx
import uuid
from models import Profile
import torch
from contextlib import redirect_stdout, redirect_stderr
import io

# Import configuration (this will configure logging automatically)
import config

# Always enable LLM debug output
config.DEBUG_LLM = True

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "chrome-extension://jfcimmieenbgbchfgmogceflafddmkpk"
    ],
    allow_credentials=True,
    allow_methods=["*"],
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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_password
    )  # type: ignore
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(f"[LOGIN DEBUG] Received username: {form_data.username}")
    print(f"[LOGIN DEBUG] Received password: {form_data.password}")
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
    return current_user

@app.put("/profile", response_model=UserResponse)
def update_profile(update: UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Only allow updating email and password for User model
    if update.email is not None:
        setattr(current_user, 'email', update.email)
    if update.password is not None:
        setattr(current_user, 'hashed_password', get_password_hash(update.password))
    db.commit()
    db.refresh(current_user)
    return current_user

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
            title=str(job.title),
            company=str(job.company),
            location=str(job.location),
            description=str(job.description or ""),
            link=str(job.link),
            source=getattr(job, 'source', None)
        )
        for job in jobs
    ]

@app.get("/search_database", response_model=List[JobResult])
def search_database_only(title: str, location: str = "", limit: int = 50):
    """
    Fast database-only search (no live scraping)
    Returns jobs from the cached database only
    """
    session = SessionLocal()
    try:
        query = session.query(Job)
        if title:
            query = query.filter(Job.title.ilike(f"%{title}%"))
        if location:
            query = query.filter(Job.location.ilike(f"%{location}%"))
        db_jobs = query.order_by(Job.fetched_at.desc()).limit(limit).all()
        
        results = []
        for job in db_jobs:
            results.append(JobResult(
                id=job.id,
                title=str(job.title),
                company=str(job.company),
                location=str(job.location),
                description=str(job.description or ""),
                link=str(job.link),
                source=str(job.source)
            ))
        
        print(f"[Search] Database-only search returned {len(results)} jobs")
        return results
        
    except Exception as e:
        print(f"[Search] Database error: {e}")
        return []
    finally:
        session.close()

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
                id=job.get("id", 0),
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
                id=job.get("id", 0),
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

@app.post("/upload_resume_llm", response_model=ProfileResponse)
def upload_resume_llm(file: UploadFile = File(...), title: str = Query(None, description="Profile title"), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Upload and parse resume using LLM with split extraction approach
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Validate file type
    allowed_extensions = {'.pdf', '.doc', '.docx'}
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Create temporary file
    tmp_path = None
    try:
        # Create a temporary file with the correct extension
        suffix = file_extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_path = tmp_file.name
            # Write uploaded file content to temporary file
            content = file.file.read()
            tmp_file.write(content)
            tmp_file.flush()
        
        if config.DEBUG_LLM:
            print(f"[DEBUG] Temporary file created: {tmp_path}")
            print(f"[DEBUG] File size: {len(content)} bytes")
        
        # Extract text from the file
        resume_text = extract_text_from_file(tmp_path)
        
        if not resume_text or len(resume_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract meaningful text from the uploaded file. Please ensure the file contains readable text.")
        
        if config.DEBUG_LLM:
            print(f"[DEBUG] Extracted text length: {len(resume_text)} characters")
            print(f"[DEBUG] First 200 characters: {resume_text[:200]}...")
        
    except Exception as e:
        if config.DEBUG_LLM:
            print(f"[DEBUG] Error extracting text: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract text from file: {str(e)}")
    finally:
        try:
            os.remove(tmp_path)
            print(f"[DEBUG] Temporary file removed: {tmp_path}")
        except Exception:
            pass
    
    # Check if current_user is valid
    if not current_user:
        raise HTTPException(status_code=401, detail="User authentication failed. Please log in again.")
    
    if not hasattr(current_user, 'id') or current_user.id is None:
        raise HTTPException(status_code=401, detail="Invalid user session. Please log in again.")
    
    # Extract resume email for comparison and logging
    resume_email = None
    
    if config.DEBUG_LLM:
        print(f"[DEBUG] Using Ollama for single-call extraction...")
        print(f"[DEBUG] Resume text length: {len(resume_text)} characters")
    
    # Create a comprehensive prompt for Ollama
    prompt = f"""
You are an expert data extraction agent. Your task is to extract structured information from the provided resume and return a **strictly valid JSON** object matching the schema defined below. All keys must always be present, even if values are missing.

## Output Format (MUST MATCH EXACTLY):

{{
  "personal_information": {{
    "full_name": "string",
    "email": "string",
    "phone": "string",
    "image_url": "string or null",
    "gender": "string or null",
    "address": "string or null",
    "city": "string or null",
    "state": "string or null",
    "zip_code": "string or null",
    "country": "string or null",
    "citizenship": "string or null"
  }},
  "work_experience": [
    {{
      "title": "string",
      "company": "string",
      "location": "string",
      "start_date": "string (YYYY-MM or similar)",
      "end_date": "string or null (use null if current)",
      "description": "string"
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "school": "string (institution name)",
      "start_date": "string (YYYY-MM or similar)",
      "end_date": "string (YYYY-MM or similar) or null if current",
      "gpa": "string or null"
    }}
  ],
  "skills": [
    {{
      "name": "string",
      "years": "integer or null"
    }}
  ],
  "languages": ["string", "string", "..."],
  "job_preferences": {{
    "linkedin": "string",
    "twitter": "string",
    "github": "string",
    "portfolio": "string",
    "other_url": "string",
    "notice_period": "string",
    "total_experience": "string",
    "default_experience": "string",
    "highest_education": "string",
    "companies_to_exclude": "string",
    "willing_to_relocate": "string",
    "driving_license": "string",
    "visa_requirement": "string",
    "race_ethnicity": "string"
  }},
  "achievements": [
    {{
      "title": "string",
      "issuer": "string or null",
      "date": "string or null",
      "description": "string or null"
    }}
  ],
  "certificates": [
    {{
      "name": "string",
      "organization": "string or null",
      "issue_date": "string or null",
      "expiry_date": "string or null",
      "credential_id": "string or null",
      "credential_url": "string or null"
    }}
  ]
}}

## IMPORTANT RULES:
- Return **only valid JSON**, no additional explanation or text.
- All fields in `job_preferences` must be **strings**. If a value is numeric, boolean, or a list, convert it to a string. If missing, return an empty string.
- Dates should be in a consistent format (e.g., `YYYY-MM`). If not available, return `null`.
- If a field is not mentioned in the resume, fill it with `null`, `""`, or an empty list `[]`, depending on the data type.
- `skills`, `achievements`, and `certificates` must be returned as structured objects — **not strings**.
- Assume any structured info (e.g., LinkedIn URLs, GitHub, salary info, visa, notice period) might appear anywhere in the resume — including footers, headers, or sidebars.
- If the job description is in bullet points, concatenate all bullet points into a single string, separated by newlines. Include all bullet points and narrative text under that job as the description. Do not omit any bullet points, even if there are many.

Example for a work experience:

Software Engineer, Acme Corp
Jan 2020 – Present
• Built X
• Improved Y
• Led Z

Output:
{{
  "work_experience": [
    {{
      "title": "Software Engineer",
      "company": "Acme Corp",
      "start_date": "2020-01",
      "end_date": "",
      "description": "• Built X\\n• Improved Y\\n• Led Z"
    }}
  ]
}}

Now extract the structured data from the following resume:
{resume_text}

Return only the JSON.
"""
    
    if config.DEBUG_LLM:
        print(f"\n[DEBUG] ========================================")
        print(f"[DEBUG] SINGLE CALL WITH OLLAMA")
        print(f"[DEBUG] ========================================")
        print(f"[DEBUG] Prompt length: {len(prompt)} characters")
        print(f"[DEBUG] Starting LLM generation...")
    
    # Instead, define a helper to call Ollama
    def call_ollama(prompt, model="llama3"):
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0
            }
        )
        response.raise_for_status()
        return response.json()["response"]

    try:
        # Call Ollama with comprehensive prompt
        output = call_ollama(prompt)
        if config.DEBUG_LLM:
            print(f"[DEBUG] Raw output length: {len(output)} characters")
            print(f"[DEBUG] Raw output: {output}")
        # Extract the JSON object from the output, even if extra text is present
        start = output.find('{')
        end = output.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = output[start:end+1]
        else:
            json_str = output  # fallback
        cleaned_output = json_str.strip()
        # Remove Markdown code blocks
        cleaned_output = re.sub(r'```json\s*', '', cleaned_output, flags=re.IGNORECASE)
        cleaned_output = re.sub(r'```\s*', '', cleaned_output)
        cleaned_output = re.sub(r'^\s*```\s*$', '', cleaned_output, flags=re.MULTILINE)
        # Remove comments and trailing commas
        cleaned_output = re.sub(r'^\s*//.*$', '', cleaned_output, flags=re.MULTILINE)
        cleaned_output = re.sub(r',\s*([}\]])', r'\1', cleaned_output)
        # Try to parse the JSON
        try:
            profile_json = pyjson.loads(cleaned_output)
            if config.DEBUG_LLM:
                print(f"[DEBUG] JSON parsed successfully!")
                print(f"[DEBUG] Profile keys: {list(profile_json.keys())}")
            
            # Extract personal information from the new structure
            if "personal_information" in profile_json:
                personal_info = profile_json["personal_information"]
                # Flatten personal information for database compatibility
                profile_json.update({
                    "full_name": personal_info.get("full_name", ""),
                    "email": personal_info.get("email", ""),
                    "phone": personal_info.get("phone", ""),
                    "image_url": personal_info.get("image_url"),
                    "gender": personal_info.get("gender"),
                    "address": personal_info.get("address"),
                    "city": personal_info.get("city"),
                    "state": personal_info.get("state"),
                    "zip_code": personal_info.get("zip_code"),
                    "country": personal_info.get("country"),
                    "citizenship": personal_info.get("citizenship")
                })
                # Remove the personal_information wrapper to avoid confusion
                del profile_json["personal_information"]
                
        except Exception as e:
            if config.DEBUG_LLM:
                print(f"[DEBUG] JSON parsing failed: {e}")
                print(f"[DEBUG] Cleaned output: {cleaned_output}")
            # Fallback to empty profile
            profile_json = {
                "full_name": "",
                "email": "",
                "phone": "",
                "image_url": None,
                "gender": None,
                "work_experience": [],
                "education": [],
                "skills": [],
                "languages": [],
                "job_preferences": {},
                "achievements": [],
                "certificates": []
            }

        # --- PATCH OLLAMA OUTPUT TO MATCH SCHEMA ---
        def ensure_list_of_dicts(val):
            if isinstance(val, list):
                # If it's a list of strings, convert to list of dicts
                if all(isinstance(x, str) for x in val):
                    return [{"name": x, "years": None} for x in val]
                if all(isinstance(x, dict) for x in val):
                    # Clean up skills years field - convert strings like "6+" to integers
                    cleaned_skills = []
                    for skill in val:
                        cleaned_skill = skill.copy()
                        if 'years' in cleaned_skill:
                            years_val = cleaned_skill['years']
                            if isinstance(years_val, str):
                                # Extract number from strings like "6+", "4+ years", etc.
                                import re
                                match = re.search(r'(\d+)', years_val)
                                if match:
                                    cleaned_skill['years'] = int(match.group(1))
                                else:
                                    cleaned_skill['years'] = None
                            elif years_val is None:
                                cleaned_skill['years'] = None
                            else:
                                # Try to convert to int, fallback to None
                                try:
                                    cleaned_skill['years'] = int(years_val)
                                except (ValueError, TypeError):
                                    cleaned_skill['years'] = None
                        cleaned_skills.append(cleaned_skill)
                    return cleaned_skills
            if isinstance(val, str):
                items = [x.strip() for x in val.split(",") if x.strip()]
                return [{"name": x, "years": None} for x in items]
            return []

        def ensure_list_of_objs(val, keys):
            if isinstance(val, list):
                if all(isinstance(x, dict) for x in val):
                    # Clean up work experience fields - ensure no None values for required fields
                    cleaned_items = []
                    for item in val:
                        cleaned_item = {}
                        for key in keys:
                            value = item.get(key)
                            if value is None:
                                cleaned_item[key] = ""  # Convert None to empty string
                            else:
                                cleaned_item[key] = str(value)  # Ensure it's a string
                        cleaned_items.append(cleaned_item)
                    return cleaned_items
                if all(isinstance(x, str) for x in val):
                    return [{keys[0]: x} for x in val]
            if isinstance(val, str):
                items = [x.strip() for x in val.split(",") if x.strip()]
                return [{keys[0]: x} for x in items]
            return []

        def fix_languages(val):
            if isinstance(val, list):
                # If it's a list of dicts with 'name', extract the names
                if all(isinstance(x, dict) and 'name' in x for x in val):
                    return [x['name'] for x in val]
                if all(isinstance(x, str) for x in val):
                    return val
            if isinstance(val, str):
                return [val]
            return []

        profile_json["skills"] = ensure_list_of_dicts(profile_json.get("skills", []))
        profile_json["achievements"] = ensure_list_of_objs(profile_json.get("achievements", []), ["title"])
        profile_json["certificates"] = ensure_list_of_objs(profile_json.get("certificates", []), ["name"])
        profile_json["languages"] = fix_languages(profile_json.get("languages", []))
        
        # Clean up work experience specifically
        if "work_experience" in profile_json:
            work_exp = profile_json["work_experience"]
            if isinstance(work_exp, list):
                cleaned_work_exp = []
                for exp in work_exp:
                    if isinstance(exp, dict):
                        # Ignore work experience entries without a company value
                        if not exp.get("company"):
                            continue
                        cleaned_exp = {}
                        for field in ["title", "company", "location", "start_date", "end_date", "description"]:
                            value = exp.get(field)
                            if value is None:
                                cleaned_exp[field] = ""  # Convert None to empty string
                            else:
                                cleaned_exp[field] = str(value)  # Ensure it's a string
                        cleaned_work_exp.append(cleaned_exp)
                profile_json["work_experience"] = cleaned_work_exp
        # --- END PATCH ---

        # Extract resume email
        if "email" in profile_json:
            resume_email = profile_json["email"]
    except Exception as e:
        if config.DEBUG_LLM:
            print(f"[DEBUG] LLM call failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")
    
    if config.DEBUG_LLM:
        print(f"[DEBUG] Final profile contains:")
        print(f"[DEBUG] - Work experiences: {len(profile_json.get('work_experience', []))}")
        print(f"[DEBUG] - Education entries: {len(profile_json.get('education', []))}")
        print(f"[DEBUG] - Skills: {len(profile_json.get('skills', []))}")
        print(f"[DEBUG] - Languages: {len(profile_json.get('languages', []))}")
    
    # Ensure all required fields exist
    required_fields = [
        "full_name", "email", "phone", "image_url", "gender", "work_experience", 
        "education", "skills", "languages", "job_preferences", "achievements", "certificates"
    ]
    
    for field in required_fields:
        if field not in profile_json:
            if field in ["work_experience", "education", "skills", "languages", "achievements", "certificates"]:
                profile_json[field] = []
            elif field == "job_preferences":
                profile_json[field] = {}
            else:
                profile_json[field] = None
    
    try:
        # Always create a new Profile for each upload
        from fastapi.encoders import jsonable_encoder
        from schemas import ProfileCreate
        # Prepare the profile data
        profile_data = {
            'title': title or "Resume Profile",
            'full_name': profile_json.get('full_name', None),
            'email': profile_json.get('email', None),
            'phone': profile_json.get('phone', None),
            'image_url': profile_json.get('image_url', None),
            'address': profile_json.get('address', None),
            'city': profile_json.get('city', None),
            'state': profile_json.get('state', None),
            'zip_code': profile_json.get('zip_code', None),
            'country': profile_json.get('country', None),
            'citizenship': profile_json.get('citizenship', None),
            'gender': profile_json.get('gender', None),
            'skills': profile_json.get('skills', []),
            'languages': profile_json.get('languages', []),
            'work_experience': profile_json.get('work_experience', []),
            'education': profile_json.get('education', []),
            'job_preferences': profile_json.get('job_preferences', {}),
            'achievements': profile_json.get('achievements', []),
            'certificates': profile_json.get('certificates', []),
        }
        # Use the ProfileCreate schema for validation
        profile_create = ProfileCreate(**profile_data)
        # Call the create_profile endpoint logic directly
        from fastapi import Request
        new_profile = create_profile(profile_create, current_user=current_user, db=db)
        db.commit()
        db.refresh(new_profile)
        if config.DEBUG_LLM:
            print(f"[DEBUG] New profile created with ID: {new_profile.id}")
        # Return the created profile data
        return ProfileResponse(
            id=new_profile.id,
            user_id=current_user.id,
            title=new_profile.title,
            full_name=new_profile.full_name,
            email=new_profile.email,
            phone=new_profile.phone,
            image_url=new_profile.image_url,
            address=new_profile.address,
            city=new_profile.city,
            state=new_profile.state,
            zip_code=new_profile.zip_code,
            country=new_profile.country,
            citizenship=new_profile.citizenship,
            gender=new_profile.gender,
            skills=new_profile.skills,
            languages=new_profile.languages,
            work_experience=new_profile.work_experience,
            education=new_profile.education,
            job_preferences=new_profile.job_preferences,
            achievements=new_profile.achievements,
            certificates=new_profile.certificates,
            created_at=new_profile.created_at,
            updated_at=new_profile.updated_at
        )
    except Exception as e:
        db.rollback()
        if config.DEBUG_LLM:
            print(f"[DEBUG] Error saving profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {str(e)}")

class DeleteResponse(BaseModel):
    message: str

class TestPdfResponse(BaseModel):
    text: str

@app.post("/test_pdf_parse", response_model=TestPdfResponse)
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
    return TestPdfResponse(text=text[:1000])  # Return first 1000 chars for preview

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

@app.middleware("http")
async def log_cors_headers(request: Request, call_next):
    origin = request.headers.get("origin")
    print(f"[CORS DEBUG] Incoming request from Origin: {origin}")
    response = await call_next(request)
    print(f"[CORS DEBUG] Response headers: {dict(response.headers)}")
    return response 

@app.get("/profiles", response_model=List[ProfileResponse])
def list_profiles(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profiles = db.query(Profile).filter(Profile.user_id == current_user.id).all()
    return profiles

@app.get("/profiles/{profile_id}", response_model=ProfileResponse)
def get_profile_by_id(profile_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.post("/profiles", response_model=ProfileResponse)
def create_profile(profile: ProfileCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    print("[DEBUG] /profiles POST called by user:", current_user.email if current_user else None)
    print("[DEBUG] Incoming profile data:", profile.dict())
    try:
        profile_data = profile.dict(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
        new_profile = Profile(user_id=current_user.id, **profile_data)
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        print("[DEBUG] Profile saved successfully, id:", new_profile.id)
        return new_profile
    except Exception as e:
        import traceback
        print(f"[DEBUG] Exception in /profiles POST: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Profile save failed: {str(e)}")

@app.put("/profiles/{profile_id}", response_model=ProfileResponse)
def update_profile_by_id(profile_id: int, update: dict, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    print(f"[DEBUG] Updating profile {profile_id} with data: {update}")
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        # Handle partial updates by updating only the fields that are provided
        for field, value in update.items():
            if hasattr(profile, field):
                # Handle special cases for nested objects
                if field == "job_preferences" and value is not None:
                    # Update job_preferences as a JSON object
                    if isinstance(value, dict):
                        setattr(profile, field, value)
                    else:
                        print(f"[DEBUG] Invalid job_preferences format: {type(value)}")
                elif field in ["skills", "languages", "work_experience", "education", "achievements", "certificates"]:
                    # Handle list fields
                    if value is not None:
                        setattr(profile, field, value)
                else:
                    # Handle simple fields
                    setattr(profile, field, value)
            else:
                print(f"[DEBUG] Field {field} not found in Profile model")
        
        db.commit()
        db.refresh(profile)
        print(f"[DEBUG] Profile {profile_id} updated successfully")
        return profile
    except Exception as e:
        print(f"[DEBUG] Error updating profile: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

@app.delete("/profiles/{profile_id}", response_model=DeleteResponse)
def delete_profile(profile_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()
    return DeleteResponse(message="Profile deleted")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 