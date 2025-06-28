from database import SessionLocal, Job

def check_stripe_in_db():
    session = SessionLocal()
    found = any(j.company.lower() == 'stripe' for j in session.query(Job).all())
    session.close()
    print(f"Is Stripe in the database? {found}")

if __name__ == "__main__":
    check_stripe_in_db() 