from database import SessionLocal, Job

def delete_all_jobs():
    session = SessionLocal()
    deleted = session.query(Job).delete()
    session.commit()
    session.close()
    print(f"Deleted {deleted} jobs from the database.")

if __name__ == "__main__":
    delete_all_jobs() 