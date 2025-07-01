#!/usr/bin/env python3
"""
Test script to verify API functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_endpoint(endpoint, description):
    """Test a single API endpoint"""
    try:
        print(f"\n--- Testing {description} ---")
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'List with ' + str(len(data)) + ' items'}")
            if isinstance(data, dict) and len(str(data)) < 500:
                print(f"Sample data: {json.dumps(data, indent=2)[:500]}...")
            elif isinstance(data, list) and len(data) > 0:
                print(f"First item: {json.dumps(data[0], indent=2)}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Failed to test {endpoint}: {e}")

def main():
    """Run all API tests"""
    print("=== RowCast API Test Suite ===")
    print(f"Testing API at {BASE_URL}")
    print(f"Test started at: {datetime.now()}")
    
    # Wait a moment for data to be available
    print("\nWaiting 30 seconds for initial data fetch...")
    time.sleep(30)
    
    # Test all endpoints
    endpoints = [
        ("/api/weather", "Weather Data (Full)"),
        ("/api/weather/current", "Current Weather"),
        ("/api/weather/forecast", "Weather Forecast"),
        ("/api/water", "Water Data (Full)"),
        ("/api/water/current", "Current Water Data"),
        ("/api/water/predictions", "Water Predictions"),
        ("/api/rowcast", "Current RowCast Score"),
        ("/api/rowcast/forecast", "RowCast Forecast"),
        ("/api/rowcast/forecast/2h", "RowCast Score in 2 hours"),
        ("/api/complete", "Complete Data"),
    ]
    
    for endpoint, description in endpoints:
        test_endpoint(endpoint, description)
    
    print(f"\n=== Test completed at: {datetime.now()} ===")

if __name__ == "__main__":
    main()
