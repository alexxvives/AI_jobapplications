#!/usr/bin/env python3
"""
Migration script to add first_name and last_name columns to the profiles table.
This script will:
1. Add the new columns to the profiles table
2. Populate them from existing full_name data if available
"""

import os
import sys
from sqlalchemy import create_engine, text
from database import Base, engine

def migrate_profile_fields():
    """Add first_name and last_name columns to profiles table"""
    
    # Create a connection
    connection = engine.connect()
    
    try:
        # Check if columns already exist (SQLite way)
        result = connection.execute(text("PRAGMA table_info(profiles)"))
        existing_columns = [row[1] for row in result]
        
        if 'first_name' not in existing_columns:
            print("Adding first_name column...")
            connection.execute(text("ALTER TABLE profiles ADD COLUMN first_name VARCHAR"))
            connection.commit()
            print("✓ Added first_name column")
        else:
            print("first_name column already exists")
            
        if 'last_name' not in existing_columns:
            print("Adding last_name column...")
            connection.execute(text("ALTER TABLE profiles ADD COLUMN last_name VARCHAR"))
            connection.commit()
            print("✓ Added last_name column")
        else:
            print("last_name column already exists")
        
        # Populate first_name and last_name from existing full_name data
        print("Populating first_name and last_name from existing full_name data...")
        result = connection.execute(text("""
            SELECT id, full_name 
            FROM profiles 
            WHERE full_name IS NOT NULL 
            AND full_name != '' 
            AND (first_name IS NULL OR first_name = '')
        """))
        
        updated_count = 0
        for row in result:
            profile_id, full_name = row
            if full_name and full_name.strip():
                # Simple name parsing - split on first space
                name_parts = full_name.strip().split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                connection.execute(text("""
                    UPDATE profiles 
                    SET first_name = :first_name, last_name = :last_name 
                    WHERE id = :profile_id
                """), {
                    'first_name': first_name,
                    'last_name': last_name,
                    'profile_id': profile_id
                })
                updated_count += 1
        
        connection.commit()
        print(f"✓ Updated {updated_count} profiles with first_name and last_name")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    print("Starting profile fields migration...")
    migrate_profile_fields()
    print("Migration completed successfully!") 