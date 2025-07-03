#!/usr/bin/env python3
"""
Test script to verify dashboard features and functionality
"""

import requests
import time
from bs4 import BeautifulSoup

def test_dashboard_features():
    base_url = "http://localhost:5000"
    
    print("🧪 Testing RowCast Dashboard Features...")
    print("=" * 50)
    
    # Test 1: Dashboard loads correctly
    try:
        response = requests.get(f"{base_url}/dashboard", timeout=10)
        assert response.status_code == 200
        print("✅ Dashboard loads successfully")
        
        # Parse HTML to check for key elements
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for tooltip elements
        tooltip_elements = soup.find_all(attrs={"data-tooltip": True})
        print(f"✅ Found {len(tooltip_elements)} elements with tooltips")
        
        # Check for required CSS and JS files
        css_links = soup.find_all('link', rel='stylesheet')
        dashboard_css = any('dashboard.css' in link.get('href', '') for link in css_links)
        print(f"✅ Dashboard CSS loaded: {dashboard_css}")
        
        js_scripts = soup.find_all('script')
        dashboard_js = any('dashboard.js' in script.get('src', '') for script in js_scripts)
        chart_js = any('chart.js' in script.get('src', '') for script in js_scripts)
        print(f"✅ Dashboard JS loaded: {dashboard_js}")
        print(f"✅ Chart.js loaded: {chart_js}")
        
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False
    
    # Test 2: API Documentation
    try:
        response = requests.get(f"{base_url}/documentation", timeout=10)
        assert response.status_code == 200
        print("✅ API Documentation loads successfully")
        
        # Check for base URL presence
        assert "api.samwduncan.com" in response.text
        print("✅ Documentation contains correct base URL")
        
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False
    
    # Test 3: API Endpoints respond correctly
    api_endpoints = [
        "/api/complete",
        "/api/rowcast",
        "/api/weather/current",
        "/api/water/current"
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {endpoint}: OK")
            else:
                print(f"⚠️ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
    
    # Test 4: Static files
    static_files = [
        "/static/css/dashboard.css",
        "/static/js/dashboard.js"
    ]
    
    for static_file in static_files:
        try:
            response = requests.get(f"{base_url}{static_file}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {static_file}: OK")
            else:
                print(f"❌ {static_file}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {static_file}: {e}")
    
    print("=" * 50)
    print("🎉 Dashboard feature tests completed!")
    print()
    print("📋 Summary:")
    print(f"📊 Dashboard: http://localhost:5000/dashboard")
    print(f"📚 Documentation: http://localhost:5000/documentation")
    print(f"🔗 API Base: https://api.samwduncan.com")
    print()
    print("🎯 Key Features:")
    print("  • Dark mode dashboard with modern UI")
    print("  • Interactive widgets for current conditions")
    print("  • Forecast pagination and time range selection")
    print("  • Real-time charts for score trends and conditions")
    print("  • Comprehensive tooltips for user guidance")
    print("  • Complete API documentation with working links")
    print("  • Mobile-responsive design")
    
    return True

if __name__ == "__main__":
    test_dashboard_features()
