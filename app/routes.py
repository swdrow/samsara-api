# app/routes.py

from flask import Blueprint, jsonify, request
import json
from datetime import datetime, timedelta
import pytz
# Import the redis_client instance from the extensions file
from app.extensions import redis_client
from app.rowcast import compute_rowcast, merge_params

# EST timezone
EST = pytz.timezone('America/New_York')

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

@bp.route("/api/rowcast/forecast/simple")
def rowcast_forecast_simple():
    """Get simplified rowcast forecast with just timestamps and scores"""
    simple_scores = get_data_from_redis('forecast_scores_simple')
    if simple_scores:
        return jsonify(simple_scores)
    return jsonify({"error": "Simple forecast scores not available yet."}), 404

@bp.route("/api/rowcast/forecast/<time_offset>")
def rowcast_forecast_offset(time_offset):
    """Get rowcast score for a specific time offset (e.g., '2h', '30m', '1d')"""
    try:
        # Parse time offset using EST timezone
        now_est = datetime.now(EST)
        if time_offset.endswith('h'):
            hours = int(time_offset[:-1])
            target_time = now_est + timedelta(hours=hours)
        elif time_offset.endswith('m'):
            minutes = int(time_offset[:-1])
            target_time = now_est + timedelta(minutes=minutes)
        elif time_offset.endswith('d'):
            days = int(time_offset[:-1])
            target_time = now_est + timedelta(days=days)
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

@bp.route("/api/rowcast/forecast/short-term")
def rowcast_short_term_forecast():
    """Get 15-minute interval rowcast forecast for the next 3 hours"""
    short_term_scores = get_data_from_redis('short_term_forecast')
    if short_term_scores:
        return jsonify(short_term_scores)
    return jsonify({"error": "Short-term forecast scores not available yet."}), 404

@bp.route("/api/rowcast/forecast/short-term/simple")
def rowcast_short_term_forecast_simple():
    """Get simplified 15-minute interval rowcast forecast with just timestamps and scores"""
    simple_short_term = get_data_from_redis('short_term_forecast_simple')
    if simple_short_term:
        return jsonify(simple_short_term)
    return jsonify({"error": "Simple short-term forecast scores not available yet."}), 404

@bp.route("/api/noaa/stageflow")
def noaa_stageflow():
    """Returns NOAA NWPS stageflow forecast data."""
    data = get_data_from_redis('noaa_stageflow_data')
    if data:
        return jsonify(data)
    return jsonify({"error": "NOAA stageflow data not available yet."}), 404

@bp.route("/api/noaa/stageflow/current")
def noaa_stageflow_current():
    """Returns current observed NOAA stageflow data."""
    data = get_data_from_redis('noaa_stageflow_data')
    if data and data.get('current'):
        return jsonify(data['current'])
    return jsonify({"error": "Current NOAA stageflow data not available yet."}), 404

@bp.route("/api/noaa/stageflow/forecast")
def noaa_stageflow_forecast():
    """Returns NOAA stageflow forecast data only."""
    data = get_data_from_redis('noaa_stageflow_data')
    if data and data.get('forecast'):
        return jsonify(data['forecast'])
    return jsonify({"error": "NOAA stageflow forecast data not available yet."}), 404

@bp.route("/api/weather/extended")
def weather_extended():
    """Returns extended weather forecast data (7 days)."""
    data = get_data_from_redis('extended_weather_data')
    if data:
        return jsonify(data)
    return jsonify({"error": "Extended weather data not available yet."}), 404

@bp.route("/api/rowcast/forecast/extended")
def rowcast_forecast_extended():
    """Returns extended RowCast forecast scores (up to 7 days) using NOAA stageflow data."""
    data = get_data_from_redis('extended_forecast_scores')
    if data:
        return jsonify(data)
    return jsonify({"error": "Extended forecast scores not available yet."}), 404

@bp.route("/api/rowcast/forecast/extended/simple")
def rowcast_forecast_extended_simple():
    """Returns simplified extended RowCast forecast scores (timestamp and score only)."""
    data = get_data_from_redis('extended_forecast_scores_simple')
    if data:
        return jsonify(data)
    return jsonify({"error": "Extended forecast scores not available yet."}), 404

