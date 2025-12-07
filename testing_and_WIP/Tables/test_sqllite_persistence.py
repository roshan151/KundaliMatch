#!/usr/bin/env python3
"""
Test script to verify persistent storage functionality
"""

import requests
import json
import time

BASE_URL = "/sqlite"

def test_persistence():
    """Test that data persists across container restarts"""
    
    print("🔍 Testing SQLite Service Persistence...")
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print("❌ Health check failed")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to service: {e}")
        return
    
    # Test 2: Create test table
    print("\n2. Creating test table...")
    create_table_query = """
    CREATE TABLE IF NOT EXISTS persistence_test (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_data TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    response = requests.post(f"{BASE_URL}/execute", 
                           json={"query": create_table_query})
    if response.status_code == 200:
        print("✅ Test table created")
    else:
        print(f"❌ Failed to create table: {response.text}")
        return
    
    # Test 3: Insert test data
    print("\n3. Inserting test data...")
    insert_query = "INSERT INTO persistence_test (test_data) VALUES (?)"
    test_value = f"Test data created at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    response = requests.post(f"{BASE_URL}/execute", 
                           json={"query": insert_query, "params": [test_value]})
    if response.status_code == 200:
        print(f"✅ Test data inserted: {test_value}")
    else:
        print(f"❌ Failed to insert data: {response.text}")
        return
    
    # Test 4: Verify data exists
    print("\n4. Verifying data exists...")
    select_query = "SELECT * FROM persistence_test ORDER BY id DESC LIMIT 1"
    
    response = requests.post(f"{BASE_URL}/execute", 
                           json={"query": select_query})
    if response.status_code == 200:
        data = response.json()
        if data['success'] and data['data']:
            latest_record = data['data'][0]
            print(f"✅ Data verified: ID={latest_record['id']}, Data='{latest_record['test_data']}'")
        else:
            print("❌ No data found")
    else:
        print(f"❌ Failed to select data: {response.text}")
        return
    
    # Test 5: Show all persistence test records
    print("\n5. Showing all persistence test records...")
    all_query = "SELECT COUNT(*) as count FROM persistence_test"
    
    response = requests.post(f"{BASE_URL}/execute", 
                           json={"query": all_query})
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            count = data['data'][0]['count']
            print(f"✅ Total persistence test records: {count}")
        else:
            print("❌ Failed to count records")
    else:
        print(f"❌ Failed to count records: {response.text}")
    
    print("\n🎉 Persistence test completed!")
    print("💡 To test full persistence:")
    print("   1. Run this script")
    print("   2. Stop the Docker container")
    print("   3. Start the container again")
    print("   4. Run this script again - data should still exist!")

if __name__ == "__main__":
    test_persistence() 