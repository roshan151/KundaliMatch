#!/usr/bin/env python3
"""
Test script for the CrewAI-based chat system
"""

import requests
import json
import time

# Test configuration
BASE_URL = "/backend"
TEST_UID = "test_user_123"


def test_app_initiated_chat():
    """Test app-initiated hobby conversation"""
    print("=== Testing App-Initiated Chat (/chat/app) ===")
    
    # Start chat (GET request)
    print("Starting app-initiated chat...")
    response = requests.get(f"{BASE_URL}/chat/app?uid={TEST_UID}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Chat started successfully")
        print(f"Message: {data.get('message', 'No message')}")
        print(f"Continue: {data.get('continue', False)}")
        
        # Continue chat (POST request)
        if data.get('continue'):
            continue_payload = {
                "uid": TEST_UID,
                "user_input": "I love playing guitar and reading books",
                "history": data.get('history', [])
            }
            
            print("\nContinuing conversation...")
            continue_response = requests.post(f"{BASE_URL}/chat/app", json=continue_payload)
            
            if continue_response.status_code == 200:
                continue_data = continue_response.json()
                print(f"✅ Conversation continued successfully")
                print(f"Message: {continue_data.get('message', 'No message')}")
            else:
                print(f"❌ Continue failed: {continue_response.status_code}")
                print(continue_response.text)
    else:
        print(f"❌ Start failed: {response.status_code}")
        print(response.text)


def test_user_initiated_chat():
    """Test user-initiated preference conversation"""
    print("\n=== Testing User-Initiated Chat (/chat/user) ===")
    
    # Start chat with general preference
    start_payload = {
        "uid": TEST_UID,
        "user_input": "What do you think about my current matches?"
    }
    
    print("Starting user-initiated chat (general)...")
    response = requests.post(f"{BASE_URL}/chat/user", json=start_payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Chat started successfully")
        print(f"Message: {data.get('message', 'No message')}")
        print(f"Filter applied: {data.get('filter_applied', False)}")
        
        # Test filter request
        filter_payload = {
            "uid": TEST_UID,
            "user_input": "Show me matches only from Delhi",
            "history": data.get('history', [])
        }
        
        print("\nTesting filter request...")
        filter_response = requests.post(f"{BASE_URL}/chat/user", json=filter_payload)
        
        if filter_response.status_code == 200:
            filter_data = filter_response.json()
            print(f"✅ Filter request processed")
            print(f"Message: {filter_data.get('message', 'No message')}")
            print(f"Filter applied: {filter_data.get('filter_applied', False)}")
            if filter_data.get('recommendations'):
                print(f"Recommendations returned: {len(filter_data['recommendations'])}")
        else:
            print(f"❌ Filter request failed: {filter_response.status_code}")
            print(filter_response.text)
    else:
        print(f"❌ Start failed: {response.status_code}")
        print(response.text)


# Legacy endpoints have been completely removed


def test_error_handling():
    """Test error handling"""
    print("\n=== Testing Error Handling ===")
    
    # Test missing uid parameter for app chat
    print("Testing missing uid parameter for /chat/app...")
    response = requests.get(f"{BASE_URL}/chat/app")
    
    if response.status_code == 400:
        print("✅ Error handling works for missing uid parameter")
    else:
        print(f"❌ Expected 400, got {response.status_code}")
    
    # Test missing user_input for user chat
    print("Testing missing user_input for /chat/user...")
    invalid_payload = {"uid": TEST_UID}  # Missing user_input
    
    response = requests.post(f"{BASE_URL}/chat/user", json=invalid_payload)
    
    if response.status_code == 400:
        print("✅ Error handling works for missing user_input")
    else:
        print(f"❌ Expected 400, got {response.status_code}")
    
    # Test missing uid for app chat POST
    print("Testing missing uid for /chat/app POST...")
    invalid_payload = {"user_input": "I like music"}  # Missing uid
    
    response = requests.post(f"{BASE_URL}/chat/app", json=invalid_payload)
    
    if response.status_code == 400:
        print("✅ Error handling works for missing uid in POST")
    else:
        print(f"❌ Expected 400, got {response.status_code}")


def check_crewai_availability():
    """Check if CrewAI system is available"""
    print("=== Checking CrewAI Availability ===")
    
    try:
        # Try to import the CrewAI system
        from crewai_chat_system import crewai_chat
        print("✅ CrewAI chat system is available")
        return True
    except ImportError as e:
        print(f"❌ CrewAI chat system not available: {e}")
        print("Make sure to install crewai and other dependencies:")
        print("pip install crewai langchain langchain-community")
        return False


def main():
    """Run all tests"""
    print("CrewAI Chat System Test Suite")
    print("=" * 40)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print(f"❌ Server not responding properly: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("Make sure the backend server is running")
        return
    
    print("✅ Server is running")
    
    # Check CrewAI availability
    if not check_crewai_availability():
        print("\n❌ CrewAI system not available - ALL CHAT ENDPOINTS WILL FAIL")
        print("The old chat system has been completely replaced with CrewAI.")
        print("Install CrewAI to use any chat functionality:")
        print("pip install crewai langchain langchain-community")
        return
    
    # Run all tests
    test_app_initiated_chat()
    time.sleep(1)  # Brief pause between tests
    
    test_user_initiated_chat()
    time.sleep(1)
    
    test_error_handling()
    
    print("\n" + "=" * 40)
    print("✅ Simplified Chat System Test Suite Completed!")
    print("🎉 All chat endpoints now use simplified CrewAI system")
    print("📱 Frontend apps need to migrate to new endpoints:")
    print("   • /chat/app - for app-initiated hobby conversations")
    print("   • /chat/user - for user-initiated preference conversations")
    print("🚀 Cleaner, faster, and easier to maintain!")


if __name__ == "__main__":
    main() 