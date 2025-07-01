# Database Schema & SQL Structure

## 🗄️ Database Schema

### Core Tables

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

## Database Technology

### Development
- **SQLite** (local) - For development and testing

### Production
- **PostgreSQL** - For production deployment
- **Management**: pgAdmin or DBeaver (free alternatives to phpMyAdmin)

## Database Features

### Caching Strategy
- **Background worker** fetches jobs from all supported job boards every 5 minutes
- **Unified in-memory cache** or lightweight database (SQLite, Redis, or Python dict with TTL)
- **Logo URLs and snippets** cached with jobs, fetched only once per cache refresh
- **Instant search results** from cache, never triggering live scraping

### Job Data Structure
Each job entry includes:
- `title` - Job title
- `link` - Application URL
- `jobId` - Unique identifier
- `snippet` - Job description preview
- `jobBoard` - Source platform (Ashby, Greenhouse, Lever)
- `companyName` - Company name
- `logo` - Company logo URL

## Database Management

### Free Services
- **Development**: SQLite (local)
- **Production**: Railway/Neon (free PostgreSQL)

### Tools
- **Database Management**: pgAdmin or DBeaver (free)
- **Version Control**: GitHub (free) 