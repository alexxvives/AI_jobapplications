# Project Plan: Job Automation Platform

A web-based platform that automates job applications in the United States, targeting platforms like LinkedIn, Greenhouse, Ashby, Lever, and others. The platform allows users to search for jobs, automatically apply via Chrome extension, track application status, and generate application content using AI.

## Supported Job Sources (as of 2025)
- **Ashby** (GraphQL API, live scraping)
- **Greenhouse** (Web scraping)
- **Lever** (API + web scraping)

> **Note:** Indeed is not supported due to strong anti-bot protection and lack of a public API. All attempts to scrape Indeed are blocked by Cloudflare. If support is needed in the future, a paid proxy/bypass service (e.g., ScrapFly) would be required.

## MVP Features
- Resume upload and parsing (LLM-powered, Mistral 7B)
- User profile extraction and display
- Unified job search across Ashby, Greenhouse, Lever, and local database
- Chrome extension for auto-apply (Phase 3)
- Application tracking and status updates
- AI-generated application content

## Architecture Overview

| Frontend (Next.js) | Backend (FastAPI) | Database (SQLite/PostgreSQL) | LLM (Mistral 7B via llama-cpp-python) | Job Sources |
|--------------------|-------------------|------------------------------|---------------------------------------|-------------|
| Profile UI         | Auth, Resume Parse| User, Jobs, Profile          | Resume parsing, content gen           | Ashby, Greenhouse, Lever |
| Job Search UI      | Job Search API    | Application status           |                                       |             |
| Application UI     | Chrome Ext API    |                              |                                       |             |

## Phases

### Phase 1: Resume Upload & Profile Extraction
- [x] User can upload a resume (PDF, DOCX, or TXT) via the frontend
- [x] Backend extracts raw text and sends a focused prompt to the Mistral 7B LLM (via llama-cpp-python) for structured parsing
- [x] LLM returns structured JSON with fields: name, phone, location, work experience, education, skills, and languages
- [x] Extracted profile data is stored in the database and displayed in the frontend

### Phase 2: Unified Job Search
- [x] Integrate Ashby, Greenhouse, and Lever job sources for live and database job search
- [x] Unified `/search_all` endpoint with deduplication
- [x] Frontend displays jobs from all sources
- [x] Remove Indeed integration (blocked by anti-bot protection)

### Phase 3: Chrome Extension & Auto-Apply
- [ ] Chrome extension for auto-applying to jobs
- [ ] Application tracking and status updates
- [ ] AI-generated cover letters and application content

## Future Enhancements
- [ ] Add more job sources (if public APIs or reliable scraping is possible)
- [ ] Support for LinkedIn (if API or reliable scraping is available)
- [ ] Integration with paid proxy/bypass services for additional sources (optional)

---

**Current Status:**
- Resume upload, profile extraction, and unified job search (Ashby, Greenhouse, Lever) are complete and working.
- Indeed is not supported due to anti-bot protection.
- Next: Chrome extension and auto-apply features.

## 🎯 Project Overview

A web-based platform that automates job applications in the United States, targeting platforms like LinkedIn, Indeed, ZipRecruiter, and others. The platform allows users to search for jobs, automatically apply via Chrome extension, track application status, and generate application content using AI.

### Core Features
- **Job Search**: Search by title and location with optional filters
- **Automated Applications**: Chrome extension that mimics user actions
- **Application Tracking**: Monitor status (applied, interviewed, rejected)
- **AI Content Generation**: Generate cover letters and form responses using GPT4All
- **User Profile Management**: Resume upload and profile creation

## 🏗️ Architecture & Tech Stack

### Frontend
- **Next.js** (React-based) - Leverages HTML/CSS knowledge, excellent performance
- **Tailwind CSS** - For beautiful, responsive UI
- **TypeScript** - Better development experience (can start with JavaScript)

### Backend
- **Python FastAPI** - Modern, fast, and now decoupled from live scraping.
- **SQLAlchemy** - ORM for database operations
- **Background job fetcher** - Periodically updates the job cache/database.
- **Unified /search endpoint** - Returns jobs from cache/database, not by live-scraping.
- **Optimized for speed and reliability** - Mimics LazyApply's architecture for instant results.

### Database
- **Development**: SQLite (local)
- **Production**: PostgreSQL
- **Management**: pgAdmin or DBeaver (free alternatives to phpMyAdmin)

### Chrome Extension
- **Manifest V3** with vanilla JavaScript
- **Content scripts** for page interaction
- **Background scripts** for API communication

### AI & Automation
- **GPT4All** (local processing) - Privacy-focused
- **Hugging Face** models for specific tasks
- **LangChain** for AI orchestration

### Platform Choice
**Indeed** - Recommended for MVP
- More straightforward automation than LinkedIn
- Better API access
- Less aggressive bot detection
- Good for initial development

## 🔄 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web App       │    │   Chrome        │    │   Backend API   │
│   (Next.js)     │◄──►│   Extension     │◄──►│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         │                                              │
         ▼                                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   AI Service    │    │   Job Scraper   │
│   (SQLite/PostgreSQL) │   (GPT4All)     │    │   (Indeed API)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Core Features (MVP)

### 1. User Profile Management (LazyApply-style)
- Resume upload (PDF parsing)
- Auto-populate profile fields from resume
- Beautiful profile UI with sections:
  - Personal Info
  - Work Experience (from resume)
  - Skills & Education
  - Visa Status
  - Demographics (optional)

### 2. Job Search & Selection
- Search by title + location
- Filters: job type, salary, remote/hybrid
- Job listing with preview
- Bulk selection (select all or individual)
- Save searches for later

