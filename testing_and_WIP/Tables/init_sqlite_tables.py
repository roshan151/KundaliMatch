#!/usr/bin/env python3
"""
SQLite Database Initialization Script
Creates the required tables for the kundali matching application.
"""

import requests
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQLITE_SERVICE_URL = "/sqlite"

def execute_sql(query, description=""):
    """Execute SQL query through SQLite service"""
    try:
        response = requests.post(f"{SQLITE_SERVICE_URL}/execute", 
                               json={"query": query})
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            logger.info(f"✓ {description}")
            return True
        else:
            logger.error(f"✗ {description}: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"✗ {description}: {e}")
        return False

def init_tables():
    """Initialize all required tables"""
    
    # Profile table - based on the CSV schema
    profile_table_sql = """
    CREATE TABLE IF NOT EXISTS PROFILE_DB (
        UID TEXT PRIMARY KEY,
        PASSWORD TEXT NOT NULL,
        NAME TEXT NOT NULL,
        PHONE TEXT,
        EMAIL TEXT,
        EMAIL_HASH TEXT,
        CITY TEXT,
        COUNTRY TEXT,
        PROFESSION TEXT,
        BIRTH_CITY TEXT,
        BIRTH_COUNTRY TEXT,
        DOB TEXT,
        TOB TEXT,
        GENDER TEXT,
        HOBBIES TEXT,
        LAT TEXT,
        LONG TEXT,
        IMAGES TEXT,
        CREATED TEXT,
        LOGIN TEXT,
        FILTERS TEXT,
        NOTIFICATIONS TEXT,
        INITIATE_CHATS TEXT,
        PREFERENCE_CHATS TEXT,
        MBTI TEXT,
        MBTI_DESCRIPTION TEXT,
        MBTI_RESPONSE TEXT,
        DESTINY_CHATS TEXT,
        QUESTION1 TEXT,
        QUESTION2 TEXT,
        QUESTION3 TEXT
    )
    """
    
    # Matching table - based on the CSV schema
    matching_table_sql = """
    CREATE TABLE IF NOT EXISTS MATCHING_TABLE (
        UID1 TEXT NOT NULL,
        UID2 TEXT NOT NULL,
        SCORE REAL,
        CREATED TEXT,
        UPDATED TEXT,
        ALIGN1 BOOLEAN DEFAULT FALSE,
        ALIGN2 BOOLEAN DEFAULT FALSE,
        SKIP1 BOOLEAN DEFAULT FALSE,
        SKIP2 BOOLEAN DEFAULT FALSE,
        BLOCK1 BOOLEAN DEFAULT FALSE,
        BLOCK2 BOOLEAN DEFAULT FALSE,
        NAME1 TEXT,
        NAME2 TEXT,
        REASON1 TEXT,
        REASON2 TEXT,
        FILTERED BOOLEAN,
        CONVERSATION_SID TEXT,
        PRIMARY KEY (UID1, UID2)
    )
    """
    
    # Create indexes for better performance
    profile_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_profile_email_hash ON PROFILE_DB(EMAIL_HASH)",
        "CREATE INDEX IF NOT EXISTS idx_profile_gender ON PROFILE_DB(GENDER)",
        "CREATE INDEX IF NOT EXISTS idx_profile_uid ON PROFILE_DB(UID)"
    ]
    
    matching_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_matching_uid1 ON MATCHING_TABLE(UID1)",
        "CREATE INDEX IF NOT EXISTS idx_matching_uid2 ON MATCHING_TABLE(UID2)",
        "CREATE INDEX IF NOT EXISTS idx_matching_updated ON MATCHING_TABLE(UPDATED)"
    ]
    
    logger.info("Initializing SQLite database tables...")
    
    # Create tables
    success = True
    success &= execute_sql(profile_table_sql, "Created PROFILE_DB table")
    success &= execute_sql(matching_table_sql, "Created MATCHING_TABLE table")
    
    # Create indexes
    for idx_sql in profile_indexes:
        success &= execute_sql(idx_sql, f"Created profile index")
    
    for idx_sql in matching_indexes:
        success &= execute_sql(idx_sql, f"Created matching index")
    
    if success:
        logger.info("✓ Database initialization completed successfully!")
    else:
        logger.error("✗ Database initialization failed!")
    
    return success

def check_service_health():
    """Check if SQLite service is running"""
    try:
        response = requests.get(f"{SQLITE_SERVICE_URL}/")
        if response.status_code == 200:
            logger.info("✓ SQLite service is running")
            return True
    except Exception as e:
        logger.error(f"✗ SQLite service not available: {e}")
        return False

if __name__ == "__main__":
    logger.info("SQLite Database Initialization")
    logger.info("=" * 40)
    
    if check_service_health():
        init_tables()
    else:
        logger.error("Please start the SQLite service first:")
        logger.error("cd service-sqlite && python sqlite_service.py") 