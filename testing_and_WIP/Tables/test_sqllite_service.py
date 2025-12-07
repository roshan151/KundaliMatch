#!/usr/bin/env python3
"""
Test script for SQLite HTTP Service
Run this after starting the service to verify it's working correctly.
"""

import requests
import json
import time

BASE_URL = "/sqlite"

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print("❌ Health check failed")
            print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")

def test_list_tables():
    """Test listing tables."""
    print("\nTesting list tables...")
    try:
        response = requests.get(f"{BASE_URL}/tables")
        if response.status_code == 200:
            print("✅ List tables passed")
            data = response.json()
            print(f"   Tables: {data.get('tables', [])}")
        else:
            print("❌ List tables failed")
            print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"❌ List tables error: {e}")

def test_execute_select():
    """Test executing a SELECT query."""
    print("\nTesting SELECT query...")
    try:
        payload = {"query": "SELECT * FROM sample_data LIMIT 3"}
        response = requests.post(f"{BASE_URL}/execute", json=payload)
        if response.status_code == 200:
            print("✅ SELECT query passed")
            data = response.json()
            print(f"   Rows returned: {data.get('rows_affected', 0)}")
            if data.get('data'):
                print(f"   First row: {data['data'][0] if data['data'] else 'No data'}")
        else:
            print("❌ SELECT query failed")
            print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"❌ SELECT query error: {e}")

def test_execute_insert():
    """Test executing an INSERT query."""
    print("\nTesting INSERT query...")
    try:
        payload = {
            "query": "INSERT INTO sample_data (name, value) VALUES (?, ?)",
            "params": ["Test Item", f"Test Value {int(time.time())}"]
        }
        response = requests.post(f"{BASE_URL}/execute", json=payload)
        if response.status_code == 200:
            print("✅ INSERT query passed")
            data = response.json()
            print(f"   Rows affected: {data.get('rows_affected', 0)}")
        else:
            print("❌ INSERT query failed")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ INSERT query error: {e}")

def test_table_schema():
    """Test getting table schema."""
    print("\nTesting table schema...")
    try:
        response = requests.get(f"{BASE_URL}/schema/sample_data")
        if response.status_code == 200:
            print("✅ Table schema passed")
            data = response.json()
            print(f"   Schema columns: {len(data.get('schema', []))}")
        else:
            print("❌ Table schema failed")
            print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Table schema error: {e}")

def test_backup():
    """Test database backup."""
    print("\nTesting database backup...")
    try:
        response = requests.post(f"{BASE_URL}/backup")
        if response.status_code == 200:
            print("✅ Database backup passed")
            data = response.json()
            print(f"   Backup file: {data.get('backup_file', 'Unknown')}")
        else:
            print("❌ Database backup failed")
            print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Database backup error: {e}")

def main():
    """Run all tests."""
    print("SQLite HTTP Service Test Suite")
    print("=" * 40)
    
    test_health_check()
    test_list_tables()
    test_execute_select()
    test_execute_insert()
    test_table_schema()
    test_backup()
    
    print("\n" + "=" * 40)
    print("Test suite completed!")

if __name__ == "__main__":
    main() 