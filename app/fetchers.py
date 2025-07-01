# app/fetchers.py

import requests
import json
import os
from datetime import datetime, timedelta
import logging
from app.utils import fmt, deg_to_cardinal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The file cache logic has been removed and is now handled by Redis.

def fetch_weather_data():
    """Fetches current and forecast weather data from the Open-Meteo API."""
    logger.info("FETCHER: Calling Open-Meteo API...")
    lat, lon = 39.8682, -75.5916
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,wind_speed_10m,"  
        "wind_direction_10m,wind_gusts_10m,precipitation,uv_index"
        "&hourly=temperature_2m,apparent_temperature,wind_speed_10m,"
        "wind_direction_10m,wind_gusts_10m,precipitation,uv_index"
        "&windspeed_unit=mph&temperature_unit=fahrenheit"
        "&timezone=America/New_York&forecast_days=2"
    )
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch weather data: {e}")
        raise Exception(f"Weather API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse weather data JSON: {e}")
        raise Exception(f"Weather API returned invalid JSON: {e}")
    
    try:
        # Current weather data
        current = data.get("current", {})
        deg = current.get('wind_direction_10m')
        wind_dir = f"{deg_to_cardinal(deg)} ({fmt(deg, 0, '°')})" if deg is not None else "N/A"
        current_weather = {
            'windSpeed': current.get('wind_speed_10m'),
            'windGust': current.get('wind_gusts_10m'),
            'windDir': wind_dir,
            'apparentTemp': current.get('apparent_temperature'),
            'uvIndex': current.get('uv_index'),
            'precipitation': current.get('precipitation'),
            'currentTemp': current.get('temperature_2m'),
            'timestamp': current.get('time')
        }
        
        # Hourly forecast data (next 24 hours)
        hourly = data.get("hourly", {})
        times = hourly.get('time', [])
        forecast = []
        
        # Get next 24 hours of data
        for i in range(min(24, len(times))):
            deg_forecast = hourly.get('wind_direction_10m', [])[i] if i < len(hourly.get('wind_direction_10m', [])) else None
            wind_dir_forecast = f"{deg_to_cardinal(deg_forecast)} ({fmt(deg_forecast, 0, '°')})" if deg_forecast is not None else "N/A"
            
            forecast_hour = {
                'timestamp': times[i],
                'windSpeed': hourly.get('wind_speed_10m', [])[i] if i < len(hourly.get('wind_speed_10m', [])) else None,
                'windGust': hourly.get('wind_gusts_10m', [])[i] if i < len(hourly.get('wind_gusts_10m', [])) else None,
                'windDir': wind_dir_forecast,
                'apparentTemp': hourly.get('apparent_temperature', [])[i] if i < len(hourly.get('apparent_temperature', [])) else None,
                'uvIndex': hourly.get('uv_index', [])[i] if i < len(hourly.get('uv_index', [])) else None,
                'precipitation': hourly.get('precipitation', [])[i] if i < len(hourly.get('precipitation', [])) else None,
                'currentTemp': hourly.get('temperature_2m', [])[i] if i < len(hourly.get('temperature_2m', [])) else None
            }
            forecast.append(forecast_hour)
        
        logger.info(f"Successfully fetched weather data with {len(forecast)} forecast hours")
        return {
            'current': current_weather,
            'forecast': forecast
        }
    except Exception as e:
        logger.error(f"Failed to process weather data: {e}")
        raise Exception(f"Weather data processing failed: {e}")

