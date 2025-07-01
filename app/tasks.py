# app/tasks.py

import json
from datetime import datetime, timedelta
from app.fetchers import fetch_weather_data, fetch_water_data_with_history
from app.rowcast import compute_rowcast, merge_params
# Import the redis_client instance from the extensions file
from app.extensions import redis_client

from datetime import datetime

def extrapolate(historical_list, current_value, target_dt):
    """Extrapolate a value based on the last two historical points within 3 hours"""
    try:
        if not historical_list or current_value is None or len(historical_list) < 2:
            return current_value
        # Sort by timestamp
        sorted_list = sorted(historical_list, key=lambda x: x['timestamp'])
        prev = sorted_list[-2]
        last = sorted_list[-1]
        prev_dt = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
        last_dt = datetime.fromisoformat(last['timestamp'].replace('Z', '+00:00'))
        time_diff = (last_dt - prev_dt).total_seconds()
        if time_diff == 0:
            return current_value
        slope = (last['value'] - prev['value']) / time_diff
        delta_sec = (target_dt - last_dt).total_seconds()
        # Only extrapolate within 3 hours
        if abs(delta_sec) <= 3 * 3600:
            return last['value'] + slope * delta_sec
        return current_value
    except Exception:
        return current_value

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
    """Fetches new water data with historical data and stores it in Redis."""
    print("SCHEDULER JOB: Running water data update...")
    try:
        data = fetch_water_data_with_history()
        # Store only current and historical data; projections will be computed dynamically
        water_data = {
            'current': data['current'],
            'historical': data['historical']
        }
        
        redis_client.set('water_data', json.dumps(water_data))
        print("SCHEDULER JOB: Water data updated successfully.")
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update water data. Error: {e}")

def update_forecast_scores_job():
    """Calculates rowcast scores for weather forecast periods."""
    print("SCHEDULER JOB: Running forecast scores update...")
    try:
        # Get weather and water data
        weather_data_str = redis_client.get('weather_data')
        water_data_str = redis_client.get('water_data')
        
        if not weather_data_str or not water_data_str:
            print("SCHEDULER JOB: Missing weather or water data for forecast calculation")
            return
            
        weather_data = json.loads(weather_data_str)
        water_data = json.loads(water_data_str)
        
        forecast_scores = []
        
        # Calculate scores for each forecast hour
        for forecast_hour in weather_data.get('forecast', []):
            # Project water parameters based on recent trends
            timestamp = forecast_hour.get('timestamp')
            target_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            current_water = water_data.get('current', {})
            hist = water_data.get('historical', {})
            # Extrapolate each water metric
            discharge_pred = extrapolate(hist.get('discharge', []), current_water.get('discharge'), target_dt)
            gauge_pred = extrapolate(hist.get('gaugeHeight', []), current_water.get('gaugeHeight'), target_dt)
            temp_pred = extrapolate(hist.get('waterTemp', []), current_water.get('waterTemp'), target_dt)
            water_prediction = {
                'discharge': discharge_pred,
                'gaugeHeight': gauge_pred,
                'waterTemp': temp_pred
            }
            
            forecast_params = {
                'windSpeed': forecast_hour.get('windSpeed'),
                'windGust': forecast_hour.get('windGust'),
                'apparentTemp': forecast_hour.get('apparentTemp'),
                'uvIndex': forecast_hour.get('uvIndex'),
                'precipitation': forecast_hour.get('precipitation'),
                # Use dynamic projections for water
                'discharge': discharge_pred,
                'waterTemp': temp_pred,
                'gaugeHeight': gauge_pred
            }
            
            score = compute_rowcast(forecast_params)
            
            forecast_scores.append({
                'timestamp': forecast_hour.get('timestamp'),
                'score': score,
                'conditions': forecast_params
            })
        
        redis_client.set('forecast_scores', json.dumps(forecast_scores))
        print("SCHEDULER JOB: Forecast scores updated successfully.")
        
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update forecast scores. Error: {e}")