@bp.route("/api/complete/extended")
def complete_extended():
    """Returns all data including extended forecasts for comprehensive dashboard."""
    try:
        # Get all data sources
        weather_data = get_data_from_redis('weather_data')
        extended_weather_data = get_data_from_redis('extended_weather_data')
        water_data = get_data_from_redis('water_data')
        noaa_stageflow_data = get_data_from_redis('noaa_stageflow_data')
        forecast_scores = get_data_from_redis('forecast_scores')
        extended_forecast_scores = get_data_from_redis('extended_forecast_scores')
        short_term_forecast = get_data_from_redis('short_term_forecast')
        
        response = {
            'weather': {
                'current': weather_data.get('current') if weather_data else None,
                'forecast': weather_data.get('forecast') if weather_data else [],
                'extended': extended_weather_data.get('forecast') if extended_weather_data else [],
                'alerts': weather_data.get('alerts') if weather_data else []
            },
            'water': {
                'current': water_data.get('current') if water_data else None,
                'historical': water_data.get('historical') if water_data else {}
            },
            'noaa': {
                'current': noaa_stageflow_data.get('current') if noaa_stageflow_data else None,
                'observed': noaa_stageflow_data.get('observed') if noaa_stageflow_data else [],
                'forecast': noaa_stageflow_data.get('forecast') if noaa_stageflow_data else [],
                'metadata': noaa_stageflow_data.get('metadata') if noaa_stageflow_data else {}
            },
            'rowcast': {
                'current': None,
                'forecast': forecast_scores or [],
                'extendedForecast': extended_forecast_scores or [],
                'shortTerm': short_term_forecast or []
            },
            'metadata': {
                'lastUpdated': datetime.now(EST).isoformat(),
                'timezone': 'America/New_York',
                'dataAvailability': {
                    'weather': weather_data is not None,
                    'extendedWeather': extended_weather_data is not None,
                    'water': water_data is not None,
                    'noaaStageflow': noaa_stageflow_data is not None,
                    'forecast': forecast_scores is not None,
                    'extendedForecast': extended_forecast_scores is not None,
                    'shortTermForecast': short_term_forecast is not None
                }
            }
        }
        
        # Calculate current rowcast if we have current data
        if weather_data and weather_data.get('current'):
            current_water = water_data.get('current') if water_data else {}
            noaa_current = noaa_stageflow_data.get('current') if noaa_stageflow_data else {}
            
            # Use NOAA data if available, otherwise use current water data
            current_params = {
                'windSpeed': weather_data['current'].get('windSpeed'),
                'windGust': weather_data['current'].get('windGust'),
                'apparentTemp': weather_data['current'].get('apparentTemp'),
                'uvIndex': weather_data['current'].get('uvIndex'),
                'precipitation': weather_data['current'].get('precipitation'),
                'discharge': noaa_current.get('discharge') or current_water.get('discharge'),
                'waterTemp': current_water.get('waterTemp'),  # NOAA doesn't provide water temp
                'gaugeHeight': noaa_current.get('gaugeHeight') or current_water.get('gaugeHeight'),
                'weatherAlerts': weather_data['current'].get('weatherAlerts', []),
                'visibility': weather_data['current'].get('visibility'),
                'lightningPotential': 0,  # Not available in current weather
                'precipitationProbability': 0  # Not available in current weather
            }
            
            response['rowcast']['current'] = {
                'score': compute_rowcast(current_params),
                'conditions': current_params,
                'timestamp': weather_data['current'].get('timestamp'),
                'noaaDataUsed': noaa_current.get('discharge') is not None or noaa_current.get('gaugeHeight') is not None
            }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Failed to compile extended data: {str(e)}"}), 500

@bp.route("/")
@bp.route("/docs")
@bp.route("/api")
def api_documentation():
    """API Documentation - Shows all available endpoints and usage"""
    docs = {
        "title": "RowCast API Documentation",
        "description": "API for rowing condition scores based on weather, water conditions, and safety factors",
        "timezone": "America/New_York (EST/EDT)",
        "version": "1.0",
        "documentation": {
            "html": "Visit /documentation or /docs/html for beautifully formatted documentation",
            "json": "This endpoint provides machine-readable API documentation"
        },
        "endpoints": {
            "current_conditions": {
                "/api/weather": "Current weather data",
                "/api/weather/current": "Current weather only",
                "/api/water": "Current water data with historical",
                "/api/water/current": "Current water conditions only",
                "/api/rowcast": "Current rowcast score with conditions"
            },
            "forecasts": {
                "/api/weather/forecast": "Weather forecast (24 hours, hourly)",
                "/api/weather/extended": "Extended weather forecast (7 days)",
                "/api/rowcast/forecast": "Detailed rowcast forecast (24 hours, hourly)",
                "/api/rowcast/forecast/simple": "Simple rowcast forecast - timestamps and scores only",
                "/api/rowcast/forecast/extended": "Extended RowCast forecast using NOAA data (up to 7 days)",
                "/api/rowcast/forecast/extended/simple": "Simple extended RowCast forecast - timestamps and scores only",
                "/api/rowcast/forecast/short-term": "Detailed 15-minute forecast (3 hours)",
                "/api/rowcast/forecast/short-term/simple": "Simple 15-minute forecast - timestamps and scores only"
            },
            "noaa_data": {
                "/api/noaa/stageflow": "Full NOAA NWPS stageflow data (observed and forecast)",
                "/api/noaa/stageflow/current": "Current observed stageflow from NOAA",
                "/api/noaa/stageflow/forecast": "NOAA stageflow forecast data only"
            },
            "time_based_queries": {
                "/api/rowcast/forecast/<time_offset>": {
                    "description": "Get forecast for specific time offset from now",
                    "examples": [
                        "/api/rowcast/forecast/2h - 2 hours from now",
                        "/api/rowcast/forecast/30m - 30 minutes from now", 
                        "/api/rowcast/forecast/1d - 1 day from now"
                    ]
                },
                "/api/rowcast/at/<timestamp>": {
                    "description": "Get forecast for specific timestamp",
                    "format": "YYYY-MM-DDTHH:MM",
                    "example": "/api/rowcast/at/2025-07-01T16:00"
                }
            },
            "complete_data": {
                "/api/complete": "All current data, forecasts, and scores in one response",
                "/api/complete/extended": "All data including extended forecasts and NOAA stageflow for comprehensive dashboard"
            },
            "dashboard": {
                "/dashboard": "Visual dashboard showing all data in easy-to-read format",
                "/data": "Alternative URL for the visual dashboard"
            },
            "dashboard": {
                "/dashboard": "Interactive web dashboard showing all data and forecasts",
                "/data": "Alias for dashboard - comprehensive data visualization"
            }
        },
        "scoring_factors": {
            "weather": ["Temperature (74-85°F optimal)", "Wind speed/gusts", "Precipitation", "UV index", "Visibility"],
            "water": ["Discharge/flow rate", "Water temperature", "Gauge height"],
            "safety": ["Weather alerts", "Lightning potential", "Severe weather conditions"]
        },
        "score_range": "0-10 (10 = perfect conditions, 0 = dangerous/unsuitable)",
        "data_updates": {
            "weather": "Every 10 minutes",
            "extended_weather": "Every 60 minutes",
            "water": "Every 15 minutes", 
            "noaa_stageflow": "Every 30 minutes",
            "forecasts": "Every 10 minutes",
            "extended_forecasts": "Every 30 minutes"
        },
        "response_formats": {
            "detailed": "Includes all conditions and parameters used in scoring",
            "simple": "Timestamps and scores only for lightweight applications"
        }
    }
    
    return jsonify(docs)

