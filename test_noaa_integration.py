#!/usr/bin/env python3
"""
Test script for NOAA NWPS integration with RowCast API.
This script tests the NOAA stageflow forecast data integration,
extended weather forecasts, and the new API endpoints.
"""

import sys
import json
import requests
from datetime import datetime, timedelta
import traceback

# Add the app directory to Python path
sys.path.insert(0, '/home/swd/RowCast_API/samsara-api')

def test_noaa_api_direct():
    """Test direct access to NOAA NWPS API"""
    print("=" * 60)
    print("TESTING DIRECT NOAA API ACCESS")
    print("=" * 60)
    
    try:
        url = "https://api.water.noaa.gov/nwps/v1/gauges/padp1/stageflow"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ NOAA API accessible")
        print(f"✓ Response status: {response.status_code}")
        
        observed_data = data.get('observed', {}).get('data', [])
        forecast_data = data.get('forecast', {}).get('data', [])
        
        print(f"✓ Observed data points: {len(observed_data)}")
        print(f"✓ Forecast data points: {len(forecast_data)}")
        
        if forecast_data:
            first_forecast = forecast_data[0]
            last_forecast = forecast_data[-1]
            print(f"✓ Forecast range: {first_forecast.get('validTime')} to {last_forecast.get('validTime')}")
            print(f"✓ Sample forecast: Stage={first_forecast.get('primary')}ft, Flow={first_forecast.get('secondary')}kcfs")
        
        return True
        
    except Exception as e:
        print(f"✗ NOAA API test failed: {e}")
        traceback.print_exc()
        return False

def test_noaa_fetcher_functions():
    """Test NOAA fetcher functions"""
    print("\n" + "=" * 60)
    print("TESTING NOAA FETCHER FUNCTIONS")
    print("=" * 60)
    
    try:
        from app.fetchers import fetch_noaa_stageflow_forecast, fetch_extended_weather_forecast
        
        # Test NOAA stageflow forecast
        print("Testing fetch_noaa_stageflow_forecast()...")
        noaa_data = fetch_noaa_stageflow_forecast()
        
        print(f"✓ NOAA stageflow data fetched successfully")
        print(f"✓ Current data available: {noaa_data.get('current') is not None}")
        print(f"✓ Observed points: {len(noaa_data.get('observed', []))}")
        print(f"✓ Forecast points: {len(noaa_data.get('forecast', []))}")
        print(f"✓ Raw forecast points: {len(noaa_data.get('raw_forecast', []))}")
        
        if noaa_data.get('forecast'):
            first = noaa_data['forecast'][0]
            last = noaa_data['forecast'][-1]
            print(f"✓ Interpolated forecast range: {first.get('timestamp')} to {last.get('timestamp')}")
            print(f"✓ Sample interpolated: discharge={first.get('discharge')}, stage={first.get('gaugeHeight')}")
        
        # Test extended weather forecast
        print("\nTesting fetch_extended_weather_forecast()...")
        extended_weather = fetch_extended_weather_forecast()
        
        print(f"✓ Extended weather data fetched successfully")
        print(f"✓ Current data available: {extended_weather.get('current') is not None}")
        print(f"✓ Extended forecast hours: {len(extended_weather.get('forecast', []))}")
        print(f"✓ Forecast days: {extended_weather.get('forecastDays')}")
        
        return True
        
    except Exception as e:
        print(f"✗ NOAA fetcher test failed: {e}")
        traceback.print_exc()
        return False

