from sqlalchemy import text
from database import engine

def migrate_profile_fields():
    """Add new profile fields to the users table"""
    with engine.connect() as conn:
        # Add new columns if they don't exist
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR"))
            print("✅ Added phone column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  phone column already exists")
            else:
                print(f"❌ Error adding phone column: {e}")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN skills JSON"))
            print("✅ Added skills column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  skills column already exists")
            else:
                print(f"❌ Error adding skills column: {e}")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN languages JSON"))
            print("✅ Added languages column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  languages column already exists")
            else:
                print(f"❌ Error adding languages column: {e}")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN work_experience JSON"))
            print("✅ Added work_experience column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  work_experience column already exists")
            else:
                print(f"❌ Error adding work_experience column: {e}")
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN education JSON"))
            print("✅ Added education column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  education column already exists")
            else:
                print(f"❌ Error adding education column: {e}")
        
        conn.commit()
        print("🎉 Migration completed!")

if __name__ == "__main__":
    migrate_profile_fields() 