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
from llama_cpp import Llama
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
        setattr(current_user, 'full_name', update.full_name)
    if update.location is not None:
        setattr(current_user, 'location', update.location)
    if update.visa_status is not None:
        setattr(current_user, 'visa_status', update.visa_status)
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
def upload_resume_llm(file: UploadFile = File(...), title: str = Query(None, description="Profile title"), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    print("[DEBUG] /upload_resume_llm called by user:", current_user.email if current_user else None)
    print("[DEBUG] Uploaded file:", file.filename)
    print("[DEBUG] File content type:", file.content_type)
    print("[DEBUG] File size:", file.size if hasattr(file, 'size') else "Unknown")
    
    # Check if filename exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Save uploaded file to a temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix="." + file.filename.split(".")[-1]) as tmp:
        file_content = file.file.read()
        print(f"[DEBUG] File content length: {len(file_content)} bytes")
        print(f"[DEBUG] File content hash: {hash(file_content)}")
        tmp.write(file_content)
        tmp_path = tmp.name
        print(f"[DEBUG] Temporary file created at: {tmp_path}")
    
    # Extract raw text
    try:
        resume_text = extract_text_from_file(tmp_path)
        print(f"[DEBUG] Extracted text length: {len(resume_text)}")
        print(f"[DEBUG] Extracted text hash: {hash(resume_text)}")
        print(f"[DEBUG] First 200 chars: {resume_text[:200]}")
        print(f"[DEBUG] Last 200 chars: {resume_text[-200:]}")
        
        # Calculate approximate token count
        approx_tokens = len(resume_text) // 4
        print(f"[DEBUG] Approximate token count: {approx_tokens} tokens")
        print(f"[DEBUG] Context window size: {config.MODEL_CONTEXT_SIZE} tokens")
    except Exception as e:
        print(f"[DEBUG] Error extracting text: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract text from file: {str(e)}")
    finally:
        try:
            os.remove(tmp_path)
            print(f"[DEBUG] Temporary file removed: {tmp_path}")
        except Exception:
            pass
    
    # Warn if resume is likely too long for the model context window
    max_tokens = 4096  # Reduced from 8192 for faster processing
    approx_token_count = len(resume_text) // 4
    if approx_token_count > max_tokens:
        print(f"[DEBUG] WARNING: Resume is likely too long for the model context window ({approx_token_count} tokens > {max_tokens} tokens). Processing full resume anyway.")
        print(f"[DEBUG] Full resume length: {len(resume_text)} characters")
        # DO NOT truncate - process the full resume
        # resume_text = resume_text[:max_tokens * 4]  # REMOVED - keep full resume

    # DEBUG: Show device info for inference
    DEBUG_SHOW_DEVICE = True  # Set to False to disable device debug print
    device = 0 if torch.cuda.is_available() else -1
    
    # Auto-optimize based on hardware
    if device == 0:  # GPU available
        if config.DEBUG_LLM:
            print(f"[DEBUG] GPU detected: {torch.cuda.get_device_name(0)}")
            print(f"[DEBUG] GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        # Optimize for GPU
        if torch.cuda.get_device_properties(0).total_memory > 8 * 1024**3:  # > 8GB VRAM
            config.MODEL_GPU_LAYERS = 35  # Use all layers on GPU
            config.MODEL_THREADS = 8      # Fewer CPU threads when using GPU
        else:
            config.MODEL_GPU_LAYERS = 20  # Use fewer layers on GPU
            config.MODEL_THREADS = 12     # More CPU threads
    else:  # CPU only
        if config.DEBUG_LLM:
            print("[DEBUG] No GPU detected, using CPU optimization")
        config.MODEL_GPU_LAYERS = 0
        config.MODEL_THREADS = min(16, os.cpu_count() or 8)  # Use available CPU cores
    
    if DEBUG_SHOW_DEVICE:
        print("\n" + "="*80)
        print(f"[DEBUG] INFERENCE DEVICE: {'GPU (cuda)' if device == 0 else 'CPU'}")
        if device == 0:
            print(f"[DEBUG] CUDA device count: {torch.cuda.device_count()}")
            print(f"[DEBUG] CUDA device name: {torch.cuda.get_device_name(0)}")
            print(f"[DEBUG] GPU layers: {config.MODEL_GPU_LAYERS}")
        print(f"[DEBUG] CPU threads: {config.MODEL_THREADS}")
        print(f"[DEBUG] Context size: {config.MODEL_CONTEXT_SIZE}")
        print("="*80 + "\n")

    # Update the LLM prompt to explicitly forbid comments or extra text
    prompt = f"""Extract from this resume and return as valid JSON with these fields. Output strictly valid JSON only:

- first_name
- last_name
- email
- phone
- work_experience (array of jobs: title, company, location, start_date, end_date, description)
- education (array of education: degree, school, year)
- skills (array of objects: name, years)
- languages (array of strings)
- job_preferences (object with linkedin, github, portfolio, etc.)

Resume: {resume_text}
JSON:"""
    
    # Print the prompt before silencing
    if config.DEBUG_LLM:
        print("\n" + "="*80)
        print("[DEBUG] EXACT PROMPT SENT TO LLM:")
        print("="*80)
        print(prompt)
        print("="*80)
        print("[DEBUG] END OF PROMPT")
        print("="*80)

    # Use the Mistral-7B Instruct v0.3 model (32k context)
    if config.DEBUG_LLM:
        print(f"[DEBUG] Attempting to load Mistral-7B v0.3 GGUF model with llama-cpp-python: {config.MODEL_PATH}")

    # Only silence the model's output
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if config.DEBUG_LLM:
                print("[DEBUG] Creating Llama model instance...")
            llm = get_llm_model()
            if config.DEBUG_LLM:
                print("[DEBUG] Model loaded successfully, calling LLM...")
            
            # Add timeout to prevent hanging
            import signal
            import threading
            import time
            
            result = None
            error = None
            generation_time = 0  # Initialize timing variables
            total_llm_time = 0
            
            def llm_call():
                nonlocal result, error, generation_time, total_llm_time
                try:
                    llm_start_time = time.time()
                    if config.DEBUG_LLM:
                        print("[DEBUG] Starting LLM generation...")
                        print(f"[DEBUG] Resume text length: {len(resume_text)} characters")
                        print(f"[DEBUG] Prompt length: {len(prompt)} characters")
                        print(f"[DEBUG] LLM generation started at: {time.strftime('%H:%M:%S')}")
                    
                    # Optimize LLM parameters for faster processing
                    generation_start_time = time.time()
                    result = llm(
                        prompt, 
                        max_tokens=8192,  # Set explicit high token limit
                        stop=["\nJSON:"],  # Stop at JSON marker
                        echo=False,        # Don't echo input
                        temperature=0.05,  # Lower temperature for more focused/faster output
                        top_p=0.8,         # Lower top_p for faster generation
                        repeat_penalty=1.05,  # Lower penalty for speed
                        top_k=40,          # Add top_k for faster sampling
                        tfs_z=0.95,        # Add tail free sampling for speed
                        mirostat_mode=0,   # Disable mirostat for speed
                        mirostat_tau=5.0,
                        mirostat_eta=0.1
                    )
                    generation_end_time = time.time()
                    generation_time = generation_end_time - generation_start_time
                    
                    llm_end_time = time.time()
                    total_llm_time = llm_end_time - llm_start_time
                    
                    if config.DEBUG_LLM:
                        print(f"[DEBUG] LLM generation completed successfully!")
                        print(f"[DEBUG] Generation time: {generation_time:.2f} seconds")
                        print(f"[DEBUG] Total LLM processing time: {total_llm_time:.2f} seconds")
                        print(f"[DEBUG] LLM generation completed at: {time.strftime('%H:%M:%S')}")
                except Exception as e:
                    error = e
                    error_time = time.time()
                    if config.DEBUG_LLM:
                        print(f"[DEBUG] LLM generation failed after {error_time - llm_start_time:.2f} seconds")
                        print(f"[DEBUG] Error: {e}")
            
            # Run LLM call in a thread with timeout
            thread = threading.Thread(target=llm_call)
            thread.daemon = True
            thread.start()
            
            # Wait for LLM response without timeout - just track timing
            start_time = time.time()
            if config.DEBUG_LLM:
                print(f"[DEBUG] Starting LLM processing at {time.strftime('%H:%M:%S')}...")
                print(f"[DEBUG] No timeout limit - will wait for completion")
            
            # Progress reporting during wait
            last_report_time = start_time
            while thread.is_alive():
                current_time = time.time()
                elapsed = int(current_time - start_time)
                
                # Report progress every 30 seconds
                if current_time - last_report_time >= 30:
                    if config.DEBUG_LLM:
                        print(f"[DEBUG] Still processing... ({elapsed}s elapsed, {time.strftime('%H:%M:%S')})")
                    last_report_time = current_time
                
                time.sleep(1)
            
            # LLM processing completed
            end_time = time.time()
            total_time = end_time - start_time
            
            if config.DEBUG_LLM:
                print(f"[DEBUG] LLM processing completed!")
                print(f"[DEBUG] Total processing time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
                print(f"[DEBUG] Started at: {time.strftime('%H:%M:%S', time.localtime(start_time))}")
                print(f"[DEBUG] Completed at: {time.strftime('%H:%M:%S', time.localtime(end_time))}")
            
            if error:
                if config.DEBUG_LLM:
                    print(f"[DEBUG] LLM call failed with error: {error}")
                raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(error)}")
            
            if result is None:
                if config.DEBUG_LLM:
                    print("[DEBUG] LLM call returned None")
                raise HTTPException(status_code=500, detail="LLM returned no response")
                
    except Exception as e:
        if config.DEBUG_LLM:
            print(f"[DEBUG] Exception during LLM processing: {e}")
        raise HTTPException(status_code=500, detail=f"LLM processing error: {str(e)}")

    # Print the raw output after silencing
    parsing_start_time = time.time()
    if config.DEBUG_LLM:
        print("\n" + "="*80)
        print("[DEBUG] RAW OUTPUT FROM LLM:")
        print("="*80)
        print(result)
        print("="*80)
        print("[DEBUG] END OF LLM OUTPUT")
        print("="*80)
        print(f"[DEBUG] Starting JSON parsing at {time.strftime('%H:%M:%S')}...")
    
    # Handle the response based on the actual structure
    if hasattr(result, 'choices') and result.choices:
        output = result.choices[0].text
    elif hasattr(result, 'text'):
        output = result.text
    elif isinstance(result, dict) and 'choices' in result:
        output = result['choices'][0]['text']
    else:
        output = str(result)
    
    if config.DEBUG_LLM:
        print(f"[DEBUG] Raw output length: {len(output)} characters")
        print(f"[DEBUG] Raw output type: {type(output)}")
    
    # MULTIPLE LAYERS OF JSON CLEANING AND PARSING
    profile_json = None
    parsing_attempts = []
    
    # Attempt 1: Direct parsing (in case LLM returned clean JSON)
    try:
        profile_json = pyjson.loads(output.strip())
        if config.DEBUG_LLM:
            print("[DEBUG] SUCCESS: Direct JSON parsing worked!")
        parsing_attempts.append("Direct parsing - SUCCESS")
    except Exception as e:
        parsing_attempts.append(f"Direct parsing - FAILED: {e}")
        if config.DEBUG_LLM:
            print(f"[DEBUG] Direct parsing failed: {e}")
    
    # Attempt 2: Basic cleaning then parsing
    if profile_json is None:
        try:
            cleaned_output = output
            
            # Remove Markdown code block markers more thoroughly
            cleaned_output = re.sub(r'```json\s*', '', cleaned_output, flags=re.IGNORECASE)
            cleaned_output = re.sub(r'```\s*', '', cleaned_output)
            cleaned_output = re.sub(r'^\s*```\s*$', '', cleaned_output, flags=re.MULTILINE)
            
            # Remove all comment lines (lines containing //, even if indented)
            cleaned_output = re.sub(r'^\s*//.*$', '', cleaned_output, flags=re.MULTILINE)
            
            # Remove trailing commas before closing brackets/braces
            cleaned_output = re.sub(r',\s*([}\]])', r'\1', cleaned_output)
            
            # Strip whitespace
            cleaned_output = cleaned_output.strip()
            
            if config.DEBUG_LLM:
                print(f"[DEBUG] After cleaning, length: {len(cleaned_output)} characters")
                print(f"[DEBUG] First 200 chars of cleaned output: {cleaned_output[:200]}")
                print(f"[DEBUG] Last 200 chars of cleaned output: {cleaned_output[-200:]}")
            
            profile_json = pyjson.loads(cleaned_output)
            if config.DEBUG_LLM:
                print("[DEBUG] SUCCESS: Basic cleaning + parsing worked!")
            parsing_attempts.append("Basic cleaning + parsing - SUCCESS")
        except Exception as e:
            parsing_attempts.append(f"Basic cleaning + parsing - FAILED: {e}")
            if config.DEBUG_LLM:
                print(f"[DEBUG] Basic cleaning + parsing failed: {e}")
    
    # Attempt 3: Extract JSON from first { to last }
    if profile_json is None:
        try:
            cleaned_output = output
            
            # Remove Markdown code block markers
            cleaned_output = re.sub(r'```json\s*', '', cleaned_output, flags=re.IGNORECASE)
            cleaned_output = re.sub(r'```\s*', '', cleaned_output)
            cleaned_output = re.sub(r'^\s*```\s*$', '', cleaned_output, flags=re.MULTILINE)
            cleaned_output = re.sub(r'^\s*//.*$', '', cleaned_output, flags=re.MULTILINE)
            cleaned_output = re.sub(r',\s*([}\]])', r'\1', cleaned_output)
            cleaned_output = cleaned_output.strip()
            
            # Extract the largest JSON object (from first { to last })
            json_start = cleaned_output.find('{')
            json_end = cleaned_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                cleaned_output = cleaned_output[json_start:json_end]
                if config.DEBUG_LLM:
                    print(f"[DEBUG] Extracted JSON from position {json_start} to {json_end}")
                    print(f"[DEBUG] Final JSON length: {len(cleaned_output)} characters")
                
                # Try to complete incomplete JSON by counting braces and brackets
                open_braces = cleaned_output.count('{')
                close_braces = cleaned_output.count('}')
                open_brackets = cleaned_output.count('[')
                close_brackets = cleaned_output.count(']')
                
                if config.DEBUG_LLM:
                    print(f"[DEBUG] Brace count: {open_braces} open, {close_braces} close")
                    print(f"[DEBUG] Bracket count: {open_brackets} open, {close_brackets} close")
                
                # Add missing closing braces/brackets
                missing_braces = open_braces - close_braces
                missing_brackets = open_brackets - close_brackets
                
                if missing_braces > 0 or missing_brackets > 0:
                    if config.DEBUG_LLM:
                        print(f"[DEBUG] Adding {missing_brackets} closing brackets and {missing_braces} closing braces")
                    cleaned_output += ']' * missing_brackets + '}' * missing_braces
            else:
                if config.DEBUG_LLM:
                    print(f"[DEBUG] No JSON braces found! json_start={json_start}, json_end={json_end}")
                raise ValueError("No JSON braces found")
            
            profile_json = pyjson.loads(cleaned_output)
            if config.DEBUG_LLM:
                print("[DEBUG] SUCCESS: JSON extraction + parsing worked!")
            parsing_attempts.append("JSON extraction + parsing - SUCCESS")
        except Exception as e:
            parsing_attempts.append(f"JSON extraction + parsing - FAILED: {e}")
            if config.DEBUG_LLM:
                print(f"[DEBUG] JSON extraction + parsing failed: {e}")
    
    # Attempt 4: Aggressive cleaning - remove everything except JSON-like content
    if profile_json is None:
        try:
            cleaned_output = output
            
            # Remove ALL potential problematic content
            cleaned_output = re.sub(r'```.*?```', '', cleaned_output, flags=re.DOTALL)  # Remove complete code blocks
            cleaned_output = re.sub(r'```.*', '', cleaned_output, flags=re.DOTALL)  # Remove incomplete code blocks
            cleaned_output = re.sub(r'^\s*//.*$', '', cleaned_output, flags=re.MULTILINE)  # Remove comments
            cleaned_output = re.sub(r'^\s*#.*$', '', cleaned_output, flags=re.MULTILINE)  # Remove markdown headers
            cleaned_output = re.sub(r'^\s*\*.*$', '', cleaned_output, flags=re.MULTILINE)  # Remove markdown lists
            cleaned_output = re.sub(r'^\s*-.*$', '', cleaned_output, flags=re.MULTILINE)  # Remove markdown lists
            cleaned_output = re.sub(r'^\s*\d+\.\s.*$', '', cleaned_output, flags=re.MULTILINE)  # Remove numbered lists
            
            # Find JSON content
            json_start = cleaned_output.find('{')
            json_end = cleaned_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                cleaned_output = cleaned_output[json_start:json_end]
                
                # Fix common JSON issues
                cleaned_output = re.sub(r',\s*([}\]])', r'\1', cleaned_output)  # Remove trailing commas
                cleaned_output = re.sub(r',\s*,', ',', cleaned_output)  # Remove double commas
                cleaned_output = re.sub(r'}\s*{', '},{', cleaned_output)  # Fix object concatenation
                
                profile_json = pyjson.loads(cleaned_output)
                if config.DEBUG_LLM:
                    print("[DEBUG] SUCCESS: Aggressive cleaning + parsing worked!")
                parsing_attempts.append("Aggressive cleaning + parsing - SUCCESS")
            else:
                raise ValueError("No JSON content found after aggressive cleaning")
        except Exception as e:
            parsing_attempts.append(f"Aggressive cleaning + parsing - FAILED: {e}")
            if config.DEBUG_LLM:
                print(f"[DEBUG] Aggressive cleaning + parsing failed: {e}")
    
    # Attempt 5: Manual JSON reconstruction (last resort)
    if profile_json is None:
        try:
            if config.DEBUG_LLM:
                print("[DEBUG] Attempting manual JSON reconstruction...")
            
            # Try to extract key-value pairs manually
            extracted_data = {}
            
            # Extract basic fields using regex
            patterns = {
                'first_name': r'"first_name"\s*:\s*"([^"]*)"',
                'last_name': r'"last_name"\s*:\s*"([^"]*)"',
                'email': r'"email"\s*:\s*"([^"]*)"',
                'phone': r'"phone"\s*:\s*"([^"]*)"',
                'country': r'"country"\s*:\s*"([^"]*)"',
                'citizenship': r'"citizenship"\s*:\s*"([^"]*)"',
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    extracted_data[field] = match.group(1)
                else:
                    extracted_data[field] = None
            
            # Try to extract work experience array
            work_exp_match = re.search(r'"work_experience"\s*:\s*\[(.*?)\]', output, re.DOTALL)
            work_experience = []
            if work_exp_match:
                work_exp_text = work_exp_match.group(1)
                # Simple extraction of work experience objects
                job_matches = re.findall(r'\{[^}]*"title"[^}]*\}', work_exp_text, re.DOTALL)
                for job_text in job_matches:
                    job = {}
                    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', job_text)
                    if title_match:
                        job['title'] = title_match.group(1)
                    company_match = re.search(r'"company"\s*:\s*"([^"]*)"', job_text)
                    if company_match:
                        job['company'] = company_match.group(1)
                    location_match = re.search(r'"location"\s*:\s*"([^"]*)"', job_text)
                    if location_match:
                        job['location'] = location_match.group(1)
                    start_match = re.search(r'"start_date"\s*:\s*"([^"]*)"', job_text)
                    if start_match:
                        job['start_date'] = start_match.group(1)
                    end_match = re.search(r'"end_date"\s*:\s*"([^"]*)"', job_text)
                    if end_match:
                        job['end_date'] = end_match.group(1)
                    if job:
                        work_experience.append(job)
            
            # Try to extract education array
            education_match = re.search(r'"education"\s*:\s*\[(.*?)\]', output, re.DOTALL)
            education = []
            if education_match:
                edu_text = education_match.group(1)
                edu_matches = re.findall(r'\{[^}]*"degree"[^}]*\}', edu_text, re.DOTALL)
                for edu_text in edu_matches:
                    edu = {}
                    degree_match = re.search(r'"degree"\s*:\s*"([^"]*)"', edu_text)
                    if degree_match:
                        edu['degree'] = degree_match.group(1)
                    school_match = re.search(r'"school"\s*:\s*"([^"]*)"', edu_text)
                    if school_match:
                        edu['school'] = school_match.group(1)
                    year_match = re.search(r'"year"\s*:\s*"([^"]*)"', edu_text)
                    if year_match:
                        edu['year'] = year_match.group(1)
                    if edu:
                        education.append(edu)
            
            # Try to extract skills array
            skills_match = re.search(r'"skills"\s*:\s*\[(.*?)\]', output, re.DOTALL)
            skills = []
            if skills_match:
                skills_text = skills_match.group(1)
                skill_matches = re.findall(r'\{[^}]*"name"[^}]*\}', skills_text, re.DOTALL)
                for skill_text in skill_matches:
                    skill = {}
                    name_match = re.search(r'"name"\s*:\s*"([^"]*)"', skill_text)
                    if name_match:
                        skill['name'] = name_match.group(1)
                    years_match = re.search(r'"years"\s*:\s*(\d+)', skill_text)
                    if years_match:
                        skill['years'] = years_match.group(1)
                    if skill:
                        skills.append(skill)
            
            # Try to extract languages array
            languages_match = re.search(r'"languages"\s*:\s*\[(.*?)\]', output, re.DOTALL)
            languages = []
            if languages_match:
                languages_text = languages_match.group(1)
                # Extract simple string languages
                lang_matches = re.findall(r'"([^"]*)"', languages_text)
                languages = lang_matches
            
            # Try to extract job_preferences object
            job_prefs_match = re.search(r'"job_preferences"\s*:\s*\{(.*?)\}', output, re.DOTALL)
            job_preferences = {}
            if job_prefs_match:
                prefs_text = job_prefs_match.group(1)
                # Extract key-value pairs
                kv_matches = re.findall(r'"([^\"]*)"\s*:\s*"([^\"]*)"', prefs_text)
                for key, value in kv_matches:
                    if key not in ["current_salary", "expected_salary", "current_salary_currency", "expected_salary_currency"]:
                        job_preferences[key] = value
            
            # Create comprehensive JSON with extracted data
            profile_json = {
                "first_name": extracted_data.get('first_name', ''),
                "last_name": extracted_data.get('last_name', ''),
                "email": extracted_data.get('email', ''),
                "phone": extracted_data.get('phone', ''),
                "image_url": None,
                "address": None,
                "city": None,
                "state": None,
                "zip_code": None,
                "country": extracted_data.get('country', ''),
                "citizenship": extracted_data.get('citizenship', ''),
                "gender": None,
                "work_experience": work_experience,
                "education": education,
                "skills": skills,
                "languages": languages,
                "job_preferences": job_preferences,
                "achievements": [],
                "certificates": []
            }
            
            if config.DEBUG_LLM:
                print("[DEBUG] SUCCESS: Manual JSON reconstruction worked!")
                print(f"[DEBUG] Extracted {len(work_experience)} work experiences")
                print(f"[DEBUG] Extracted {len(education)} education entries")
                print(f"[DEBUG] Extracted {len(skills)} skills")
                print(f"[DEBUG] Extracted {len(languages)} languages")
            parsing_attempts.append("Manual JSON reconstruction - SUCCESS")
        except Exception as e:
            parsing_attempts.append(f"Manual JSON reconstruction - FAILED: {e}")
            if config.DEBUG_LLM:
                print(f"[DEBUG] Manual JSON reconstruction failed: {e}")
    
    # FINAL CHECK - If all attempts failed
    if profile_json is None:
        if config.DEBUG_LLM:
            print("\n" + "="*80)
            print("[DEBUG] ALL JSON PARSING ATTEMPTS FAILED!")
            print("="*80)
            print("Parsing attempts:")
            for i, attempt in enumerate(parsing_attempts, 1):
                print(f"  {i}. {attempt}")
            print("\nRaw LLM output:")
            print("="*80)
            print(output)
            print("="*80)
        
        # Return a minimal valid profile instead of crashing
        profile_json = {
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "image_url": None,
            "address": None,
            "city": None,
            "state": None,
            "zip_code": None,
            "country": None,
            "citizenship": None,
            "gender": None,
            "work_experience": [],
            "education": [],
            "skills": [],
            "languages": [],
            "job_preferences": {},
            "achievements": [],
            "certificates": []
        }
        
        if config.DEBUG_LLM:
            print("[DEBUG] Using fallback empty profile to prevent crash")
    
    if config.DEBUG_LLM:
        print(f"[DEBUG] Final profile_json keys: {list(profile_json.keys())}")
        print(f"[DEBUG] Profile contains {len(profile_json.get('work_experience', []))} work experiences")
        print(f"[DEBUG] Profile contains {len(profile_json.get('education', []))} education entries")
        print(f"[DEBUG] Profile contains {len(profile_json.get('skills', []))} skills")
    
    # Final timing summary
    parsing_end_time = time.time()
    total_parsing_time = parsing_end_time - parsing_start_time
    if config.DEBUG_LLM:
        print(f"[DEBUG] JSON parsing completed!")
        print(f"[DEBUG] JSON parsing time: {total_parsing_time:.2f} seconds")
        print(f"[DEBUG] JSON parsing completed at: {time.strftime('%H:%M:%S')}")
        print("="*80)
        print("[DEBUG] TIMING SUMMARY:")
        print("="*80)
        print(f"[DEBUG] Total processing time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        print(f"[DEBUG] LLM generation time: {generation_time:.2f} seconds")
        print(f"[DEBUG] JSON parsing time: {total_parsing_time:.2f} seconds")
        print(f"[DEBUG] Other overhead: {total_time - generation_time - total_parsing_time:.2f} seconds")
        print("="*80)
    
    # Check if current_user is valid
    if not current_user:
        raise HTTPException(status_code=401, detail="User authentication failed. Please log in again.")
    
    if not hasattr(current_user, 'id') or current_user.id is None:
        raise HTTPException(status_code=401, detail="Invalid user session. Please log in again.")
    
    # Extract resume email for comparison and logging
    resume_email = None
    
    if config.DEBUG_LLM:
        print(f"[DEBUG] Starting split extraction approach...")
        print(f"[DEBUG] Resume text length: {len(resume_text)} characters")
    
    # Get the LLM model
    llm = get_llm_model()
    
    # Extract each section individually
    sections = [
        "personal_info",
        "job_preferences", 
        "work_experience",
        "education",
        "skills",
        "languages",
        "certificates"
    ]
    
    profile_json = {}
    
    for section in sections:
        if config.DEBUG_LLM:
            print(f"\n[DEBUG] ========================================")
            print(f"[DEBUG] EXTRACTING SECTION: {section.upper()}")
            print(f"[DEBUG] ========================================")
        
        section_data = extract_section_from_resume(resume_text, section, llm)
        
        if section_data:
            profile_json.update(section_data)
            if config.DEBUG_LLM:
                print(f"[DEBUG] {section} data: {section_data}")
        else:
            if config.DEBUG_LLM:
                print(f"[DEBUG] {section} extraction failed or returned empty")
    
    # Extract resume email from personal_info if available
    if "email" in profile_json:
        resume_email = profile_json["email"]
    
    if config.DEBUG_LLM:
        print(f"\n[DEBUG] ========================================")
        print(f"[DEBUG] FINAL COMBINED PROFILE")
        print(f"[DEBUG] ========================================")
        print(f"[DEBUG] Profile keys: {list(profile_json.keys())}")
        print(f"[DEBUG] Work experiences: {len(profile_json.get('work_experience', []))}")
        print(f"[DEBUG] Education entries: {len(profile_json.get('education', []))}")
        print(f"[DEBUG] Skills: {len(profile_json.get('skills', []))}")
        print(f"[DEBUG] Languages: {len(profile_json.get('languages', []))}")
        print(f"[DEBUG] Job preferences keys: {list(profile_json.get('job_preferences', {}).keys())}")
    
    # Ensure all required fields exist
    required_fields = [
        "first_name", "last_name", "email", "phone", "image_url", "address", "city", 
        "state", "zip_code", "country", "citizenship", "gender", "work_experience", 
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
        # Create or update a Profile instead of updating the User directly
        # First, try to find an existing profile for this user
        existing_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        
        if existing_profile:
            if config.DEBUG_LLM:
                print(f"[DEBUG] Found existing profile (ID: {existing_profile.id}), updating it...")
            profile = existing_profile
        else:
            if config.DEBUG_LLM:
                print(f"[DEBUG] No existing profile found, creating new profile...")
            profile = Profile(user_id=current_user.id)
            db.add(profile)
        
        # Update profile fields with resume data
        profile_fields = [
            ('title', 'title'),  # Add title field
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
            ('email', 'email'),  # This will store the resume email
            ('phone', 'phone'),
            ('image_url', 'image_url'),
            ('address', 'address'),
            ('city', 'city'),
            ('state', 'state'),
            ('zip_code', 'zip_code'),
            ('country', 'country'),
            ('citizenship', 'citizenship'),
            ('gender', 'gender'),
            ('skills', 'skills'),
            ('languages', 'languages'),
            ('work_experience', 'work_experience'),
            ('job_preferences', 'job_preferences'),
            ('achievements', 'achievements'),
            ('certificates', 'certificates'),
        ]
        
        for profile_field, json_field in profile_fields:
            if profile_field == 'title':
                # Use the title parameter from the request, or fall back to a default
                setattr(profile, profile_field, title or "Resume Profile")
            else:
                setattr(profile, profile_field, profile_json.get(json_field, None))
        
        # Special handling for full_name - combine first_name and last_name
        first_name = profile_json.get('first_name', '')
        last_name = profile_json.get('last_name', '')
        if first_name or last_name:
            full_name = f"{first_name} {last_name}".strip()
            profile.full_name = full_name if full_name else None
        else:
            profile.full_name = None
        
        # Special handling for education
        education_data = profile_json.get("education", None)
        if education_data is not None:
            if isinstance(education_data, list):
                valid_education = []
                for edu in education_data:
                    if isinstance(edu, dict) and edu.get("school"):
                        if not edu.get("degree"):
                            edu["degree"] = "Education at " + edu["school"]
                        valid_education.append(edu)
                profile.education = valid_education
            else:
                profile.education = education_data
        else:
            profile.education = None
        
        if config.DEBUG_LLM:
            print(f"[DEBUG] Successfully updated profile data")
            print(f"[DEBUG] User account email remains: {current_user.email}")
            print(f"[DEBUG] Profile email (for job applications): {profile.email}")
            print(f"[DEBUG] Committing to database...")
        
        db.commit()
        db.refresh(profile)
        
        if config.DEBUG_LLM:
            print(f"[DEBUG] Database commit successful!")
            print(f"[DEBUG] Profile saved with ID: {profile.id}")
            print(f"[DEBUG] Returning UserResponse...")
        
        # Return the user data (not the profile data) to maintain API compatibility
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        if config.DEBUG_LLM:
            print(f"[DEBUG] ERROR saving profile data: {e}")
            print(f"[DEBUG] Error type: {type(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save profile data: {str(e)}")

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
def update_profile_by_id(profile_id: int, update: ProfileUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for k, v in update.dict(exclude_unset=True).items():
        setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return profile

@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()
    return {"message": "Profile deleted"} 

# Global model cache
_llm_model = None
_model_lock = threading.Lock()

def get_llm_model():
    """Get or create the LLM model instance with caching"""
    global _llm_model
    with _model_lock:
        if _llm_model is None:
            if config.DEBUG_LLM:
                print(f"[DEBUG] Loading LLM model for the first time...")
            _llm_model = Llama(
                model_path=config.MODEL_PATH,
                n_ctx=config.MODEL_CONTEXT_SIZE,
                n_threads=config.MODEL_THREADS,
                n_gpu_layers=config.MODEL_GPU_LAYERS,
                verbose=False,  # Disable verbose output
                n_batch=512,    # Increase batch size for speed
                use_mmap=True,  # Use memory mapping for faster loading
                use_mlock=False, # Disable memory locking for speed
                seed=42         # Fixed seed for consistent results
            )
            if config.DEBUG_LLM:
                print(f"[DEBUG] LLM model loaded successfully!")
        return _llm_model 

def extract_section_from_resume(resume_text: str, section_name: str, llm_model) -> dict:
    """Extract a specific section from resume using a focused LLM call"""
    
    section_prompts = {
        "personal_info": f"""Extract personal information from this resume and return as valid JSON. Output strictly valid JSON only:

- first_name
- last_name
- email
- phone
- image_url
- address
- city
- state
- zip_code
- country
- citizenship
- gender

Resume: {resume_text}
JSON:""",

        "job_preferences": f"""Extract job preferences and professional information from this resume and return as valid JSON. Output strictly valid JSON only:

- linkedin
- twitter
- github
- portfolio
- other_url
- notice_period
- total_experience
- default_experience
- highest_education
- companies_to_exclude
- willing_to_relocate
- driving_license
- visa_requirement
- race_ethnicity

Resume: {resume_text}
JSON:""",

        "work_experience": f"""Extract work experience from this resume and return as valid JSON. Output strictly valid JSON only:

- work_experience (array of jobs with: title, company, location, start_date, end_date, description, bullets)

Resume: {resume_text}
JSON:""",

        "education": f"""Extract education from this resume and return as valid JSON. Output strictly valid JSON only:

- education (array of education entries with: degree, school, year)

Resume: {resume_text}
JSON:""",

        "skills": f"""Extract skills from this resume and return as valid JSON. Output strictly valid JSON only:

- skills (array of objects with: name, years)

Resume: {resume_text}
JSON:""",

        "languages": f"""Extract languages from this resume and return as valid JSON. Output strictly valid JSON only:

- languages (array of strings)

Resume: {resume_text}
JSON:""",

        "certificates": f"""Extract certificates and achievements from this resume and return as valid JSON. Output strictly valid JSON only:

- certificates (array of strings)
- achievements (array of strings - include awards, honors, recognitions)

Resume: {resume_text}
JSON:"""
    }
    
    if section_name not in section_prompts:
        return {}
    
    prompt = section_prompts[section_name]
    
    if config.DEBUG_LLM:
        print(f"\n[DEBUG] Extracting {section_name}...")
        print(f"[DEBUG] {section_name} prompt length: {len(prompt)} characters")
    
    try:
        # Call LLM with focused prompt
        result = llm_model(
            prompt,
            max_tokens=2048,  # Reasonable limit for each section
            stop=["\nJSON:"],
            echo=False,
            temperature=0.05,
            top_p=0.8,
            repeat_penalty=1.05,
            top_k=40,
            tfs_z=0.95,
            mirostat_mode=0,
            mirostat_tau=5.0,
            mirostat_eta=0.1
        )
        
        # Extract the text from the result
        if hasattr(result, 'choices') and result.choices:
            output = result.choices[0].text
        elif hasattr(result, 'text'):
            output = result.text
        elif isinstance(result, dict) and 'choices' in result:
            output = result['choices'][0]['text']
        else:
            output = str(result)
        
        if config.DEBUG_LLM:
            print(f"[DEBUG] {section_name} raw output length: {len(output)} characters")
            print(f"[DEBUG] {section_name} output: {output[:200]}...")
        
        # Clean and parse the JSON
        cleaned_output = output.strip()
        
        # Remove Markdown code blocks
        cleaned_output = re.sub(r'```json\s*', '', cleaned_output, flags=re.IGNORECASE)
        cleaned_output = re.sub(r'```\s*', '', cleaned_output)
        cleaned_output = re.sub(r'^\s*```\s*$', '', cleaned_output, flags=re.MULTILINE)
        
        # Remove comments and trailing commas
        cleaned_output = re.sub(r'^\s*//.*$', '', cleaned_output, flags=re.MULTILINE)
        cleaned_output = re.sub(r',\s*([}\]])', r'\1', cleaned_output)
        
        # Try to parse the JSON
        try:
            section_data = pyjson.loads(cleaned_output)
            if config.DEBUG_LLM:
                print(f"[DEBUG] {section_name} parsed successfully!")
            return section_data
        except Exception as e:
            if config.DEBUG_LLM:
                print(f"[DEBUG] {section_name} JSON parsing failed: {e}")
                print(f"[DEBUG] {section_name} cleaned output: {cleaned_output}")
            return {}
            
    except Exception as e:
        if config.DEBUG_LLM:
            print(f"[DEBUG] {section_name} LLM call failed: {e}")
        return {}