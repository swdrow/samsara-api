# app/tasks.py

import json
from app.fetchers import fetch_weather_data, fetch_water_data
# Import the redis_client instance from the extensions file
from app.extensions import redis_client

# ... rest of the file is the same ...
def update_weather_data_job():
    """Fetches new weather data and stores it in Redis."""
    print("SCHEDULER JOB: Running weather data update...")
    try:
        data = fetch_weather_data()
        redis_client.set('weather_data', json.dumps(data))
        print("SCHEDULER JOB: Weather data updated successfully.")
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update weather data. Error: {e}")

def update_water_data_job():
    """Fetches new water data and stores it in Redis."""
    print("SCHEDULER JOB: Running water data update...")
    try:
        data = fetch_water_data()
        redis_client.set('water_data', json.dumps(data))
        print("SCHEDULER JOB: Water data updated successfully.")
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update water data. Error: {e}")