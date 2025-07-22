#!/usr/bin/env python3
"""
Example usage of the MBTI Analysis Service

This script demonstrates how to interact with the MBTI service API
"""

import requests
import json

def example_predictions():
    """Show example predictions for different personality types"""
    
    base_url = "http://localhost:5000"
    
    # Sample texts representing different MBTI types
    examples = [
        {
            "name": "Analyst (NT) - Strategic Thinker",
            "text": "I enjoy analyzing complex systems and finding logical solutions. I prefer working independently on challenging problems and am motivated by efficiency and competence. I like to plan ahead and consider long-term implications of decisions.",
            "expected_types": ["INTJ", "INTP", "ENTJ", "ENTP"]
        },
        {
            "name": "Diplomat (NF) - People-Focused Idealist", 
            "text": "I'm passionate about helping others reach their potential and creating harmony in relationships. I value authenticity and personal growth, and I enjoy exploring new ideas and possibilities for positive change in the world.",
            "expected_types": ["INFJ", "INFP", "ENFJ", "ENFP"]
        },
        {
            "name": "Sentinel (SJ) - Practical Organizer",
            "text": "I believe in following established procedures and maintaining order. I'm reliable, detail-oriented, and prefer structured environments. I value tradition and stability, and I like to plan everything carefully.",
            "expected_types": ["ISTJ", "ISFJ", "ESTJ", "ESFJ"]
        },
        {
            "name": "Explorer (SP) - Flexible Adaptateur",
            "text": "I love spontaneous adventures and hands-on experiences. I prefer to keep my options open and adapt to situations as they come. I'm practical and resourceful, and I enjoy living in the moment.",
            "expected_types": ["ISTP", "ISFP", "ESTP", "ESFP"]
        }
    ]
    
    print("🧠 MBTI Service - Example Predictions")
    print("=" * 60)
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['name']}")
        print("-" * 40)
        print(f"Input: {example['text'][:80]}...")
        print(f"Expected Types: {', '.join(example['expected_types'])}")
        
        try:
            # Make prediction request
            response = requests.post(
                f"{base_url}/predict",
                json={"text": example["text"]},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()["result"]
                
                print(f"Predicted: {result['mbti_type']} ({result['confidence']:.1%} confidence)")
                print(f"Description: {result['description']}")
                
                # Show dimensional breakdown
                dims = result['dimensional_breakdown']
                print(f"Dimensions: {dims['E_vs_I'][0]}{dims['S_vs_N'][0]}{dims['T_vs_F'][0]}{dims['J_vs_P'][0]}")
                
                # Check if prediction matches expected
                if result['mbti_type'] in example['expected_types']:
                    print("✅ Prediction matches expected type!")
                else:
                    print("⚠️  Prediction differs from expected")
                
                # Show top compatibility matches
                matches = list(result['best_compatibility_matches'].items())[:3]
                print(f"Top Matches: {', '.join([f'{t}({s}%)' for t, s in matches])}")
                
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

def interactive_demo():
    """Interactive demo allowing user input"""
    
    base_url = "http://localhost:5000"
    
    print("\n🎮 Interactive MBTI Analysis Demo")
    print("=" * 40)
    print("Enter some text about yourself to get your MBTI prediction!")
    print("(Type 'quit' to exit)")
    
    while True:
        try:
            user_input = input("\nYour text: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if len(user_input) < 10:
                print("⚠️  Please provide more text for better analysis")
                continue
            
            # Make prediction
            response = requests.post(
                f"{base_url}/predict",
                json={"text": user_input},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()["result"]
                
                print(f"\n🎯 Analysis Results:")
                print(f"   MBTI Type: {result['mbti_type']}")
                print(f"   Confidence: {result['confidence']:.1%}")
                print(f"   Description: {result['description']}")
                
                # Show dimensional preferences
                dims = result['dimensional_breakdown']
                print(f"\n🧭 Your Preferences:")
                print(f"   Energy: {dims['E_vs_I']}")
                print(f"   Information: {dims['S_vs_N']}")
                print(f"   Decisions: {dims['T_vs_F']}")
                print(f"   Lifestyle: {dims['J_vs_P']}")
                
                # Show compatibility
                matches = list(result['best_compatibility_matches'].items())[:3]
                print(f"\n💕 Best Compatibility:")
                for mbti_type, score in matches:
                    print(f"   {mbti_type}: {score}%")
                
            else:
                print(f"❌ Error: {response.text}")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def service_info():
    """Display service information"""
    
    base_url = "http://localhost:5000"
    
    print("ℹ️  MBTI Service Information")
    print("=" * 30)
    
    try:
        # Get service info
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            info = response.json()
            print(f"Service: {info['service']}")
            print(f"Version: {info['version']}")
            print("\nEndpoints:")
            for endpoint, description in info['endpoints'].items():
                print(f"  {endpoint}: {description}")
        
        # Get all MBTI types
        response = requests.get(f"{base_url}/types")
        if response.status_code == 200:
            types_data = response.json()
            print(f"\nSupported MBTI Types: {types_data['total_types']}")
            print("\nType Descriptions:")
            for mbti_type, description in list(types_data['mbti_types'].items())[:4]:
                print(f"  {mbti_type}: {description}")
            print("  ... and 12 more types")
            
    except Exception as e:
        print(f"❌ Error connecting to service: {e}")
        print("Make sure the service is running at http://localhost:5000")

def main():
    """Main demo function"""
    
    print("🧠 MBTI Analysis Service - Demo & Examples")
    print("=" * 50)
    
    # Check if service is available
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Service is not healthy")
            return
    except:
        print("❌ Cannot connect to MBTI service at http://localhost:5000")
        print("Please make sure the service is running:")
        print("  ./run_service.sh run")
        return
    
    print("✅ Service is available!")
    
    while True:
        print("\nWhat would you like to do?")
        print("1. View example predictions")
        print("2. Interactive demo (enter your own text)")
        print("3. Service information")
        print("4. Quit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            example_predictions()
        elif choice == "2":
            interactive_demo()
        elif choice == "3":
            service_info()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("⚠️  Invalid choice, please enter 1-4")

if __name__ == "__main__":
    main() 