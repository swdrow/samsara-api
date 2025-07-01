# app/routes.py

from flask import Blueprint, jsonify, request
import json
from datetime import datetime, timedelta
# Import the redis_client instance from the extensions file
from app.extensions import redis_client
from app.rowcast import compute_rowcast, merge_params

# ... rest of the file is the same ...
bp = Blueprint("api", __name__)

def get_data_from_redis(key):
    """Helper function to get and decode data from Redis."""
    data_str = redis_client.get(key)
    if data_str:
        return json.loads(data_str)
    return None

def find_forecast_by_time(forecast_data, target_time):
    """Helper function to find forecast data for a specific time."""
    if not forecast_data:
        return None
    
    target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
    
    closest_forecast = None
    min_diff = float('inf')
    
    for forecast in forecast_data:
        forecast_dt = datetime.fromisoformat(forecast['timestamp'].replace('Z', '+00:00'))
        diff = abs((target_dt - forecast_dt).total_seconds())
        if diff < min_diff:
            min_diff = diff
            closest_forecast = forecast
    
    return closest_forecast

@bp.route("/api/weather")
def weather():
    data = get_data_from_redis('weather_data')
    if data:
        return jsonify(data)
    return jsonify({"error": "Weather data not available yet."}), 404

@bp.route("/api/weather/current")
def current_weather():
    data = get_data_from_redis('weather_data')
    if data and 'current' in data:
        return jsonify(data['current'])
    return jsonify({"error": "Current weather data not available yet."}), 404

@bp.route("/api/weather/forecast")
def weather_forecast():
    data = get_data_from_redis('weather_data')
    if data and 'forecast' in data:
        return jsonify(data['forecast'])
    return jsonify({"error": "Weather forecast data not available yet."}), 404

@bp.route("/api/water")
def water():
    data = get_data_from_redis('water_data')
    if data:
        return jsonify(data)
    return jsonify({"error": "Water data not available yet."}), 404

@bp.route("/api/water/current")
def current_water():
    data = get_data_from_redis('water_data')
    if data and 'current' in data:
        return jsonify(data['current'])
    return jsonify({"error": "Current water data not available yet."}), 404

@bp.route("/api/water/predictions")
def water_predictions():
    data = get_data_from_redis('water_data')
    if data and 'predictions' in data:
        return jsonify(data['predictions'])
    return jsonify({"error": "Water prediction data not available yet."}), 404

@bp.route("/api/rowcast")
def rowcast():
    # Always fetch the latest data from Redis
    weather_data = get_data_from_redis('weather_data')
    water_data = get_data_from_redis('water_data')
    
    if not weather_data or not water_data:
        return jsonify({"error": "Data not available yet, please try again shortly."}), 404

    # Use current data for current rowcast score
    current_weather = weather_data.get('current', {})
    current_water = water_data.get('current', {})
    # Defensive: if current_weather or current_water is empty, force a fresh fetch (if possible)
    if not current_weather or not current_water:
        return jsonify({"error": "Current weather or water data not available yet. Please try again shortly."}), 404
    
    params = merge_params(current_weather, current_water)
    score = compute_rowcast(params)
    return jsonify({ "rowcastScore": score, "params": params })

@bp.route("/api/rowcast/forecast")
def rowcast_forecast():
    forecast_scores = get_data_from_redis('forecast_scores')
    if forecast_scores:
        return jsonify(forecast_scores)
    return jsonify({"error": "Forecast scores not available yet."}), 404

@bp.route("/api/rowcast/forecast/<time_offset>")
def rowcast_forecast_offset(time_offset):
    """Get rowcast score for a specific time offset (e.g., '2h', '30m', '1d')"""
    try:
        # Parse time offset
        if time_offset.endswith('h'):
            hours = int(time_offset[:-1])
            target_time = datetime.now() + timedelta(hours=hours)
        elif time_offset.endswith('m'):
            minutes = int(time_offset[:-1])
            target_time = datetime.now() + timedelta(minutes=minutes)
        elif time_offset.endswith('d'):
            days = int(time_offset[:-1])
            target_time = datetime.now() + timedelta(days=days)
        else:
            return jsonify({"error": "Invalid time format. Use format like '2h', '30m', '1d'"}), 400
        
        forecast_scores = get_data_from_redis('forecast_scores')
        if not forecast_scores:
            return jsonify({"error": "Forecast scores not available yet."}), 404
        
        # Find closest forecast to target time
        closest_forecast = find_forecast_by_time(forecast_scores, target_time.isoformat())
        
        if closest_forecast:
            return jsonify(closest_forecast)
        else:
            return jsonify({"error": "No forecast data available for requested time"}), 404
            
    except ValueError:
        return jsonify({"error": "Invalid time format. Use format like '2h', '30m', '1d'"}), 400

@bp.route("/api/rowcast/at/<timestamp>")
def rowcast_at_time(timestamp):
    """Get rowcast score for a specific timestamp"""
    try:
        forecast_scores = get_data_from_redis('forecast_scores')
        if not forecast_scores:
            return jsonify({"error": "Forecast scores not available yet."}), 404
        
        # Find closest forecast to specified timestamp
        closest_forecast = find_forecast_by_time(forecast_scores, timestamp)
        
        if closest_forecast:
            return jsonify(closest_forecast)
        else:
            return jsonify({"error": "No forecast data available for requested time"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Invalid timestamp format: {str(e)}"}), 400

@bp.route("/api/complete")
def complete_data():
    """Get all current data, forecasts, and scores in one response"""
    weather_data = get_data_from_redis('weather_data')
    water_data = get_data_from_redis('water_data')
    forecast_scores = get_data_from_redis('forecast_scores')
    
    # Calculate current rowcast score
    current_score = None
    if weather_data and water_data:
        current_weather = weather_data.get('current', {})
        current_water = water_data.get('current', {})
        params = merge_params(current_weather, current_water)
        current_score = compute_rowcast(params)
    
    response = {
        "current": {
            "weather": weather_data.get('current') if weather_data else None,
            "water": water_data.get('current') if water_data else None,
            "rowcastScore": current_score
        },
        "forecast": {
            "weather": weather_data.get('forecast') if weather_data else None,
            "water": water_data.get('predictions') if water_data else None,
            "rowcastScores": forecast_scores
        },
        "lastUpdated": datetime.now().isoformat()
    }
    
    return jsonify(response)