def fetch_water_data_with_history():
    """Fetches current and historical water data from the USGS API for trend analysis."""
    logger.info("FETCHER: Calling USGS Water Services API with historical data...")
    site_id = "01474500"
    params = "00010,00065,00060"
    
    try:
        # Get current data
        current_url = f"https://waterservices.usgs.gov/nwis/iv/?sites={site_id}&parameterCd={params}&format=json"
        current_response = requests.get(current_url, timeout=30)
        current_response.raise_for_status()
        current_data = current_response.json()
        
        # Get historical data (last 7 days for trend analysis)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        historical_url = f"https://waterservices.usgs.gov/nwis/iv/?sites={site_id}&parameterCd={params}&startDT={start_str}&endDT={end_str}&format=json"
        
        historical_data = None
        try:
            historical_response = requests.get(historical_url, timeout=30)
            historical_response.raise_for_status()
            historical_data = historical_response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch historical water data: {e}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch current water data: {e}")
        raise Exception(f"Water API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse water data JSON: {e}")
        raise Exception(f"Water API returned invalid JSON: {e}")
    
    try:
        # Process current data
        current_out = {'gaugeHeight': None, 'waterTemp': None, 'discharge': None}
        for series in current_data.get('value', {}).get('timeSeries', []):
            name = series['variable']['variableName'].lower()
            try:
                val = series['values'][0]['value'][0]['value']
                if 'gage height' in name:
                    current_out['gaugeHeight'] = float(val)
                elif 'temperature' in name:
                    current_out['waterTemp'] = float(val) * 1.8 + 32
                elif 'discharge' in name or 'flow' in name:
                    current_out['discharge'] = int(float(val))
            except (IndexError, KeyError, ValueError):
                logger.warning(f"Could not parse data for {name}")
                continue
        
        # Process historical data for trend analysis
        historical_out = {'gaugeHeight': [], 'waterTemp': [], 'discharge': []}
        if historical_data:
            for series in historical_data.get('value', {}).get('timeSeries', []):
                name = series['variable']['variableName'].lower()
                try:
                    values = series['values'][0]['value']
                    if 'gage height' in name:
                        for val_entry in values[-24:]:  # Last 24 hours
                            historical_out['gaugeHeight'].append({
                                'timestamp': val_entry['dateTime'],
                                'value': float(val_entry['value'])
                            })
                    elif 'temperature' in name:
                        for val_entry in values[-24:]:  # Last 24 hours
                            historical_out['waterTemp'].append({
                                'timestamp': val_entry['dateTime'],
                                'value': float(val_entry['value']) * 1.8 + 32
                            })
                    elif 'discharge' in name or 'flow' in name:
                        for val_entry in values[-24:]:  # Last 24 hours
                            historical_out['discharge'].append({
                                'timestamp': val_entry['dateTime'],
                                'value': int(float(val_entry['value']))
                            })
                except (IndexError, KeyError, ValueError):
                    logger.warning(f"Could not parse historical data for {name}")
                    continue
        
        logger.info("Successfully fetched water data with historical trends")
        return {
            'current': current_out,
            'historical': historical_out
        }
    except Exception as e:
        logger.error(f"Failed to process water data: {e}")
        raise Exception(f"Water data processing failed: {e}")

def predict_water_data(historical_data):
    """Simple trend-based prediction for water data."""
    try:
        predictions = []
        
        # Generate predictions for next 24 hours
        for hour in range(1, 25):
            future_time = datetime.now() + timedelta(hours=hour)
            
            # Simple trend analysis - use recent values to predict
            discharge_values = [entry['value'] for entry in historical_data.get('discharge', [])]
            gauge_values = [entry['value'] for entry in historical_data.get('gaugeHeight', [])]
            temp_values = [entry['value'] for entry in historical_data.get('waterTemp', [])]
            
            # Use average of recent values as prediction (could be improved with ML)
            predicted_discharge = None
            predicted_gauge = None
            predicted_temp = None
            
            if discharge_values:
                recent_discharge = discharge_values[-min(6, len(discharge_values)):]
                predicted_discharge = sum(recent_discharge) / len(recent_discharge)
                
            if gauge_values:
                recent_gauge = gauge_values[-min(6, len(gauge_values)):]
                predicted_gauge = sum(recent_gauge) / len(recent_gauge)
                
            if temp_values:
                recent_temp = temp_values[-min(6, len(temp_values)):]
                predicted_temp = sum(recent_temp) / len(recent_temp)
            
            predictions.append({
                'timestamp': future_time.isoformat(),
                'discharge': predicted_discharge,
                'gaugeHeight': predicted_gauge,
                'waterTemp': predicted_temp
            })
        
        logger.info(f"Generated {len(predictions)} water predictions")
        return predictions
        
    except Exception as e:
        logger.error(f"Failed to generate water predictions: {e}")
        # Return empty predictions rather than failing
        return [{'timestamp': (datetime.now() + timedelta(hours=h)).isoformat(), 
                'discharge': None, 'gaugeHeight': None, 'waterTemp': None} 
                for h in range(1, 25)]

def fetch_water_data():
    """Fetches the latest water data from the USGS API (legacy function for compatibility)."""
    logger.info("FETCHER: Calling USGS Water Services API...")
    site_id = "01474500"
    params = "00010,00065,00060"
    
    try:
        url = f"https://waterservices.usgs.gov/nwis/iv/?sites={site_id}&parameterCd={params}&format=json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch water data: {e}")
        raise Exception(f"Water API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse water data JSON: {e}")
        raise Exception(f"Water API returned invalid JSON: {e}")
    
    try:
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
            except (IndexError, KeyError, ValueError):
                logger.warning(f"Could not parse data for {name}")
                continue
        
        logger.info("Successfully fetched legacy water data")
        return out
    except Exception as e:
        logger.error(f"Failed to process water data: {e}")
        raise Exception(f"Water data processing failed: {e}")