@bp.route("/docs/html")
@bp.route("/documentation")
def api_documentation_html():
    """Serve HTML formatted API documentation"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RowCast API Documentation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            color: #e2e8f0; 
            background: #0f1419;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(79, 70, 229, 0.3);
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header p { font-size: 1.2rem; opacity: 0.9; }
        .section { 
            background: #1a202c; 
            margin-bottom: 2rem; 
            padding: 2rem; 
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            border: 1px solid #2d3748;
        }
        .section h2 { 
            color: #60a5fa; 
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #374151;
        }
        .section h3 { 
            color: #a5b4fc; 
            margin: 1.5rem 0 1rem 0;
            padding: 0.5rem;
            background: #111827;
            border-left: 4px solid #4f46e5;
            border-radius: 3px;
        }
        .endpoint { 
            background: #111827; 
            padding: 1rem; 
            margin: 1rem 0; 
            border-radius: 5px;
            border-left: 4px solid #10b981;
            border: 1px solid #374151;
        }
        .method { 
            background: #10b981; 
            color: white; 
            padding: 0.2rem 0.5rem; 
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-right: 0.5rem;
        }
        .url { 
            font-family: 'Monaco', 'Consolas', monospace; 
            background: #374151; 
            color: #fbbf24;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        pre { 
            background: #0f172a; 
            color: #e2e8f0; 
            padding: 1rem; 
            border-radius: 5px;
            overflow-x: auto;
            margin: 1rem 0;
            border: 1px solid #334155;
        }
        .json { font-family: 'Monaco', 'Consolas', monospace; }
        .info-box {
            background: #1e3a8a;
            border: 1px solid #3b82f6;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
            color: #dbeafe;
        }
        .warning-box {
            background: #92400e;
            border: 1px solid #f59e0b;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
            color: #fef3c7;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .card {
            background: #111827;
            padding: 1rem;
            border-radius: 5px;
            border-left: 4px solid #4f46e5;
            border: 1px solid #374151;
        }
        .card h4 {
            color: #a5b4fc;
            margin-bottom: 0.5rem;
        }
        .toc {
            background: #111827;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
            border: 1px solid #374151;
        }
        .toc ul { list-style: none; padding-left: 1rem; }
        .toc a { text-decoration: none; color: #60a5fa; }
        .toc a:hover { text-decoration: underline; color: #93c5fd; }
        table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
        th, td { 
            padding: 0.75rem; 
            text-align: left; 
            border-bottom: 1px solid #374151; 
        }
        th { 
            background: #111827; 
            font-weight: 600; 
            color: #a5b4fc;
        }
        .status-code { 
            padding: 0.2rem 0.5rem; 
            border-radius: 3px; 
            font-family: monospace;
            font-weight: bold;
        }
        .status-200 { background: #065f46; color: #6ee7b7; }
        .status-400 { background: #7c2d12; color: #fca5a5; }
        .status-404 { background: #92400e; color: #fcd34d; }
        .status-500 { background: #7c2d12; color: #fca5a5; }
        a { color: #60a5fa; text-decoration: none; }
        a:hover { color: #93c5fd; text-decoration: underline; }
        code { 
            background: #374151; 
            color: #fbbf24; 
            padding: 0.2rem 0.4rem; 
            border-radius: 3px; 
            font-family: 'Monaco', 'Consolas', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚣 RowCast API</h1>
            <p>Advanced Rowing Condition Forecasting API</p>
            <p><strong>Base URL:</strong> https://api.samwduncan.com</p>
        </div>

        <div class="toc section">
            <h2>📋 Table of Contents</h2>
            <ul>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#current-conditions">Current Conditions</a></li>
                <li><a href="#forecasts">Forecasts</a></li>
                <li><a href="#time-queries">Time-Based Queries</a></li>
                <li><a href="#scoring">Scoring System</a></li>
                <li><a href="#updates">Data Updates</a></li>
                <li><a href="#examples">Usage Examples</a></li>
            </ul>
        </div>

        <div class="section" id="overview">
            <h2>🌊 Overview</h2>
            <p>The RowCast API provides comprehensive rowing condition assessments by combining:</p>
            <div class="grid">
                <div class="card">
                    <h4>🌤️ Weather Data</h4>
                    <p>Temperature, wind, precipitation, UV, visibility, and severe weather alerts</p>
                </div>
                <div class="card">
                    <h4>🌊 Water Conditions</h4>
                    <p>Flow rate, water temperature, and gauge height with historical trends</p>
                </div>
                <div class="card">
                    <h4>⚡ Safety Factors</h4>
                    <p>Lightning risk, weather alerts, and dangerous conditions</p>
                </div>
            </div>
            
            <div class="info-box">
                <strong>🕒 Timezone:</strong> All timestamps are in EST/EDT (America/New_York)<br>
                <strong>📊 Score Range:</strong> 0-10 (10 = perfect conditions, 0 = dangerous/unsuitable)<br>
                <strong>🔄 Updates:</strong> Data refreshes automatically every 5-15 minutes
            </div>
        </div>

        <div class="section" id="current-conditions">
            <h2>📊 Current Conditions</h2>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast</span>
                <p>Get current rowing condition score with all parameters</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/weather</span>
                <p>Complete weather data (current + 24-hour forecast)</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/water</span>
                <p>Water conditions with historical data and predictions</p>
            </div>

            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/complete</span>
                <p>All data in one comprehensive response</p>
            </div>
        </div>

        <div class="section" id="forecasts">
            <h2>🔮 Forecasts</h2>
            
            <h3>📅 24-Hour Forecasts (Hourly)</h3>
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/forecast</span>
                <p>Detailed rowing scores with all conditions</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/forecast/simple</span>
                <p>Simple format: timestamps and scores only</p>
            </div>

            <h3>⚡ Short-Term Forecasts (15-minute intervals, 3 hours)</h3>
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/forecast/short-term</span>
                <p>Detailed 15-minute interval forecasts</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/forecast/short-term/simple</span>
                <p>Simple 15-minute forecasts: timestamps and scores only</p>
            </div>

            <h3>📅 Extended Forecasts (up to 7 days)</h3>
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/weather/extended</span>
                <p>Extended weather forecast data</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/forecast/extended</span>
                <p>Extended RowCast forecast scores using NOAA data</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/forecast/extended/simple</span>
                <p>Simple extended RowCast forecast - timestamps and scores only</p>
            </div>
        </div>

        <div class="section" id="time-queries">
            <h2>🕐 Time-Based Queries</h2>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/forecast/&lt;time_offset&gt;</span>
                <p>Get score for specific time offset from now</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="url">/api/rowcast/at/&lt;timestamp&gt;</span>
                <p>Get score for specific timestamp</p>
            </div>

            <h3>Time Offset Examples:</h3>
            <table>
                <tr><th>Format</th><th>Example</th><th>Description</th></tr>
                <tr><td><code>Xh</code></td><td><code>/api/rowcast/forecast/2h</code></td><td>2 hours from now</td></tr>
                <tr><td><code>Xm</code></td><td><code>/api/rowcast/forecast/30m</code></td><td>30 minutes from now</td></tr>
                <tr><td><code>Xd</code></td><td><code>/api/rowcast/forecast/1d</code></td><td>1 day from now</td></tr>
            </table>

            <h3>Timestamp Format:</h3>
            <div class="info-box">
                <strong>Format:</strong> <code>YYYY-MM-DDTHH:MM</code><br>
                <strong>Example:</strong> <code>/api/rowcast/at/2025-07-02T16:00</code>
            </div>
        </div>

        <div class="section" id="scoring">
            <h2>🏆 Scoring System</h2>
            
            <div class="grid">
                <div class="card">
                    <h4>🌡️ Temperature</h4>
                    <p><strong>Optimal:</strong> 74-85°F<br>
                    Exponential decay outside range</p>
                </div>
                <div class="card">
                    <h4>💨 Wind</h4>
                    <p><strong>Ideal:</strong> &lt;5mph speed, &lt;10mph gusts<br>
                    Poor conditions: &gt;25mph speed or &gt;35mph gusts</p>
                </div>
                <div class="card">
                    <h4>🌊 Water Flow</h4>
                    <p><strong>Good:</strong> ≤8,000 cfs<br>
                    <strong>Dangerous:</strong> &gt;13,000 cfs</p>
                </div>
                <div class="card">
                    <h4>🌡️ Water Temperature</h4>
                    <p><strong>Comfortable:</strong> ≥65°F<br>
                    <strong>Cold but safe:</strong> 50-65°F<br>
                    <strong>Safety concern:</strong> &lt;50°F</p>
                </div>
                <div class="card">
                    <h4>🌧️ Precipitation</h4>
                    <p><strong>Good:</strong> &lt;1 inch<br>
                    <strong>Poor:</strong> 5-10 inches<br>
                    <strong>Dangerous:</strong> ≥10 inches</p>
                </div>
                <div class="card">
                    <h4>☀️ UV Index</h4>
                    <p><strong>Low:</strong> 0-3 (score: 1.0)<br>
                    <strong>Moderate:</strong> 3-6 (score: 0.9)<br>
                    <strong>Extreme:</strong> 11+ (score: 0.1)</p>
                </div>
            </div>

            <div class="warning-box">
                <h4>⚠️ Safety Override Conditions</h4>
                <p>These conditions will result in very low or zero scores:</p>
                <ul>
                    <li><strong>Lightning risk &gt;80%:</strong> Score = 0</li>
                    <li><strong>Visibility &lt;0.25 miles:</strong> Score = 0</li>
                    <li><strong>Severe weather alerts:</strong> Score = 0</li>
                    <li><strong>Flash flood warnings:</strong> Score = 0</li>
                </ul>
            </div>
        </div>

        <div class="section" id="updates">
            <h2>🔄 Data Update Intervals</h2>
            <table>
                <tr><th>Data Type</th><th>Update Frequency</th><th>Description</th></tr>
                <tr><td>Weather Data</td><td>Every 10 minutes</td><td>Current conditions and forecasts</td></tr>
                <tr><td>Water Data</td><td>Every 15 minutes</td><td>USGS gauge readings</td></tr>
                <tr><td>Forecast Scores</td><td>Every 10 minutes</td><td>24-hour rowing scores</td></tr>
                <tr><td>Short-term Forecast</td><td>Every 5 minutes</td><td>15-minute interval scores</td></tr>
            </table>
        </div>

        <div class="section" id="examples">
            <h2>💻 Usage Examples</h2>
            
            <h3>Get Current Score</h3>
            <pre><code>curl https://api.samwduncan.com/api/rowcast</code></pre>
            
            <h3>Check Conditions in 2 Hours</h3>
            <pre><code>curl https://api.samwduncan.com/api/rowcast/forecast/2h</code></pre>
            
            <h3>Get Simple 24-Hour Forecast</h3>
            <pre><code>curl https://api.samwduncan.com/api/rowcast/forecast/simple</code></pre>
            
            <h3>Get 15-Minute Forecast for Next 3 Hours</h3>
            <pre><code>curl https://api.samwduncan.com/api/rowcast/forecast/short-term/simple</code></pre>

            <h3>Example Response (Simple Forecast)</h3>
            <pre class="json"><code>[
  {"timestamp": "2025-07-02T14:00", "score": 8.2},
  {"timestamp": "2025-07-02T15:00", "score": 7.9},
  {"timestamp": "2025-07-02T16:00", "score": 6.5}
]</code></pre>
        </div>

        <div class="section">
            <h2>📜 HTTP Status Codes</h2>
            <table>
                <tr><th>Code</th><th>Description</th><th>Example</th></tr>
                <tr><td><span class="status-code status-200">200 OK</span></td><td>Successful request</td><td>Data returned successfully</td></tr>
                <tr><td><span class="status-code status-404">404 Not Found</span></td><td>Data not available</td><td>Forecast not yet calculated</td></tr>
                <tr><td><span class="status-code status-400">400 Bad Request</span></td><td>Invalid parameters</td><td>Invalid time format</td></tr>
                <tr><td><span class="status-code status-500">500 Server Error</span></td><td>Server error</td><td>API service unavailable</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>🔗 Quick Links</h2>
            <div class="grid">
                <div class="card">
                    <h4>📊 Current Conditions</h4>
                    <p><a href="https://api.samwduncan.com/api/rowcast" target="_blank">Current Score</a></p>
                    <p><a href="https://api.samwduncan.com/api/complete" target="_blank">All Current Data</a></p>
                </div>
                <div class="card">
                    <h4>📈 Forecasts</h4>
                    <p><a href="https://api.samwduncan.com/api/rowcast/forecast/simple" target="_blank">24-Hour Simple</a></p>
                    <p><a href="https://api.samwduncan.com/api/rowcast/forecast/short-term/simple" target="_blank">15-Min Simple</a></p>
                </div>
                <div class="card">
                    <h4>📋 Raw Data</h4>
                    <p><a href="https://api.samwduncan.com/api" target="_blank">JSON Documentation</a></p>
                    <p><a href="https://api.samwduncan.com/docs" target="_blank">JSON API Info</a></p>
                </div>
            </div>
        </div>

        <div class="info-box">
            <p><strong>🚀 RowCast API</strong> - Advanced rowing condition forecasting<br>
            For support or questions, check the server logs or API status.</p>
        </div>
    </div>
</body>
</html>
    """
    
    from flask import Response
    return Response(html_content, mimetype='text/html')

