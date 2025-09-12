#!/usr/bin/env python3

import sys
import os
import requests
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_sec_service():
    """Test SEC service directly"""
    print("🧪 Testing SEC Service...")
    
    try:
        from sec_service import sec_service
        
        # Test ticker search
        print("1. Testing AAPL search...")
        results = sec_service.search_documents("AAPL", 3)
        print(f"   Found {len(results)} results for AAPL")
        
        # Test typo search
        print("2. Testing APPL (typo) search...")
        results_typo = sec_service.search_documents("APPL", 3)
        print(f"   Found {len(results_typo)} results for APPL")
        
        # Test company name search
        print("3. Testing Apple search...")
        results_name = sec_service.search_documents("Apple", 3)
        print(f"   Found {len(results_name)} results for Apple")
        
        print("✅ SEC Service tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ SEC Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n🌐 Testing API Endpoints...")
    
    base_url = "http://localhost:8005"
    
    # Test search endpoint
    try:
        print("1. Testing search endpoint...")
        response = requests.post(
            f"{base_url}/api/sec/search",
            json={"query": "AAPL", "limit": 3},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('documents', []))} documents")
            print("✅ API endpoint test passed!")
            return True
        else:
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Backend not running or not accessible")
        return False
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 SEC Integration Test")
    print("=" * 50)
    
    # Test service
    service_ok = test_sec_service()
    
    # Test API
    api_ok = test_api_endpoints()
    
    print("\n" + "=" * 50)
    if service_ok and api_ok:
        print("🎉 All tests passed!")
    elif service_ok:
        print("⚠️  Service OK, but API issues")
    else:
        print("❌ Tests failed")