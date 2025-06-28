from database import SessionLocal, Job

def check_database():
    db = SessionLocal()
    try:
        total_jobs = db.query(Job).count()
        print(f"Total jobs in database: {total_jobs}")
        
        if total_jobs > 0:
            # Get some sample jobs
            sample_jobs = db.query(Job).limit(3).all()
            print("\nSample jobs:")
            for job in sample_jobs:
                print(f"- {job.title} at {job.company}")
        
        # Get unique companies
        companies = db.query(Job.company).distinct().all()
        print(f"\nUnique companies: {len(companies)}")
        for company in companies[:5]:  # Show first 5
            print(f"- {company[0]}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_database() 