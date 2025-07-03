# app/tasks.py
import logging
import json
from datetime import datetime, timedelta
from app.fetchers import fetch_weather_data, fetch_water_data_with_history, fetch_noaa_stageflow_forecast, fetch_extended_weather_forecast
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
    """Calculates rowcast scores for weather forecast periods, using NOAA data when available."""
    print("SCHEDULER JOB: Running forecast scores update...")
    try:
        # Get weather and water data
        weather_data_str = redis_client.get('weather_data')
        water_data_str = redis_client.get('water_data')
        noaa_stageflow_str = redis_client.get('noaa_stageflow_data')
        
        if not weather_data_str or not water_data_str:
            print("SCHEDULER JOB: Missing weather or water data for forecast calculation")
            return
            
        weather_data = json.loads(weather_data_str)
        water_data = json.loads(water_data_str)
        noaa_stageflow = json.loads(noaa_stageflow_str) if noaa_stageflow_str else None
        
        # Create a lookup dictionary for NOAA stageflow forecast data by timestamp
        # Handle timezone differences and find closest matches
        noaa_forecast_lookup = {}
        if noaa_stageflow and noaa_stageflow.get('forecast'):
            for noaa_point in noaa_stageflow['forecast']:
                timestamp = noaa_point.get('timestamp')
                if timestamp:
                    # Normalize timestamp format for matching
                    try:
                        # Parse NOAA timestamp (with Z timezone)
                        noaa_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        # Create lookup key without timezone for matching
                        lookup_key = noaa_dt.replace(tzinfo=None).isoformat()
                        noaa_forecast_lookup[lookup_key] = noaa_point
                    except Exception:
                        # Fallback to direct timestamp matching
                        noaa_forecast_lookup[timestamp] = noaa_point
        
        forecast_scores = []
        
        # Calculate scores for each forecast hour
        for forecast_hour in weather_data.get('forecast', []):
            timestamp = forecast_hour.get('timestamp')
            target_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            current_water = water_data.get('current', {})
            hist = water_data.get('historical', {})
            
            # Try to get NOAA stageflow data for this timestamp
            # Handle timezone differences in timestamp matching
            noaa_data = None
            try:
                # Parse weather timestamp (no timezone)
                weather_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if weather_dt.tzinfo:
                    weather_dt = weather_dt.replace(tzinfo=None)
                
                # Try exact match first
                lookup_key = weather_dt.isoformat()
                noaa_data = noaa_forecast_lookup.get(lookup_key)
                
                # If no exact match, find closest timestamp within 1 hour
                if not noaa_data:
                    closest_diff = float('inf')
                    for noaa_key, noaa_point in noaa_forecast_lookup.items():
                        try:
                            noaa_dt = datetime.fromisoformat(noaa_key)
                            diff = abs((weather_dt - noaa_dt).total_seconds())
                            if diff < closest_diff and diff <= 3600:  # Within 1 hour
                                closest_diff = diff
                                noaa_data = noaa_point
                        except Exception:
                            continue
            except Exception:
                # Fallback to direct lookup
                noaa_data = noaa_forecast_lookup.get(timestamp)
            
            # Use NOAA data if available, otherwise fall back to extrapolation
            if noaa_data:
                discharge_pred = noaa_data.get('discharge')
                gauge_pred = noaa_data.get('gaugeHeight')
                # Water temp not available from NOAA, extrapolate
                temp_pred = extrapolate(hist.get('waterTemp', []), current_water.get('waterTemp'), target_dt)
                noaa_used = True
            else:
                # Extrapolate each water metric
                discharge_pred = extrapolate(hist.get('discharge', []), current_water.get('discharge'), target_dt)
                gauge_pred = extrapolate(hist.get('gaugeHeight', []), current_water.get('gaugeHeight'), target_dt)
                temp_pred = extrapolate(hist.get('waterTemp', []), current_water.get('waterTemp'), target_dt)
                noaa_used = False
            
            forecast_params = {
                'windSpeed': forecast_hour.get('windSpeed'),
                'windGust': forecast_hour.get('windGust'),
                'apparentTemp': forecast_hour.get('apparentTemp'),
                'uvIndex': forecast_hour.get('uvIndex'),
                'precipitation': forecast_hour.get('precipitation'),
                # Use NOAA data or dynamic projections for water
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
                'conditions': forecast_params,
                'noaaDataUsed': noaa_used
            })
        
        # Create simplified scores array with just timestamps and scores
        simple_scores = [
            {
                'timestamp': score['timestamp'],
                'score': score['score'],
                'noaaDataUsed': score.get('noaaDataUsed', False)
            }
            for score in forecast_scores
        ]
        
        redis_client.set('forecast_scores', json.dumps(forecast_scores))
        redis_client.set('forecast_scores_simple', json.dumps(simple_scores))
        
        noaa_count = sum(1 for score in forecast_scores if score.get('noaaDataUsed'))
        print(f"SCHEDULER JOB: Forecast scores updated successfully with {len(forecast_scores)} hours ({noaa_count} using NOAA data).")
        
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

