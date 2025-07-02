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
                "/api/rowcast/forecast": "Detailed rowcast forecast (24 hours, hourly)",
                "/api/rowcast/forecast/simple": "Simple rowcast forecast - timestamps and scores only",
                "/api/rowcast/forecast/short-term": "Detailed 15-minute forecast (3 hours)",
                "/api/rowcast/forecast/short-term/simple": "Simple 15-minute forecast - timestamps and scores only"
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
                "/api/complete": "All current data, forecasts, and scores in one response"
            }
        },
        "scoring_factors": {
            "weather": ["Temperature (74-85°F optimal)", "Wind speed/gusts", "Precipitation", "UV index", "Visibility"],
            "water": ["Discharge/flow rate", "Water temperature", "Gauge height"],
            "safety": ["Weather alerts", "Lightning potential", "Severe weather conditions"]
        },
        "score_range": "0-10 (10 = perfect conditions, 0 = dangerous/unsuitable)",
        "data_updates": {
            "weather": "Every 15 minutes",
            "water": "Every 30 minutes", 
            "forecasts": "Every hour"
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