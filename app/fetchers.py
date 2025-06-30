import requests
import json
import os
from time import time
from app.utils import fmt, deg_to_cardinal

CACHE_PATH = "/tmp/rowcast_cache"
os.makedirs(CACHE_PATH, exist_ok=True)

def load_cache(key, ttl=300):
    path = os.path.join(CACHE_PATH, f"{key}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        obj = json.load(f)
    if time() - obj.get("timestamp", 0) > ttl:
        return None
    return obj.get("data")

def save_cache(key, data):
    with open(os.path.join(CACHE_PATH, f"{key}.json"), "w") as f:
        json.dump({ "timestamp": time(), "data": data }, f)

def fetch_water_data():
    cached = load_cache("water", ttl=10)
    if cached:
        return cached
    site_id = "01474500"
    params = "00010,00065,00060"
    url = f"https://waterservices.usgs.gov/nwis/iv/?sites={site_id}&parameterCd={params}&format=json"
    data = requests.get(url).json()
    out = {'gaugeHeight': None, 'waterTemp': None, 'discharge': None}
    for series in data.get('value', {}).get('timeSeries', []):
        name = series['variable']['variableName'].lower()
        val = series['values'][0]['value'][0]['value']
        if 'gage height' in name:
            out['gaugeHeight'] = float(val)
        elif 'temperature' in name:
            out['waterTemp'] = float(val) * 1.8 + 32
        elif 'discharge' in name or 'flow' in name:
            # discharge may appear under different variable names
            out['discharge'] = int(float(val))
    save_cache("water", out)
    return out

def fetch_weather_data():
    cached = load_cache("weather")
    if cached:
        return cached
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
    save_cache("weather", out)
    return out