def update_noaa_stageflow_job():
    """Fetches NOAA NWPS stageflow forecast data and stores it in Redis."""
    print("SCHEDULER JOB: Running NOAA stageflow data update...")
    try:
        data = fetch_noaa_stageflow_forecast()
        redis_client.set('noaa_stageflow_data', json.dumps(data))
        print(f"SCHEDULER JOB: NOAA stageflow data updated successfully with {len(data.get('forecast', []))} forecast hours.")
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update NOAA stageflow data. Error: {e}")

def update_extended_weather_data_job():
    """Fetches extended weather forecast data (7 days) and stores it in Redis."""
    print("SCHEDULER JOB: Running extended weather data update...")
    try:
        data = fetch_extended_weather_forecast()
        redis_client.set('extended_weather_data', json.dumps(data))
        print(f"SCHEDULER JOB: Extended weather data updated successfully with {len(data.get('forecast', []))} forecast hours.")
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update extended weather data. Error: {e}")

def update_extended_forecast_scores_job():
    """Calculates rowcast scores for extended forecast periods using NOAA stageflow and extended weather data."""
    print("SCHEDULER JOB: Running extended forecast scores update...")
    try:
        # Get extended weather and NOAA stageflow data
        extended_weather_str = redis_client.get('extended_weather_data')
        noaa_stageflow_str = redis_client.get('noaa_stageflow_data')
        
        if not extended_weather_str:
            print("SCHEDULER JOB: Missing extended weather data for extended forecast calculation")
            return
            
        extended_weather = json.loads(extended_weather_str)
        noaa_stageflow = json.loads(noaa_stageflow_str) if noaa_stageflow_str else None
        
        # Create a lookup dictionary for NOAA stageflow forecast data by timestamp
        # Handle timezone differences and find closest matches
        noaa_forecast_lookup = {}
        if noaa_stageflow and noaa_stageflow.get('forecast'):
            for noaa_point in noaa_stageflow['forecast']:
                timestamp = noaa_point.get('timestamp')
                if timestamp:
                    # Normalize timestamp format for matching
                    try:
                        # Parse NOAA timestamp (with Z timezone)
                        noaa_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        # Create lookup key without timezone for matching
                        lookup_key = noaa_dt.replace(tzinfo=None).isoformat()
                        noaa_forecast_lookup[lookup_key] = noaa_point
                    except Exception:
                        # Fallback to direct timestamp matching
                        noaa_forecast_lookup[timestamp] = noaa_point
        
        extended_forecast_scores = []
        
        # Calculate scores for each extended forecast hour
        for forecast_hour in extended_weather.get('forecast', []):
            timestamp = forecast_hour.get('timestamp')
            
            # Try to get NOAA stageflow data for this timestamp
            # Handle timezone differences in timestamp matching
            noaa_data = None
            try:
                # Parse weather timestamp (no timezone)
                weather_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if weather_dt.tzinfo:
                    weather_dt = weather_dt.replace(tzinfo=None)
                
                # Try exact match first
                lookup_key = weather_dt.isoformat()
                noaa_data = noaa_forecast_lookup.get(lookup_key)
                
                # If no exact match, find closest timestamp within 1 hour
                if not noaa_data:
                    closest_diff = float('inf')
                    for noaa_key, noaa_point in noaa_forecast_lookup.items():
                        try:
                            noaa_dt = datetime.fromisoformat(noaa_key)
                            diff = abs((weather_dt - noaa_dt).total_seconds())
                            if diff < closest_diff and diff <= 3600:  # Within 1 hour
                                closest_diff = diff
                                noaa_data = noaa_point
                        except Exception:
                            continue
            except Exception:
                # Fallback to direct lookup
                noaa_data = noaa_forecast_lookup.get(timestamp)
            
            # Use NOAA data if available, otherwise fall back to extrapolation
            if noaa_data:
                discharge = noaa_data.get('discharge')
                gauge_height = noaa_data.get('gaugeHeight')
                water_temp = None  # NOAA doesn't provide water temp, we'll need to extrapolate
                
                # For water temp, extrapolate from current water data if available
                water_data_str = redis_client.get('water_data')
                if water_data_str:
                    water_data = json.loads(water_data_str)
                    target_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    current_water = water_data.get('current', {})
                    hist = water_data.get('historical', {})
                    water_temp = extrapolate(hist.get('waterTemp', []), current_water.get('waterTemp'), target_dt)
            else:
                # Fall back to extrapolation if no NOAA data
                water_data_str = redis_client.get('water_data')
                if water_data_str:
                    water_data = json.loads(water_data_str)
                    target_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    current_water = water_data.get('current', {})
                    hist = water_data.get('historical', {})
                    discharge = extrapolate(hist.get('discharge', []), current_water.get('discharge'), target_dt)
                    gauge_height = extrapolate(hist.get('gaugeHeight', []), current_water.get('gaugeHeight'), target_dt)
                    water_temp = extrapolate(hist.get('waterTemp', []), current_water.get('waterTemp'), target_dt)
                else:
                    discharge = None
                    gauge_height = None
                    water_temp = None
            
            forecast_params = {
                'windSpeed': forecast_hour.get('windSpeed'),
                'windGust': forecast_hour.get('windGust'),
                'apparentTemp': forecast_hour.get('apparentTemp'),
                'uvIndex': forecast_hour.get('uvIndex'),
                'precipitation': forecast_hour.get('precipitation'),
                'discharge': discharge,
                'waterTemp': water_temp,
                'gaugeHeight': gauge_height,
                'weatherAlerts': forecast_hour.get('weatherAlerts', []),
                'visibility': forecast_hour.get('visibility'),
                'lightningPotential': forecast_hour.get('lightningPotential'),
                'precipitationProbability': forecast_hour.get('precipitationProbability')
            }
            
            score = compute_rowcast(forecast_params)
            
            extended_forecast_scores.append({
                'timestamp': forecast_hour.get('timestamp'),
                'score': score,
                'conditions': forecast_params,
                'noaaDataUsed': noaa_data is not None
            })
        
        # Create simplified scores array with just timestamps and scores
        simple_extended_scores = [
            {
                'timestamp': score['timestamp'],
                'score': score['score'],
                'noaaDataUsed': score.get('noaaDataUsed', False)
            }
            for score in extended_forecast_scores
        ]
        
        redis_client.set('extended_forecast_scores', json.dumps(extended_forecast_scores))
        redis_client.set('extended_forecast_scores_simple', json.dumps(simple_extended_scores))
        
        noaa_count = sum(1 for score in extended_forecast_scores if score.get('noaaDataUsed'))
        print(f"SCHEDULER JOB: Extended forecast scores updated successfully with {len(extended_forecast_scores)} hours ({noaa_count} using NOAA data).")
        
    except Exception as e:
        print(f"SCHEDULER JOB: Failed to update extended forecast scores. Error: {e}")