### 3. Application Automation
- Chrome extension activation
- One-click apply to selected jobs
- Progress tracking (applied, interviewed, rejected)
- Application history dashboard

### 4. AI Content Generation
- Unique cover letters per job
- Auto-fill application forms
- Smart responses to common questions

## 🗄️ Database Schema

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profiles table  
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    full_name VARCHAR(255),
    current_job VARCHAR(255),
    location VARCHAR(255),
    visa_status VARCHAR(100),
    resume_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job searches
CREATE TABLE job_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255),
    location VARCHAR(255),
    filters TEXT, -- JSON string
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job listings
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255),
    company VARCHAR(255),
    location VARCHAR(255),
    description TEXT,
    salary VARCHAR(100),
    url VARCHAR(500),
    platform VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Applications
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    job_id INTEGER REFERENCES jobs(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, applied, interviewed, rejected
    applied_at TIMESTAMP,
    cover_letter TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📅 Development Phases

### Phase 1: Foundation (2-3 weeks)
- [x] Set up Next.js frontend with Tailwind CSS
- [x] FastAPI backend with SQLite database
- [x] User authentication system
- [x] Basic profile management
- [ ] Resume upload and parsing functionality

### Phase 2: Job Search (2-3 weeks)
- [ ] Indeed API integration
- [ ] Job search interface
- [ ] Job selection and saving functionality
- [ ] Basic job data storage

### Phase 3: Chrome Extension (3-4 weeks)
- [ ] Extension development and setup
- [ ] Page interaction automation
- [ ] Form filling capabilities
- [ ] Communication with backend API

### Phase 4: AI Integration (2-3 weeks)
- [ ] GPT4All setup and configuration
- [ ] Cover letter generation
- [ ] Smart form filling
- [ ] Content customization based on job descriptions

### Phase 5: Polish & Deploy (1-2 weeks)
- [ ] Application tracking dashboard
- [ ] Analytics and statistics
- [ ] Error handling and validation
- [ ] Self-hosted deployment setup

## 🆓 Free Services & Resources

### Development
- **Database**: SQLite (local) → Railway/Neon (free PostgreSQL)
- **File Storage**: Local storage → Cloudinary (free tier)
- **Deployment**: Vercel (frontend, free) + Railway (backend, free tier)
- **AI Models**: GPT4All (local) + Hugging Face (free)

### Tools
- **Database Management**: pgAdmin or DBeaver (free)
- **Version Control**: GitHub (free)
- **Code Editor**: VS Code (free)

## 🎨 UI/UX Design

### Inspiration
- **LazyApply** (https://lazyapply.com/) - Clean, modern interface
- Minimalist design with focus on functionality
- Beautiful profile creation from resume upload
- Intuitive job selection and application process

### Key Design Principles
- Clean, professional appearance
- Mobile-responsive design
- Intuitive navigation
- Clear progress indicators
- Minimal cognitive load

## 🔒 Security Considerations

### Data Protection
- Local AI processing for privacy
- Encrypted password storage
- Secure file upload handling
- API rate limiting

### Chrome Extension Security
- Minimal permissions required
- Secure communication with backend
- No sensitive data stored in extension

## 🚀 Deployment Strategy

### Development
- Local development environment
- SQLite database
- Local file storage

### Production (Future)
- **Frontend**: Vercel or Netlify
- **Backend**: Railway or Heroku
- **Database**: PostgreSQL on Railway/Neon
- **File Storage**: AWS S3 or Cloudinary

## 📊 Key Differentiators from Competitors

1. **Open-source** - Users can self-host and customize
2. **Local AI processing** - Privacy-focused approach
3. **User supervision** - More control over the application process
4. **Customizable** - Adapt to specific user needs
5. **Free tier friendly** - Accessible to all users

## 🎯 Success Metrics

### Technical Metrics
- Application success rate
- AI content quality scores
- System performance and uptime
- User engagement metrics

### Business Metrics
- User adoption rate
- Application-to-interview conversion
- User satisfaction scores
- Platform reliability

## 🔄 Future Enhancements

### Phase 2 Features
- Multiple job platform support
- Advanced analytics dashboard
- Email integration for follow-ups
- Interview scheduling automation

### Phase 3 Features
- Resume optimization suggestions
- Salary negotiation tools
- Networking automation
- Career path recommendations

## 🚀 LazyApply-Style Aggregation & Caching (NEW)

- A **background worker** fetches jobs from all supported job boards (Ashby, Greenhouse, Lever, etc.) for the curated company list every 5 minutes.
- Uses official APIs (JSON endpoints) wherever possible for speed and reliability.
- For boards without APIs, scrapes efficiently and caches results.
- All jobs are stored in a **unified in-memory cache or lightweight database** (e.g., SQLite, Redis, or Python dict with TTL).
- Each job entry includes: `title`, `link`, `jobId`, `snippet`, `jobBoard`, `companyName`, `logo`, etc.
- The **/search API endpoint** returns jobs from this cache instantly, never triggering live scraping.
- Logo URLs and snippets are cached with jobs, fetched only once per cache refresh.
- The frontend consumes this fast, unified endpoint for instant job search results.

### Backend (updated)
- **Python FastAPI** - Modern, fast, and now decoupled from live scraping.
- **Background job fetcher** - Periodically updates the job cache/database.
- **Unified /search endpoint** - Returns jobs from cache/database, not by live-scraping.
- **Optimized for speed and reliability** - Mimics LazyApply's architecture for instant results.

### Frontend (updated)
- **Next.js** - Consumes the unified, fast /search endpoint for job results.
- **No delays from live scraping** - All results are served from the cache/database.

---

*This plan serves as the foundation for developing a comprehensive job application automation platform that prioritizes user privacy, customization, and effectiveness.* 