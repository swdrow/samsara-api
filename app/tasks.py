# app/tasks.py
import logging

import json
from datetime import datetime, timedelta
from app.fetchers import fetch_weather_data, fetch_water_data_with_history
from app.rowcast import compute_rowcast, merge_params
# Import the redis_client instance from the extensions file
from app.extensions import redis_client

from datetime import datetime

logger = logging.getLogger(__name__)

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
        # Strip timezone info to compare with naive target_dt
        if prev_dt.tzinfo is not None:
            prev_dt = prev_dt.replace(tzinfo=None)
        if last_dt.tzinfo is not None:
            last_dt = last_dt.replace(tzinfo=None)
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
        logging.exception("Error extrapolating data")
        raise

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
                'gaugeHeight': gauge_pred,
                # Add safety parameters
                'weatherAlerts': forecast_hour.get('weatherAlerts', []),
                'visibility': forecast_hour.get('visibility'),
                'lightningPotential': forecast_hour.get('lightningPotential'),
                'precipitationProbability': forecast_hour.get('precipitationProbability')
            }
            
            score = compute_rowcast(forecast_params)
            
            forecast_scores.append({
                'timestamp': forecast_hour.get('timestamp'),
                'score': score,
                'conditions': forecast_params
            })
        
        # Create simplified scores array with just timestamps and scores
        simple_scores = [
            {
                'timestamp': score['timestamp'],
                'score': score['score']
            }
            for score in forecast_scores
        ]
        
        redis_client.set('forecast_scores', json.dumps(forecast_scores))
        redis_client.set('forecast_scores_simple', json.dumps(simple_scores))
        print("SCHEDULER JOB: Forecast scores updated successfully.")
        
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update forecast scores. Error: {e}")

def update_short_term_forecast_job():
    """Calculates rowcast scores for 15-minute intervals over the next 3 hours."""
    print("SCHEDULER JOB: Running short-term forecast scores update...")
    try:
        from app.fetchers import fetch_short_term_forecast
        
        # Get 15-minute forecast data
        short_term_data = fetch_short_term_forecast()
        
        short_term_scores = []
        
        # Calculate scores for each 15-minute interval
        for interval in short_term_data.get('forecast', []):
            forecast_params = {
                'windSpeed': interval.get('windSpeed'),
                'windGust': interval.get('windGust'),
                'apparentTemp': interval.get('apparentTemp'),
                'uvIndex': interval.get('uvIndex', 0),  # Default to 0 for short-term
                'precipitation': interval.get('precipitation'),
                'discharge': interval.get('discharge'),
                'waterTemp': interval.get('waterTemp'),
                'gaugeHeight': interval.get('gaugeHeight'),
                'weatherAlerts': interval.get('weatherAlerts', []),
                'visibility': interval.get('visibility'),
                'lightningPotential': interval.get('lightningPotential', 0),
                'precipitationProbability': interval.get('precipitationProbability')
            }
            
            score = compute_rowcast(forecast_params)
            
            short_term_scores.append({
                'timestamp': interval.get('timestamp'),
                'score': score,
                'conditions': forecast_params
            })
        
        # Create simplified scores for short-term
        simple_short_term = [
            {
                'timestamp': score['timestamp'],
                'score': score['score']
            }
            for score in short_term_scores
        ]
        
        redis_client.set('short_term_forecast', json.dumps(short_term_scores))
        redis_client.set('short_term_forecast_simple', json.dumps(simple_short_term))
        print(f"SCHEDULER JOB: Short-term forecast scores updated successfully with {len(short_term_scores)} intervals.")
        
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update short-term forecast scores. Error: {e}")
