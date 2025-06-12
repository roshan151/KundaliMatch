import requests
import json
import snowflake.connector
from config import (
    SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA
)

BASE_URL = "http://localhost:8080"

# Get test users from Snowflake
def fetch_test_data():
    conn = snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA
    )
    cursor = conn.cursor()
    cursor.execute("SELECT uid, email, password FROM test_users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"uid": uid, "email": email, "password": pwd} for uid, email, pwd in rows]

def run_tests():
    users = fetch_test_data()
    for user in users:
        print(f"\nTesting for user: {user['email']}")

        endpoints = [
            {
                "desc": "/account:update",
                "method": "POST",
                "url": f"{BASE_URL}/account:update",
                "data": {"uid": user["uid"], "password": user["password"]}
            },
            {
                "desc": "/account:login",
                "method": "POST",
                "url": f"{BASE_URL}/account:login",
                "data": {"email": user["email"], "password": user["password"]}
            },
            {
                "desc": "/account:create",
                "method": "POST",
                "url": f"{BASE_URL}/account:create",
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
                "desc": "/chat:initiate/<uid>",
                "method": "GET",
                "url": f"{BASE_URL}/chat:initiate/{user['uid']}"
            },
            {
                "desc": "/account:action",
                "method": "POST",
                "url": f"{BASE_URL}/account:action",
                "data": {"uid": user["uid"], "action": "some_action"}
            },
            {
                "desc": "/find:profiles",
                "method": "POST",
                "url": f"{BASE_URL}/find:profiles",
                "data": {"criteria": {"interests": ["test"]}}
            },
            {
                "desc": "/chat:continue",
                "method": "POST",
                "url": f"{BASE_URL}/chat:continue",
                "data": {"uid": user["uid"], "message": "Hello"}
            },
            {
                "desc": "/twillio:token",
                "method": "POST",
                "url": f"{BASE_URL}/twillio:token",
                "data": {"uid": user["uid"]}
            }
        ]

        for ep in endpoints:
            print(f"Testing {ep['desc']}")
            try:
                if ep["method"] == "POST":
                    response = requests.post(ep["url"], files={"metadata": (None, json.dumps(ep["data"]))})
                else:
                    response = requests.get(ep["url"])

                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}\n")
            except Exception as e:
                print(f"Error testing {ep['desc']}: {str(e)}")

if __name__ == "__main__":
    run_tests()
