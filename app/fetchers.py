# app/fetchers.py

import requests
import json
import os
from app.utils import fmt, deg_to_cardinal

# The file cache logic has been removed and is now handled by Redis.

def fetch_water_data():
    """Fetches the latest water data from the USGS API."""
    print("FETCHER: Calling USGS Water Services API...")
    site_id = "01474500"
    params = "00010,00065,00060"
    url = f"https://waterservices.usgs.gov/nwis/iv/?sites={site_id}&parameterCd={params}&format=json"
    data = requests.get(url).json()
    out = {'gaugeHeight': None, 'waterTemp': None, 'discharge': None}
    for series in data.get('value', {}).get('timeSeries', []):
        name = series['variable']['variableName'].lower()
        # Ensure values exist before trying to access them
        try:
            val = series['values'][0]['value'][0]['value']
            if 'gage height' in name:
                out['gaugeHeight'] = float(val)
            elif 'temperature' in name:
                out['waterTemp'] = float(val) * 1.8 + 32
            elif 'discharge' in name or 'flow' in name:
                out['discharge'] = int(float(val))
        except (IndexError, KeyError):
            # This handles cases where a time series has no value data
            continue
    return out

def fetch_weather_data():
    """Fetches the latest weather data from the Open-Meteo API."""
    print("FETCHER: Calling Open-Meteo API...")
    lat, lon = 39.8682, -75.5916
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,wind_speed_10m,"  
        "wind_direction_10m,wind_gusts_10m,precipitation,uv_index"
        "&windspeed_unit=mph&temperature_unit=fahrenheit"
        "&timezone=America/New_York&forecast_days=1"
    )
    data = requests.get(url).json()
    current = data.get("current", {})
    # Convert wind direction to cardinal
    deg = current.get('wind_direction_10m')
    wind_dir = f"{deg_to_cardinal(deg)} ({fmt(deg, 0, '°')})"
    out = {
        'windSpeed': current.get('wind_speed_10m'),
        'windGust': current.get('wind_gusts_10m'),
        'windDir': wind_dir,
        'apparentTemp': current.get('apparent_temperature'),
        'uvIndex': current.get('uv_index'),
        'precipitation': current.get('precipitation'),
        'currentTemp': current.get('temperature_2m')
    }
    return out