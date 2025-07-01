# Project Details, Notes & Caveats

## 🎯 Project Overview

A web-based platform that automates job applications in the United States, targeting platforms like LinkedIn, Indeed, ZipRecruiter, and others. The platform allows users to search for jobs, automatically apply via Chrome extension, track application status, and generate application content using AI.

## 🎯 MVP Features

### Core Features
- **Job Search**: Search by title and location with optional filters
- **Automated Applications**: Chrome extension that mimics user actions
- **Application Tracking**: Monitor status (applied, interviewed, rejected)
- **AI Content Generation**: Generate cover letters and form responses using Mistral 7B
- **User Profile Management**: Resume upload and profile creation

### User Profile Management (LazyApply-style)
- Resume upload (PDF parsing)
- Auto-populate profile fields from resume
- Beautiful profile UI with sections:
  - Personal Info
  - Work Experience (from resume)
  - Skills & Education
  - Visa Status
  - Demographics (optional)

### Job Search & Selection
- Search by title + location
- Filters: job type, salary, remote/hybrid
- Job listing with preview
- Bulk selection (select all or individual)
- Save searches for later

### Application Automation
- Chrome extension activation
- One-click apply to selected jobs
- Progress tracking (applied, interviewed, rejected)
- Application history dashboard

### AI Content Generation
- Unique cover letters per job
- Auto-fill application forms
- Smart responses to common questions

## 🏗️ Architecture & Tech Stack

### Frontend
- **Next.js** (React-based) - Leverages HTML/CSS knowledge, excellent performance
- **Tailwind CSS** - For beautiful, responsive UI
- **TypeScript** - Better development experience (can start with JavaScript)

### Backend
- **Python FastAPI** - Modern, fast, and now decoupled from live scraping
- **SQLAlchemy** - ORM for database operations
- **Background job fetcher** - Periodically updates the job cache/database
- **Unified /search endpoint** - Returns jobs from cache/database, not by live-scraping
- **Optimized for speed and reliability** - Mimics LazyApply's architecture for instant results

### Database
- **Development**: SQLite (local)
- **Production**: PostgreSQL
- **Management**: pgAdmin or DBeaver (free alternatives to phpMyAdmin)

### Chrome Extension
- **Manifest V3** with vanilla JavaScript
- **Content scripts** for page interaction
- **Background scripts** for API communication

### AI & Automation
- **Mistral 7B** (local processing) - Privacy-focused, via llama-cpp-python
- **Hugging Face** models for specific tasks
- **LangChain** for AI orchestration

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
│   (SQLite/PostgreSQL) │   (Mistral 7B)   │    │   (Background)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Supported Job Sources (as of 2025)

- **Ashby** (GraphQL API, live scraping)
- **Greenhouse** (Web scraping)
- **Lever** (API + web scraping)

> **⚠️ Important Note:** Indeed is not supported due to strong anti-bot protection and lack of a public API. All attempts to scrape Indeed are blocked by Cloudflare. If support is needed in the future, a paid proxy/bypass service (e.g., ScrapFly) would be required.

## 🚀 LazyApply-Style Aggregation & Caching

- A **background worker** fetches jobs from all supported job boards (Ashby, Greenhouse, Lever, etc.) for the curated company list every 5 minutes
- Uses official APIs (JSON endpoints) wherever possible for speed and reliability
- For boards without APIs, scrapes efficiently and caches results
- All jobs are stored in a **unified in-memory cache or lightweight database** (e.g., SQLite, Redis, or Python dict with TTL)
- Each job entry includes: `title`, `link`, `jobId`, `snippet`, `jobBoard`, `companyName`, `logo`, etc.
- The **/search API endpoint** returns jobs from this cache instantly, never triggering live scraping
- Logo URLs and snippets are cached with jobs, fetched only once per cache refresh
- The frontend consumes this fast, unified endpoint for instant job search results

## 🆓 Free Services & Resources

### Development
- **Database**: SQLite (local) → Railway/Neon (free PostgreSQL)
- **File Storage**: Local storage → Cloudinary (free tier)
- **Deployment**: Vercel (frontend, free) + Railway (backend, free tier)
- **AI Models**: Mistral 7B (local) + Hugging Face (free)

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

## 🎯 Platform Choice Considerations

**Indeed** - Was initially recommended for MVP but now removed due to:
- Strong anti-bot protection blocking all scraping attempts
- No public API access
- Cloudflare protection making automation impossible
- Would require paid proxy/bypass services for any future integration

**Current Focus**: Ashby, Greenhouse, and Lever provide sufficient coverage for the MVP with reliable APIs and scraping capabilities.

## 🔄 Current Implementation Status

### Completed Features
- Resume upload, profile extraction, and unified job search (Ashby, Greenhouse, Lever) are complete and working
- User authentication system
- Basic profile management
- Job search interface
- Job selection and saving functionality

### Technical Achievements
- Unified `/search_all` endpoint with deduplication
- Background job fetching and caching system
- LLM-powered resume parsing with Mistral 7B
- Fast, reliable job search without live scraping delays

## 🚧 Known Limitations & Caveats

### Job Source Limitations
- **Indeed**: Completely blocked by anti-bot protection
- **LinkedIn**: No public API, would require complex scraping
- **ZipRecruiter**: Limited API access, would need paid services

### Technical Constraints
- Local AI processing requires sufficient computational resources
- Chrome extension permissions may be limited by browser security policies
- Rate limiting on job board APIs may affect caching frequency

### Future Considerations
- Paid proxy services may be needed for additional job sources
- Advanced AI models may require cloud processing for better performance
- Scaling may require migration from SQLite to PostgreSQL

---

*This project prioritizes user privacy, customization, and effectiveness while working within the constraints of available job board APIs and anti-bot protections.* 