def test_task_functions():
    """Test the new task functions"""
    print("\n" + "=" * 60)
    print("TESTING TASK FUNCTIONS")
    print("=" * 60)
    
    try:
        from app.tasks import (
            update_noaa_stageflow_job,
            update_extended_weather_data_job,
            update_extended_forecast_scores_job
        )
        from app.extensions import redis_client
        
        # Test NOAA stageflow job
        print("Testing update_noaa_stageflow_job()...")
        update_noaa_stageflow_job()
        
        # Check if data was stored in Redis
        noaa_data_str = redis_client.get('noaa_stageflow_data')
        if noaa_data_str:
            noaa_data = json.loads(noaa_data_str)
            print(f"✓ NOAA stageflow data stored in Redis")
            print(f"✓ Forecast points in Redis: {len(noaa_data.get('forecast', []))}")
        else:
            print("✗ NOAA stageflow data not found in Redis")
            return False
        
        # Test extended weather job
        print("\nTesting update_extended_weather_data_job()...")
        update_extended_weather_data_job()
        
        # Check if data was stored in Redis
        extended_weather_str = redis_client.get('extended_weather_data')
        if extended_weather_str:
            extended_weather = json.loads(extended_weather_str)
            print(f"✓ Extended weather data stored in Redis")
            print(f"✓ Extended forecast hours in Redis: {len(extended_weather.get('forecast', []))}")
        else:
            print("✗ Extended weather data not found in Redis")
            return False
        
        # Test extended forecast scores job
        print("\nTesting update_extended_forecast_scores_job()...")
        update_extended_forecast_scores_job()
        
        # Check if scores were calculated and stored
        extended_scores_str = redis_client.get('extended_forecast_scores')
        if extended_scores_str:
            extended_scores = json.loads(extended_scores_str)
            print(f"✓ Extended forecast scores calculated and stored")
            print(f"✓ Extended forecast score points: {len(extended_scores)}")
            
            # Count how many used NOAA data
            noaa_count = sum(1 for score in extended_scores if score.get('noaaDataUsed'))
            print(f"✓ Scores using NOAA data: {noaa_count}/{len(extended_scores)}")
        else:
            print("✗ Extended forecast scores not found in Redis")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Task function test failed: {e}")
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test the new API endpoints"""
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINTS")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    endpoints_to_test = [
        "/api/noaa/stageflow",
        "/api/noaa/stageflow/current",
        "/api/noaa/stageflow/forecast",
        "/api/weather/extended",
        "/api/rowcast/forecast/extended",
        "/api/rowcast/forecast/extended/simple",
        "/api/complete/extended",
        "/api/dashboard"
    ]
    
    success_count = 0
    
    for endpoint in endpoints_to_test:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {endpoint} - Status: {response.status_code}")
                
                # Basic validation based on endpoint
                if "noaa" in endpoint and "stageflow" in endpoint:
                    if "forecast" in endpoint:
                        print(f"  - Forecast data points: {len(data) if isinstance(data, list) else 'N/A'}")
                    elif "current" in endpoint:
                        print(f"  - Current timestamp: {data.get('timestamp', 'N/A')}")
                    else:
                        print(f"  - Has current: {data.get('current') is not None}")
                        print(f"  - Has forecast: {data.get('forecast') is not None}")
                
                elif "extended" in endpoint:
                    if isinstance(data, list):
                        print(f"  - Data points: {len(data)}")
                    else:
                        print(f"  - Has forecast data: {data.get('forecast') is not None}")
                
                elif endpoint == "/api/dashboard":
                    print(f"  - Dashboard HTML rendered successfully")
                
                success_count += 1
            else:
                print(f"✗ {endpoint} - Status: {response.status_code}")
                if response.status_code == 404:
                    print(f"  - Error: {response.json().get('error', 'Unknown error')}")
                
        except requests.exceptions.ConnectionError:
            print(f"✗ {endpoint} - Connection failed (server not running?)")
        except Exception as e:
            print(f"✗ {endpoint} - Error: {e}")
    
    print(f"\nAPI Endpoint Test Results: {success_count}/{len(endpoints_to_test)} endpoints successful")
    return success_count == len(endpoints_to_test)

def test_forecast_integration():
    """Test that NOAA data is properly integrated into forecasts"""
    print("\n" + "=" * 60)
    print("TESTING FORECAST INTEGRATION")
    print("=" * 60)
    
    try:
        from app.extensions import redis_client
        
        # Get forecast scores and check for NOAA integration
        forecast_scores_str = redis_client.get('forecast_scores')
        extended_scores_str = redis_client.get('extended_forecast_scores')
        
        if forecast_scores_str:
            forecast_scores = json.loads(forecast_scores_str)
            noaa_regular = sum(1 for score in forecast_scores if score.get('noaaDataUsed'))
            print(f"✓ Regular forecast scores: {len(forecast_scores)} total, {noaa_regular} using NOAA data")
        else:
            print("✗ Regular forecast scores not available")
            return False
        
        if extended_scores_str:
            extended_scores = json.loads(extended_scores_str)
            noaa_extended = sum(1 for score in extended_scores if score.get('noaaDataUsed'))
            print(f"✓ Extended forecast scores: {len(extended_scores)} total, {noaa_extended} using NOAA data")
            
            # Check forecast range
            if extended_scores:
                first_time = extended_scores[0]['timestamp']
                last_time = extended_scores[-1]['timestamp']
                print(f"✓ Extended forecast time range: {first_time} to {last_time}")
        else:
            print("✗ Extended forecast scores not available")
            return False
        
        # Test that we have more extended forecast points than regular
        if len(extended_scores) > len(forecast_scores):
            print(f"✓ Extended forecast provides longer duration ({len(extended_scores)} vs {len(forecast_scores)} hours)")
        else:
            print(f"⚠ Extended forecast may not be longer than regular forecast")
        
        return True
        
    except Exception as e:
        print(f"✗ Forecast integration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("NOAA NWPS Integration Testing Suite")
    print("Testing Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    tests = [
        ("NOAA API Direct Access", test_noaa_api_direct),
        ("NOAA Fetcher Functions", test_noaa_fetcher_functions),
        ("Task Functions", test_task_functions),
        ("Forecast Integration", test_forecast_integration),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! NOAA integration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
