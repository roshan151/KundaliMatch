import requests
import json
from sqlite_adapter import SQLConnect

BASE_URL = "/backend"

# Get test users from SQLite
def fetch_test_data():
    conn = SQLConnect()
    conn.cursor.execute("SELECT UID, EMAIL, PASSWORD FROM PROFILE_DB LIMIT 5")
    rows = conn.cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries for easier handling
    test_users = []
    for row in rows:
        test_users.append({
            "uid": row.get("UID") if isinstance(row, dict) else row[0],
            "email": row.get("EMAIL") if isinstance(row, dict) else row[1], 
            "password": row.get("PASSWORD") if isinstance(row, dict) else row[2]
        })
    return test_users

def run_tests():
    print("Fetching test data from SQLite...")
    try:
        users = fetch_test_data()
        if not users:
            print("No test users found in database. Please create some test users first.")
            return
            
        for user in users:
            print(f"\nTesting for user: {user['email']}")

            endpoints = [
                {
                    "desc": "/account:login",
                    "method": "POST",
                    "url": f"{BASE_URL}/account:login",
                    "data": {"email": user["email"], "password": user["password"]}
                },
                {
                    "desc": "/verify:email",  
                    "method": "POST",
                    "url": f"{BASE_URL}/verify:email",
                    "data": {"email": user["email"]}
                },
                {
                    "desc": "/get:profile/<uid>",
                    "method": "GET", 
                    "url": f"{BASE_URL}/get:profile/{user['uid']}"
                },
                {
                    "desc": "/get:user/<uid>",
                    "method": "GET",
                    "url": f"{BASE_URL}/get:user/{user['uid']}"
                },
                {
                    "desc": "/chat:initiate/<uid>",
                    "method": "GET",
                    "url": f"{BASE_URL}/chat:initiate/{user['uid']}"
                },
                {
                    "desc": "/get:recommendations/<uid>",
                    "method": "GET",
                    "url": f"{BASE_URL}/get:recommendations/{user['uid']}"
                },
                {
                    "desc": "/get:matches/<uid>",
                    "method": "GET", 
                    "url": f"{BASE_URL}/get:matches/{user['uid']}"
                },
                {
                    "desc": "/get:awaiting/<uid>",
                    "method": "GET",
                    "url": f"{BASE_URL}/get:awaiting/{user['uid']}"
                }
            ]

            for ep in endpoints:
                print(f"Testing {ep['desc']}")
                try:
                    if ep["method"] == "POST":
                        response = requests.post(ep["url"], json=ep["data"])
                    else:
                        response = requests.get(ep["url"])

                    print(f"Status: {response.status_code}")
                    if response.status_code == 200:
                        print("✓ Success")
                    else:
                        print(f"✗ Response: {response.text}")
                    print()
                except Exception as e:
                    print(f"✗ Error testing {ep['desc']}: {str(e)}")
                    
    except Exception as e:
        print(f"Error fetching test data: {str(e)}")
        print("Make sure SQLite service is running and database is initialized.")

if __name__ == "__main__":
    print("Backend Endpoint Testing with SQLite")
    print("=" * 40)
    run_tests()
