#!/usr/bin/env python3
"""
Test script for MBTI Service

Run this script to test the MBTI service endpoints
"""

import requests
import json
import time

def test_mbti_service(base_url="http://localhost:5000"):
    """Test all MBTI service endpoints"""
    
    print("🧪 Testing MBTI Service")
    print("="*50)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Test root endpoint
    print("\n2. Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Service: {data.get('service')}")
        print(f"   Version: {data.get('version')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test types endpoint
    print("\n3. Testing types endpoint...")
    try:
        response = requests.get(f"{base_url}/types")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Total types: {data.get('total_types')}")
        print(f"   Sample types: {list(data.get('mbti_types', {}).keys())[:5]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test prediction endpoint with sample texts
    print("\n4. Testing prediction endpoint...")
    
    test_cases = [
        {
            "name": "Introvert Thinker",
            "text": "I prefer working alone and solving complex problems. I like to analyze data and make logical decisions based on facts. I enjoy quiet environments where I can focus deeply on my work."
        },
        {
            "name": "Extrovert Feeler",
            "text": "I love meeting new people and making connections. I care deeply about others' feelings and try to help everyone around me. I enjoy parties and social gatherings where I can energize others."
        },
        {
            "name": "Intuitive Perceiver",
            "text": "I'm always thinking about future possibilities and new ideas. I like to keep my options open and adapt to new situations. I enjoy exploring abstract concepts and theoretical discussions."
        },
        {
            "name": "Sensor Judger",
            "text": "I focus on practical details and concrete facts. I like to plan ahead and organize everything in my life. I prefer structured environments and clear procedures to follow."
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   Test {i}: {test_case['name']}")
        try:
            payload = {"text": test_case["text"]}
            response = requests.post(
                f"{base_url}/predict",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})
                
                print(f"   Predicted MBTI: {result.get('mbti_type')}")
                print(f"   Confidence: {result.get('confidence', 0):.3f}")
                print(f"   Description: {result.get('description', '')[:50]}...")
                
                # Show dimensional breakdown
                dimensions = result.get('dimensional_breakdown', {})
                print(f"   Dimensions: {', '.join(dimensions.values())}")
                
            else:
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test error cases
    print("\n5. Testing error cases...")
    
    # Empty text
    try:
        payload = {"text": ""}
        response = requests.post(f"{base_url}/predict", json=payload)
        print(f"   Empty text - Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.json().get('error', '')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Missing text field
    try:
        payload = {"message": "This should fail"}
        response = requests.post(f"{base_url}/predict", json=payload)
        print(f"   Missing field - Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.json().get('error', '')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # No JSON
    try:
        response = requests.post(f"{base_url}/predict")
        print(f"   No JSON - Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.json().get('error', '')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ Testing complete!")
    return True

def benchmark_service(base_url="http://localhost:5000", num_requests=10):
    """Benchmark the service performance"""
    
    print(f"\n⚡ Benchmarking service with {num_requests} requests...")
    
    test_text = "I enjoy meeting new people and working in teams. I prefer practical solutions and like to plan ahead for everything."
    payload = {"text": test_text}
    
    times = []
    success_count = 0
    
    for i in range(num_requests):
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{base_url}/predict",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            end_time = time.time()
            request_time = end_time - start_time
            times.append(request_time)
            
            if response.status_code == 200:
                success_count += 1
            
            if i % 5 == 0:
                print(f"   Progress: {i+1}/{num_requests} requests completed")
                
        except Exception as e:
            print(f"   Request {i+1} failed: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 Benchmark Results:")
        print(f"   Total requests: {num_requests}")
        print(f"   Successful: {success_count}")
        print(f"   Success rate: {success_count/num_requests*100:.1f}%")
        print(f"   Average response time: {avg_time:.3f}s")
        print(f"   Min response time: {min_time:.3f}s")
        print(f"   Max response time: {max_time:.3f}s")
        print(f"   Requests per second: {1/avg_time:.2f}")

if __name__ == "__main__":
    import sys
    
    base_url = "http://localhost:5000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing MBTI service at: {base_url}")
    
    # Basic functionality test
    success = test_mbti_service(base_url)
    
    if success:
        # Performance benchmark
        benchmark_service(base_url)
    else:
        print("❌ Basic tests failed, skipping benchmark") 