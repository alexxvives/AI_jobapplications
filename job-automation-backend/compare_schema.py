import sqlite3
from models import Profile
from schemas import ProfileCreate, ProfileResponse

def compare_schema():
    print("=== SCHEMA COMPARISON ===\n")
    
    # Get database columns
    db_path = "job_automation.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(profiles)")
    db_columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    
    print(f"Database columns ({len(db_columns)}): {db_columns}")
    
    # Get SQLAlchemy model columns
    model_columns = [column.name for column in Profile.__table__.columns]
    print(f"\nSQLAlchemy model columns ({len(model_columns)}): {model_columns}")
    
    # Get Pydantic schema fields
    schema_fields = list(ProfileCreate.__fields__.keys())
    print(f"\nPydantic ProfileCreate fields ({len(schema_fields)}): {schema_fields}")
    
    # Check for missing fields in database
    missing_in_db = set(model_columns) - set(db_columns)
    if missing_in_db:
        print(f"\n❌ MISSING IN DATABASE: {missing_in_db}")
    else:
        print(f"\n✅ All model columns exist in database")
    
    # Check for extra fields in database
    extra_in_db = set(db_columns) - set(model_columns)
    if extra_in_db:
        print(f"\n⚠️  EXTRA IN DATABASE: {extra_in_db}")
    else:
        print(f"\n✅ No extra fields in database")
    
    # Check for missing fields in schema
    missing_in_schema = set(model_columns) - set(schema_fields)
    if missing_in_schema:
        print(f"\n❌ MISSING IN SCHEMA: {missing_in_schema}")
    else:
        print(f"\n✅ All model fields exist in schema")
    
    # Check for extra fields in schema
    extra_in_schema = set(schema_fields) - set(model_columns)
    if extra_in_schema:
        print(f"\n⚠️  EXTRA IN SCHEMA: {extra_in_schema}")
    else:
        print(f"\n✅ No extra fields in schema")
    
    # Check ProfileResponse specific fields
    response_fields = list(ProfileResponse.__fields__.keys())
    response_only_fields = set(response_fields) - set(schema_fields)
    if response_only_fields:
        print(f"\n📋 ProfileResponse only fields: {response_only_fields}")
    
    print("\n=== FIELD ANALYSIS ===")
    
    # Analyze each field type
    field_types = {
        'basic_info': ['id', 'user_id', 'title', 'full_name', 'email', 'phone'],
        'location_fields': ['location', 'address', 'city', 'state', 'zip_code', 'country'],
        'personal_info': ['citizenship', 'gender', 'image_url'],
        'json_fields': ['skills', 'languages', 'work_experience', 'education', 'job_preferences', 'achievements', 'certificates'],
        'timestamps': ['created_at', 'updated_at']
    }
    
    for category, fields in field_types.items():
        print(f"\n{category.upper()}:")
        for field in fields:
            in_db = field in db_columns
            in_model = field in model_columns
            in_schema = field in schema_fields
            status = []
            if in_db: status.append("DB")
            if in_model: status.append("Model")
            if in_schema: status.append("Schema")
            print(f"  {field}: {'✅' if len(status) == 3 else '❌'} ({', '.join(status)})")

if __name__ == "__main__":
    compare_schema() 