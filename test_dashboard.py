#!/usr/bin/env python3
"""
Test the dashboard and API routes
"""

import requests
import sys

def test_dashboard():
    """Test the new dashboard routes"""
    base_url = "http://localhost:5000"
    
    tests = [
        {
            'url': f'{base_url}/dashboard',
            'name': 'Dashboard',
            'expected': 'text/html'
        },
        {
            'url': f'{base_url}/documentation',
            'name': 'API Documentation',
            'expected': 'text/html'
        },
        {
            'url': f'{base_url}/api/complete',
            'name': 'Complete API Data',
            'expected': 'application/json'
        }
    ]
    
    print("🚣 Testing RowCast Dashboard Routes...")
    print("=" * 50)
    
    all_passed = True
    
    for test in tests:
        try:
            response = requests.get(test['url'], timeout=10)
            content_type = response.headers.get('content-type', '').lower()
            
            if response.status_code == 200:
                if test['expected'] in content_type:
                    print(f"✅ {test['name']}: SUCCESS (HTTP {response.status_code})")
                else:
                    print(f"⚠️  {test['name']}: SUCCESS but unexpected content type: {content_type}")
            else:
                print(f"❌ {test['name']}: FAILED (HTTP {response.status_code})")
                all_passed = False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {test['name']}: CONNECTION ERROR - {e}")
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All dashboard tests passed!")
        print("\n📊 Dashboard URL: http://localhost:5000/dashboard")
        print("📚 Documentation URL: http://localhost:5000/documentation")
    else:
        print("⚠️  Some tests failed. Check the server status.")
    
    return all_passed

if __name__ == "__main__":
    success = test_dashboard()
    sys.exit(0 if success else 1)
