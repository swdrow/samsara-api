#!/usr/bin/env python3
"""
Test script to verify API functionality
"""

import requests
import time
import pytest

BASE_URL = "http://localhost:5000/api"

def test_endpoint(endpoint, description):
    """Test a single API endpoint"""
    try:
        print(f"\n--- Testing {description} ---")
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"Status: {response.status_code}")
        assert response.status_code == 200, f"Endpoint {endpoint} failed: {response.text}"
        return response.json()
    except Exception as e:
        pytest.fail(f"Failed to test {endpoint}: {e}")

@pytest.fixture(scope="session", autouse=True)
def wait_for_data():
    """Wait for initial data fetch before running tests."""
    print("\nWaiting 30 seconds for initial data fetch...")
    time.sleep(30)

def test_weather_full():
    data = test_endpoint("/weather", "Weather Data (Full)")
    assert "current" in data and "forecast" in data

def test_weather_current():
    test_endpoint("/weather/current", "Current Weather")

def test_weather_forecast():
    test_endpoint("/weather/forecast", "Weather Forecast")

def test_water_full():
    data = test_endpoint("/water", "Water Data (Full)")
    assert "current" in data and "predictions" in data

def test_water_current():
    test_endpoint("/water/current", "Current Water Data")

def test_water_predictions():
    test_endpoint("/water/predictions", "Water Predictions")

def test_rowcast_current():
    test_endpoint("/rowcast", "Current RowCast Score")

def test_rowcast_forecast():
    test_endpoint("/rowcast/forecast", "RowCast Forecast")

def test_complete_data():
    test_endpoint("/complete", "Complete Data")

if __name__ == "__main__":
    pytest.main([__file__])