@bp.route("/dashboard")
@bp.route("/data")
def data_dashboard():
    """Comprehensive data dashboard showing all API data in an easy-to-read format"""
    try:
        # Get all data sources
        weather_data = get_data_from_redis('weather_data')
        extended_weather_data = get_data_from_redis('extended_weather_data')
        water_data = get_data_from_redis('water_data')
        noaa_stageflow_data = get_data_from_redis('noaa_stageflow_data')
        forecast_scores = get_data_from_redis('forecast_scores')
        extended_forecast_scores = get_data_from_redis('extended_forecast_scores')
        short_term_forecast = get_data_from_redis('short_term_forecast')
        
        # Calculate current rowcast if we have current data
        current_rowcast = None
        if weather_data and weather_data.get('current'):
            current_water = water_data.get('current') if water_data else {}
            noaa_current = noaa_stageflow_data.get('current') if noaa_stageflow_data else {}
            
            current_params = {
                'windSpeed': weather_data['current'].get('windSpeed'),
                'windGust': weather_data['current'].get('windGust'),
                'apparentTemp': weather_data['current'].get('apparentTemp'),
                'uvIndex': weather_data['current'].get('uvIndex'),
                'precipitation': weather_data['current'].get('precipitation'),
                'discharge': noaa_current.get('discharge') or current_water.get('discharge'),
                'waterTemp': current_water.get('waterTemp'),
                'gaugeHeight': noaa_current.get('gaugeHeight') or current_water.get('gaugeHeight'),
                'weatherAlerts': weather_data['current'].get('weatherAlerts', []),
                'visibility': weather_data['current'].get('visibility'),
                'lightningPotential': 0,
                'precipitationProbability': 0
            }
            
            current_rowcast = {
                'score': compute_rowcast(current_params),
                'conditions': current_params,
                'timestamp': weather_data['current'].get('timestamp'),
                'noaaDataUsed': noaa_current.get('discharge') is not None or noaa_current.get('gaugeHeight') is not None
            }
        
        # Prepare extended forecast data for the widget
        extended_forecast_widget_data = []
        if extended_forecast_scores:
            for item in extended_forecast_scores[:168]:  # 7 days * 24 hours
                discharge = item.get('conditions', {}).get('discharge')
                # Round discharge to nearest whole number if available
                if discharge is not None:
                    discharge = round(discharge)
                
                extended_forecast_widget_data.append({
                    'timestamp': item.get('timestamp'),
                    'score': item.get('score'),
                    'discharge': discharge,
                    'apparentTemp': item.get('conditions', {}).get('apparentTemp'),
                    'windSpeed': item.get('conditions', {}).get('windSpeed'),
                    'windGust': item.get('conditions', {}).get('windGust'),
                    'noaaDataUsed': item.get('noaaDataUsed', False)
                })
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RowCast Data Dashboard</title>
    <style>
        body {{
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            line-height: 1.5;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 50%, #0f0f23 100%);
            color: #e4e4e7;
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px 0;
            background: rgba(15, 15, 35, 0.8);
            border-radius: 20px;
            border: 1px solid rgba(99, 102, 241, 0.3);
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            color: #a5b4fc;
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
            text-shadow: 0 0 20px rgba(165, 180, 252, 0.5);
        }}
        
        .last-updated {{
            color: #9ca3af;
            font-size: 0.9rem;
            margin-top: 10px;
            opacity: 0.8;
        }}
        
        .nav-links {{
            margin-top: 20px;
        }}
        
        .nav-links a {{
            color: #6366f1;
            text-decoration: none;
            margin: 0 15px;
            padding: 8px 16px;
            border: 1px solid rgba(99, 102, 241, 0.5);
            border-radius: 8px;
            transition: all 0.3s ease;
            background: rgba(99, 102, 241, 0.1);
        }}
        
        .nav-links a:hover {{
            background: rgba(99, 102, 241, 0.2);
            border-color: #6366f1;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: rgba(30, 30, 45, 0.9);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, #6366f1, #8b5cf6, #06b6d4);
            opacity: 0.7;
        }}
        
        .card:hover {{
            transform: translateY(-4px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 8px 32px rgba(99, 102, 241, 0.2);
        }}
        
        .card h2 {{
            color: #f1f5f9;
            margin: 0 0 20px 0;
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .score {{
            font-size: 3.5rem;
            font-weight: 800;
            text-align: center;
            margin: 20px 0;
            padding: 30px;
            border-radius: 16px;
            position: relative;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
            border: 1px solid rgba(99, 102, 241, 0.3);
        }}
        
        .score-excellent {{ 
            color: #10b981;
            text-shadow: 0 0 20px rgba(16, 185, 129, 0.5);
            border-color: rgba(16, 185, 129, 0.3);
        }}
        .score-good {{ 
            color: #f59e0b;
            text-shadow: 0 0 20px rgba(245, 158, 11, 0.5);
            border-color: rgba(245, 158, 11, 0.3);
        }}
        .score-poor {{ 
            color: #ef4444;
            text-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
            border-color: rgba(239, 68, 68, 0.3);
        }}
        .score-unknown {{ 
            color: #6b7280;
            text-shadow: 0 0 20px rgba(107, 114, 128, 0.5);
        }}
        
        .data-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 15px;
        }}
        
        .data-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: rgba(15, 15, 35, 0.6);
            border: 1px solid rgba(99, 102, 241, 0.1);
            border-radius: 8px;
            font-size: 0.9rem;
        }}
        
        .data-label {{
            font-weight: 500;
            color: #cbd5e1;
        }}
        
        .data-value {{
            color: #f1f5f9;
            font-weight: 600;
        }}
        
        .noaa-badge {{
            background: linear-gradient(135deg, #06b6d4, #0891b2);
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            text-align: center;
            margin-top: 10px;
        }}
        
        .alert {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
            padding: 16px;
            margin: 10px 0;
            color: #fbbf24;
        }}
        
        .alert-danger {{
            background: rgba(239, 68, 68, 0.1);
            border-color: rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }}
        
        .status-good {{ color: #10b981; }}
        .status-warning {{ color: #f59e0b; }}
        .status-error {{ color: #ef4444; }}
        
        .icon {{
            font-size: 1.4rem;
        }}
        
        .wide-card {{
            grid-column: 1 / -1;
        }}
        
        /* Extended Forecast Widget Styles */
        .forecast-widget {{
            background: rgba(30, 30, 45, 0.95);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 20px;
            padding: 24px;
            margin-top: 20px;
            position: relative;
            overflow: hidden;
        }}
        
        .forecast-widget::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #6366f1, #8b5cf6, #06b6d4, #10b981);
        }}
        
        .forecast-controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
        }}
        
        .forecast-nav {{
            display: flex;
            gap: 10px;
        }}
        
        .nav-btn {{
            background: rgba(99, 102, 241, 0.2);
            border: 1px solid rgba(99, 102, 241, 0.4);
            color: #a5b4fc;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }}
        
        .nav-btn:hover {{
            background: rgba(99, 102, 241, 0.3);
            border-color: #6366f1;
        }}
        
        .nav-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .forecast-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
        }}
        
        .forecast-item {{
            background: rgba(15, 15, 35, 0.7);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
        }}
        
        .forecast-item:hover {{
            border-color: rgba(99, 102, 241, 0.4);
            transform: translateY(-2px);
        }}
        
        .forecast-time {{
            color: #9ca3af;
            font-size: 0.8rem;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .forecast-score {{
            font-size: 1.8rem;
            font-weight: 700;
            margin: 8px 0;
        }}
        
        .forecast-details {{
            font-size: 0.75rem;
            color: #cbd5e1;
            margin-top: 8px;
        }}
        
        .forecast-details div {{
            margin: 2px 0;
        }}
        
        .noaa-indicator {{
            position: absolute;
            top: 4px;
            right: 4px;
            width: 8px;
            height: 8px;
            background: #06b6d4;
            border-radius: 50%;
            box-shadow: 0 0 6px rgba(6, 182, 212, 0.6);
        }}
        
        .page-indicator {{
            color: #9ca3af;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        /* Responsive adjustments */
        @media (max-width: 768px) {{
            .container {{ padding: 10px; }}
            .grid {{ grid-template-columns: 1fr; }}
            .forecast-grid {{ grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }}
            .nav-links {{ text-align: center; }}
            .nav-links a {{ display: inline-block; margin: 5px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚣 RowCast Data Dashboard</h1>
            <div class="last-updated">
                Last Updated: {datetime.now(EST).strftime('%Y-%m-%d %H:%M:%S %Z')}
            </div>
            <div class="nav-links">
                <a href="/api">API Docs</a>
                <a href="/documentation">Full Documentation</a>
                <a href="/api/complete/extended">JSON Data</a>
            </div>
        </div>

        <div class="grid">
            <!-- Current RowCast Score -->
            <div class="card">
                <h2><span class="icon">🎯</span> Current RowCast Score</h2>
                {f'''
                <div class="score {'score-excellent' if current_rowcast and current_rowcast['score'] >= 8 else 'score-good' if current_rowcast and current_rowcast['score'] >= 5 else 'score-poor' if current_rowcast else 'score-unknown'}">
                    {current_rowcast['score'] if current_rowcast else 'N/A'}
                </div>
                ''' if current_rowcast else '<div class="score score-unknown">N/A</div>'}
                {f'<div class="noaa-badge">Using NOAA Data</div>' if current_rowcast and current_rowcast.get('noaaDataUsed') else ''}
                {f'<p style="text-align: center; color: #9ca3af; margin-top: 10px; font-size: 0.85rem;">Updated: {current_rowcast["timestamp"]}</p>' if current_rowcast else ''}
            </div>

            <!-- Current Weather -->
            <div class="card">
                <h2><span class="icon">🌤️</span> Current Weather</h2>
                {f'''
                <div class="data-grid">
                    <div class="data-item">
                        <span class="data-label">Temperature:</span>
                        <span class="data-value">{weather_data['current'].get('apparentTemp', 'N/A')}°F</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Wind:</span>
                        <span class="data-value">{weather_data['current'].get('windSpeed', 'N/A')} mph</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Gusts:</span>
                        <span class="data-value">{weather_data['current'].get('windGust', 'N/A')} mph</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">UV Index:</span>
                        <span class="data-value">{weather_data['current'].get('uvIndex', 'N/A')}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Visibility:</span>
                        <span class="data-value">{weather_data['current'].get('visibility', 'N/A')} mi</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Precipitation:</span>
                        <span class="data-value">{weather_data['current'].get('precipitation', 'N/A')} mm</span>
                    </div>
                </div>
                ''' if weather_data and weather_data.get('current') else '<p class="status-error">Weather data not available</p>'}
            </div>

            <!-- Current Water Conditions -->
            <div class="card">
                <h2><span class="icon">🌊</span> Current Water Conditions</h2>
                {f'''
                <div class="data-grid">
                    <div class="data-item">
                        <span class="data-label">Discharge:</span>
                        <span class="data-value">{(noaa_stageflow_data.get('current', {}).get('discharge') or water_data.get('current', {}).get('discharge', 'N/A')) if (noaa_stageflow_data or water_data) else 'N/A'} cfs</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Gauge Height:</span>
                        <span class="data-value">{(noaa_stageflow_data.get('current', {}).get('gaugeHeight') or water_data.get('current', {}).get('gaugeHeight', 'N/A')) if (noaa_stageflow_data or water_data) else 'N/A'} ft</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Water Temp:</span>
                        <span class="data-value">{water_data.get('current', {}).get('waterTemp', 'N/A') if water_data else 'N/A'}°F</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Source:</span>
                        <span class="data-value">{'NOAA + Local' if noaa_stageflow_data and noaa_stageflow_data.get('current') else 'Local Only'}</span>
                    </div>
                </div>
                ''' if (water_data or noaa_stageflow_data) else '<p class="status-error">Water data not available</p>'}
            </div>

            <!-- Data Availability Status -->
            <div class="card">
                <h2><span class="icon">📊</span> Data Status</h2>
                <div class="data-grid">
                    <div class="data-item">
                        <span class="data-label">Weather:</span>
                        <span class="data-value status-{'good' if weather_data else 'error'}">{'✓ Available' if weather_data else '✗ Unavailable'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Extended Weather:</span>
                        <span class="data-value status-{'good' if extended_weather_data else 'error'}">{'✓ Available' if extended_weather_data else '✗ Unavailable'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Water Data:</span>
                        <span class="data-value status-{'good' if water_data else 'error'}">{'✓ Available' if water_data else '✗ Unavailable'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">NOAA Stageflow:</span>
                        <span class="data-value status-{'good' if noaa_stageflow_data else 'error'}">{'✓ Available' if noaa_stageflow_data else '✗ Unavailable'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Forecast Scores:</span>
                        <span class="data-value status-{'good' if forecast_scores else 'error'}">{'✓ Available' if forecast_scores else '✗ Unavailable'}</span>
                    </div>
                    <div class="data-item">
                        <span class="data-label">Extended Forecast:</span>
                        <span class="data-value status-{'good' if extended_forecast_scores else 'error'}">{'✓ Available' if extended_forecast_scores else '✗ Unavailable'}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Weather Alerts -->
        {f'''
        <div class="card wide-card">
            <h2><span class="icon">⚠️</span> Weather Alerts</h2>
            {f"""
            {"".join([f'<div class="alert alert-danger"><strong>{alert.get("type", "Alert")}</strong>: {alert.get("description", "No description available")}</div>' for alert in weather_data.get('alerts', [])]) if weather_data.get('alerts') else '<p style="color: #10b981;">No active weather alerts</p>'}
            """ if weather_data else '<p class="status-error">Weather alert data not available</p>'}
        </div>
        ''' if weather_data else ''}

        <!-- Extended Forecast Widget -->
        <div class="forecast-widget wide-card">
            <div class="forecast-controls">
                <div>
                    <h2><span class="icon">📅</span> Extended Forecast</h2>
                    <p style="color: #9ca3af; font-size: 0.85rem; margin: 5px 0 0 0;">
                        Blue dots indicate NOAA river data • Orange "Extrapolated" shows estimated values
                    </p>
                </div>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="page-indicator" id="pageIndicator">Page 1 of 7</span>
                    <div class="forecast-nav">
                        <button class="nav-btn" id="prevBtn" onclick="changePage(-1)">← Previous</button>
                        <button class="nav-btn" id="nextBtn" onclick="changePage(1)">Next →</button>
                    </div>
                </div>
            </div>
            <div class="forecast-grid" id="forecastGrid">
                <!-- Forecast items will be populated by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        // Extended forecast data
        const forecastData = {json.dumps(extended_forecast_widget_data)};
        const itemsPerPage = 24; // 24 hours per page
        let currentPage = 0;
        const totalPages = Math.ceil(forecastData.length / itemsPerPage);

        function formatTime(timestamp) {{
            const date = new Date(timestamp);
            return date.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }}) + ' ' + 
                   date.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit', hour12: false }});
        }}

        function getScoreClass(score) {{
            if (score >= 8) return 'score-excellent';
            if (score >= 5) return 'score-good';
            if (score > 0) return 'score-poor';
            return 'score-unknown';
        }}

        function renderForecast() {{
            const grid = document.getElementById('forecastGrid');
            const start = currentPage * itemsPerPage;
            const end = Math.min(start + itemsPerPage, forecastData.length);
            
            if (forecastData.length === 0) {{
                grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #9ca3af; padding: 40px;">No extended forecast data available</div>';
                return;
            }}
            
            grid.innerHTML = '';
            
            for (let i = start; i < end; i++) {{
                const item = forecastData[i];
                const scoreClass = getScoreClass(item.score);
                
                const forecastItem = document.createElement('div');
                forecastItem.className = 'forecast-item';
                forecastItem.innerHTML = `
                    ${{item.noaaDataUsed ? '<div class="noaa-indicator"></div>' : ''}}
                    <div class="forecast-time">${{formatTime(item.timestamp)}}</div>
                    <div class="forecast-score ${{scoreClass}}">${{item.score !== null && item.score !== undefined ? item.score : 'N/A'}}</div>
                    <div class="forecast-details">
                        <div>Flow: ${{item.discharge !== null ? item.discharge.toLocaleString() : 'N/A'}} cfs</div>
                        <div>Temp: ${{item.apparentTemp !== null ? Math.round(item.apparentTemp) : 'N/A'}}°F</div>
                        <div>Wind: ${{item.windSpeed !== null ? Math.round(item.windSpeed) : 'N/A'}} mph</div>
                        ${{!item.noaaDataUsed ? '<div style="font-size: 0.7rem; color: #f59e0b;">Extrapolated</div>' : ''}}
                    </div>
                `;
                grid.appendChild(forecastItem);
            }}
            
            // Update page indicator
            document.getElementById('pageIndicator').textContent = `Page ${{currentPage + 1}} of ${{totalPages}}`;
            
            // Update button states
            document.getElementById('prevBtn').disabled = currentPage === 0;
            document.getElementById('nextBtn').disabled = currentPage === totalPages - 1;
        }}

        function changePage(direction) {{
            const newPage = currentPage + direction;
            if (newPage >= 0 && newPage < totalPages) {{
                currentPage = newPage;
                renderForecast();
            }}
        }}

        // Initialize forecast widget
        renderForecast();
    </script>
</body>
</html>
        """
        
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate dashboard: {str(e)}"}), 500