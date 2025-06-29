#!/usr/bin/env python3
"""
SQLite Database Schema Setup
This script creates the necessary tables for the KundaliMatch backend service.
"""

import requests
import json
import sys

def execute_sqlite_query(query, params=None):
    """Execute a query on the SQLite service."""
    payload = {
        'query': query,
        'params': params
    }
    
    try:
        response = requests.post(
            'http://localhost:8030/execute',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✓ Query executed successfully: {result.get('message', 'OK')}")
                return True
            else:
                print(f"✗ Query failed: {result.get('error')}")
                return False
        else:
            print(f"✗ HTTP error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error executing query: {e}")
        return False

def create_profile_table():
    """Create the PROFILE table."""
    print("\nCreating PROFILE table...")
    
    query = """
    CREATE TABLE IF NOT EXISTS PROFILE (
        UID TEXT PRIMARY KEY,
        PASSWORD TEXT,
        NAME TEXT,
        PHONE TEXT,
        EMAIL TEXT,
        EMAIL_HASH TEXT UNIQUE,
        CITY TEXT,
        COUNTRY TEXT,
        PROFESSION TEXT,
        BIRTH_CITY TEXT,
        BIRTH_COUNTRY TEXT,
        DOB TEXT,
        TOB TEXT,
        GENDER TEXT,
        HOBBIES TEXT,
        LAT REAL,
        LONG REAL,
        IMAGES TEXT,
        CREATED TEXT,
        LOGIN TEXT,
        NOTIFICATIONS TEXT,
        CHATS TEXT
    )
    """
    
    return execute_sqlite_query(query)

def create_matching_table():
    """Create the MATCHING table."""
    print("\nCreating MATCHING table...")
    
    query = """
    CREATE TABLE IF NOT EXISTS MATCHING (
        UID1 TEXT,
        NAME1 TEXT,
        UID2 TEXT,
        NAME2 TEXT,
        SCORE TEXT,
        CREATED TEXT,
        UPDATED TEXT,
        ALIGN1 INTEGER DEFAULT 0,
        ALIGN2 INTEGER DEFAULT 0,
        SKIP1 INTEGER DEFAULT 0,
        SKIP2 INTEGER DEFAULT 0,
        BLOCK1 INTEGER DEFAULT 0,
        BLOCK2 INTEGER DEFAULT 0,
        CONVERSATION_SID TEXT,
        PRIMARY KEY (UID1, UID2)
    )
    """
    
    return execute_sqlite_query(query)

def create_indexes():
    """Create useful indexes for performance."""
    print("\nCreating indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_profile_email_hash ON PROFILE(EMAIL_HASH)",
        "CREATE INDEX IF NOT EXISTS idx_profile_gender ON PROFILE(GENDER)",
        "CREATE INDEX IF NOT EXISTS idx_profile_uid ON PROFILE(UID)",
        "CREATE INDEX IF NOT EXISTS idx_matching_uid1 ON MATCHING(UID1)",
        "CREATE INDEX IF NOT EXISTS idx_matching_uid2 ON MATCHING(UID2)",
        "CREATE INDEX IF NOT EXISTS idx_matching_uids ON MATCHING(UID1, UID2)"
    ]
    
    success = True
    for index_query in indexes:
        if not execute_sqlite_query(index_query):
            success = False
    
    return success

def verify_tables():
    """Verify that tables were created successfully."""
    print("\nVerifying tables...")
    
    try:
        response = requests.get('http://localhost:8030/tables', timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                tables = result.get('tables', [])
                print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
                
                # Check for required tables
                required_tables = ['PROFILE', 'MATCHING']
                for table in required_tables:
                    if table in tables:
                        print(f"✓ {table} table exists")
                    else:
                        print(f"✗ {table} table missing")
                        return False
                return True
            else:
                print(f"✗ Failed to list tables: {result.get('error')}")
                return False
        else:
            print(f"✗ HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error verifying tables: {e}")
        return False

def main():
    """Main setup function."""
    print("Setting up SQLite database schema for KundaliMatch backend...")
    
    # Check if SQLite service is running
    try:
        response = requests.get('http://localhost:8030/', timeout=5)
        if response.status_code != 200:
            print("✗ SQLite service is not responding. Please start the service first.")
            sys.exit(1)
        print("✓ SQLite service is running")
    except Exception as e:
        print(f"✗ Cannot connect to SQLite service: {e}")
        print("Please make sure the SQLite service is running on port 8030")
        sys.exit(1)
    
    # Create tables
    success = True
    success &= create_profile_table()
    success &= create_matching_table()
    success &= create_indexes()
    success &= verify_tables()
    
    if success:
        print("\n✓ Database schema setup completed successfully!")
        print("The backend service can now connect to SQLite.")
    else:
        print("\n✗ Database schema setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 