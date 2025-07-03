#!/usr/bin/env python3
"""
Final verification of the RowCast Dashboard functionality
"""

import requests
import json

def test_dashboard_functionality():
    base_url = "http://localhost:5000"
    
    print("🔍 Final Dashboard Verification")
    print("=" * 40)
    
    # Test 1: Dashboard loads
    try:
        response = requests.get(f"{base_url}/dashboard")
        if response.status_code == 200:
            print("✅ Dashboard page loads successfully")
            # Check for key elements
            if 'current-score' in response.text:
                print("✅ Score widget elements present")
            if 'forecast-grid' in response.text:
                print("✅ Forecast grid elements present")
            if 'dashboard.js' in response.text:
                print("✅ JavaScript file included")
        else:
            print(f"❌ Dashboard failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
    
    # Test 2: API data availability
    try:
        response = requests.get(f"{base_url}/api/complete")
        if response.status_code == 200:
            data = response.json()
            print("✅ API complete endpoint working")
            
            # Check data structure
            if 'current' in data:
                current_score = data['current'].get('rowcastScore', 'N/A')
                print(f"✅ Current score: {current_score}")
                
                if 'weather' in data['current']:
                    temp = data['current']['weather'].get('apparentTemp', 'N/A')
                    wind = data['current']['weather'].get('windSpeed', 'N/A')
                    print(f"✅ Weather data: {temp}°F, {wind} mph wind")
                
                if 'water' in data['current']:
                    flow = data['current']['water'].get('discharge', 'N/A')
                    water_temp = data['current']['water'].get('waterTemp', 'N/A')
                    print(f"✅ Water data: {flow} cfs, {water_temp}°F")
            
            if 'forecast' in data and 'rowcastScores' in data['forecast']:
                forecast_count = len(data['forecast']['rowcastScores'])
                print(f"✅ Forecast data: {forecast_count} hours available")
        else:
            print(f"❌ API failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ API test failed: {e}")
    
    # Test 3: Static files
    static_files = [
        ("/static/css/dashboard.css", "CSS"),
        ("/static/js/dashboard.js", "JavaScript")
    ]
    
    for file_path, file_type in static_files:
        try:
            response = requests.get(f"{base_url}{file_path}")
            if response.status_code == 200:
                size_kb = len(response.content) / 1024
                print(f"✅ {file_type} file loads ({size_kb:.1f} KB)")
            else:
                print(f"❌ {file_type} file failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {file_type} test failed: {e}")
    
    # Test 4: Debug endpoint
    try:
        response = requests.get(f"{base_url}/test-debug")
        if response.status_code == 200:
            print("✅ Debug test page available")
        else:
            print(f"❌ Debug test failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
    
    print("=" * 40)
    print("📋 Summary:")
    print(f"🌐 Dashboard URL: {base_url}/dashboard")
    print(f"📚 Documentation URL: {base_url}/documentation")
    print(f"🧪 Debug URL: {base_url}/test-debug")
    print()
    print("🔧 Key Fixes Applied:")
    print("  • Fixed base URL (using local instead of production)")
    print("  • Added global function wrappers for onclick handlers")
    print("  • Fixed forecast data loading (using complete API)")
    print("  • Added comprehensive debug logging")
    print("  • Fixed JavaScript initialization timing")
    print()
    print("📝 Next Steps:")
    print("  • Open dashboard in browser and check browser console")
    print("  • Verify that data populates correctly")
    print("  • Test interactive features (pagination, time ranges)")
    print("  • Check tooltips on hover")

if __name__ == "__main__":
    test_dashboard_functionality()
