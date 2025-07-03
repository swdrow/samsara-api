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
        "wind_direction_10m,wind_gusts_10m,precipitation,uv_index,visibility"
        "&hourly=temperature_2m,apparent_temperature,wind_speed_10m,"
        "wind_direction_10m,wind_gusts_10m,precipitation,uv_index,visibility,precipitation_probability,lightning_potential"
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
    
    # Fetch weather alerts from NWS API
    alerts = fetch_weather_alerts(lat, lon)
    
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
            'visibility': current.get('visibility'),
            'timestamp': current.get('time'),
            'weatherAlerts': alerts  # Add active alerts
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
                'currentTemp': hourly.get('temperature_2m', [])[i] if i < len(hourly.get('temperature_2m', [])) else None,
                'visibility': hourly.get('visibility', [])[i] if i < len(hourly.get('visibility', [])) else None,
                'precipitationProbability': hourly.get('precipitation_probability', [])[i] if i < len(hourly.get('precipitation_probability', [])) else None,
                'lightningPotential': hourly.get('lightning_potential', [])[i] if i < len(hourly.get('lightning_potential', [])) else None,
                'weatherAlerts': alerts  # Include alerts for each forecast hour
            }
            forecast.append(forecast_hour)
        
        logger.info(f"Successfully fetched weather data with {len(forecast)} forecast hours and {len(alerts)} active alerts")
        return {
            'current': current_weather,
            'forecast': forecast,
            'alerts': alerts
        }
    except Exception as e:
        logger.error(f"Failed to process weather data: {e}")
        raise Exception(f"Weather data processing failed: {e}")

def fetch_weather_alerts(lat, lon):
    """Fetch active weather alerts from NWS API for the given coordinates."""
    try:
        # Get the NWS grid point for the coordinates
        grid_url = f"https://api.weather.gov/points/{lat},{lon}"
        grid_response = requests.get(grid_url, timeout=10)
        grid_response.raise_for_status()
        grid_data = grid_response.json()
        
        # Get the zone and county for alerts
        zone = grid_data.get('properties', {}).get('forecastZone', '').split('/')[-1]
        county = grid_data.get('properties', {}).get('county', '').split('/')[-1]
        
        alerts = []
        
        # Fetch zone-based alerts
        if zone:
            zone_alerts_url = f"https://api.weather.gov/alerts/active/zone/{zone}"
            try:
                zone_response = requests.get(zone_alerts_url, timeout=10)
                zone_response.raise_for_status()
                zone_data = zone_response.json()
                
                for feature in zone_data.get('features', []):
                    props = feature.get('properties', {})
                    alert = {
                        'type': props.get('event'),
                        'severity': props.get('severity'),
                        'urgency': props.get('urgency'),
                        'certainty': props.get('certainty'),
                        'headline': props.get('headline'),
                        'description': props.get('description'),
                        'instruction': props.get('instruction'),
                        'onset': props.get('onset'),
                        'expires': props.get('expires')
                    }
                    alerts.append(alert)
            except Exception as e:
                logger.warning(f"Failed to fetch zone alerts: {e}")
        
        return alerts
        
    except Exception as e:
        logger.warning(f"Failed to fetch weather alerts: {e}")
        return []

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

def fetch_short_term_forecast():
    """Fetches 15-minute interval weather data for the next 3 hours."""
    logger.info("FETCHER: Calling Open-Meteo API for 15-minute forecast...")
    lat, lon = 39.8682, -75.5916
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&minutely_15=temperature_2m,apparent_temperature,wind_speed_10m,"
        "wind_direction_10m,wind_gusts_10m,precipitation,precipitation_probability,visibility"
        "&windspeed_unit=mph&temperature_unit=fahrenheit"
        "&timezone=America/New_York&forecast_hours=3"
    )
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch 15-minute forecast data: {e}")
        raise Exception(f"15-minute forecast API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse 15-minute forecast JSON: {e}")
        raise Exception(f"15-minute forecast API returned invalid JSON: {e}")
    
    try:
        # Get current water data for the short-term projections
        from app.extensions import redis_client
        water_data_str = redis_client.get('water_data')
        water_data = json.loads(water_data_str) if water_data_str else {}
        current_water = water_data.get('current', {})
        
        # 15-minute forecast data
        minutely = data.get("minutely_15", {})
        times = minutely.get('time', [])
        forecast = []
        
        # Process next 3 hours (12 x 15-minute intervals)
        for i in range(min(12, len(times))):
            deg_forecast = minutely.get('wind_direction_10m', [])[i] if i < len(minutely.get('wind_direction_10m', [])) else None
            wind_dir_forecast = f"{deg_to_cardinal(deg_forecast)} ({fmt(deg_forecast, 0, '°')})" if deg_forecast is not None else "N/A"
            
            forecast_interval = {
                'timestamp': times[i],
                'windSpeed': minutely.get('wind_speed_10m', [])[i] if i < len(minutely.get('wind_speed_10m', [])) else None,
                'windGust': minutely.get('wind_gusts_10m', [])[i] if i < len(minutely.get('wind_gusts_10m', [])) else None,
                'windDir': wind_dir_forecast,
                'apparentTemp': minutely.get('apparent_temperature', [])[i] if i < len(minutely.get('apparent_temperature', [])) else None,
                'precipitation': minutely.get('precipitation', [])[i] if i < len(minutely.get('precipitation', [])) else None,
                'currentTemp': minutely.get('temperature_2m', [])[i] if i < len(minutely.get('temperature_2m', [])) else None,
                'visibility': minutely.get('visibility', [])[i] if i < len(minutely.get('visibility', [])) else None,
                'precipitationProbability': minutely.get('precipitation_probability', [])[i] if i < len(minutely.get('precipitation_probability', [])) else None,
                # Use current water values for short-term forecast
                'discharge': current_water.get('discharge'),
                'waterTemp': current_water.get('waterTemp'),
                'gaugeHeight': current_water.get('gaugeHeight'),
                'uvIndex': 0,  # UV not available in 15-min data, default to 0 for short term
                'lightningPotential': 0,  # Lightning not available in 15-min data
                'weatherAlerts': []  # Use current alerts
            }
            forecast.append(forecast_interval)
        
        logger.info(f"Successfully fetched 15-minute forecast data with {len(forecast)} intervals")
        return {
            'forecast': forecast,
            'interval': '15min',
            'duration': '3hours'
        }
    except Exception as e:
        logger.error(f"Failed to process 15-minute forecast data: {e}")
        raise Exception(f"15-minute forecast data processing failed: {e}")

def fetch_noaa_stageflow_forecast():
    """Fetches stage and flow forecast data from NOAA NWPS API with interpolation for hourly intervals."""
    logger.info("FETCHER: Calling NOAA NWPS API for stageflow forecast...")
    
    try:
        url = "https://api.water.noaa.gov/nwps/v1/gauges/padp1/stageflow"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch NOAA stageflow data: {e}")
        raise Exception(f"NOAA NWPS API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse NOAA stageflow JSON: {e}")
        raise Exception(f"NOAA NWPS API returned invalid JSON: {e}")
    
    try:
        # Extract observed and forecast data
        observed_data = data.get('observed', {}).get('data', [])
        forecast_data = data.get('forecast', {}).get('data', [])
        
        # Process current/latest observed data
        current_observed = None
        if observed_data:
            latest = observed_data[-1]  # Most recent observation
            current_observed = {
                'timestamp': latest.get('validTime'),
                'gaugeHeight': latest.get('primary'),  # Stage in feet
                'discharge': latest.get('secondary') * 1000 if latest.get('secondary') else None,  # Convert kcfs to cfs
                'generatedTime': latest.get('generatedTime')
            }
        
        # Process forecast data and interpolate to hourly intervals
        hourly_forecast = []
        
        if forecast_data and len(forecast_data) >= 2:
            # Sort forecast data by timestamp
            sorted_forecast = sorted(forecast_data, key=lambda x: x.get('validTime', ''))
            
            # Get the time range for interpolation
            start_time = datetime.fromisoformat(sorted_forecast[0]['validTime'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(sorted_forecast[-1]['validTime'].replace('Z', '+00:00'))
            
            # Generate hourly timestamps from start to end
            current_hour = start_time.replace(minute=0, second=0, microsecond=0)
            
            while current_hour <= end_time:
                # Find the two forecast points that bracket this hour
                interpolated_values = interpolate_forecast_values(sorted_forecast, current_hour)
                
                if interpolated_values:
                    hourly_forecast.append({
                        'timestamp': current_hour.isoformat().replace('+00:00', 'Z'),
                        'gaugeHeight': interpolated_values['stage'],
                        'discharge': interpolated_values['flow'] * 1000 if interpolated_values['flow'] else None,  # Convert kcfs to cfs
                        'source': 'noaa_nwps_interpolated'
                    })
                
                current_hour += timedelta(hours=1)
        
        logger.info(f"Successfully processed NOAA stageflow data: {len(observed_data)} observed points, {len(forecast_data)} forecast points, {len(hourly_forecast)} interpolated hours")
        
        return {
            'current': current_observed,
            'observed': observed_data[-24:] if len(observed_data) >= 24 else observed_data,  # Last 24 observations
            'forecast': hourly_forecast,
            'raw_forecast': forecast_data,
            'metadata': {
                'issuedTime': data.get('forecast', {}).get('issuedTime'),
                'wfo': data.get('forecast', {}).get('wfo'),
                'timeZone': data.get('forecast', {}).get('timeZone'),
                'primaryName': data.get('forecast', {}).get('primaryName'),
                'primaryUnits': data.get('forecast', {}).get('primaryUnits'),
                'secondaryName': data.get('forecast', {}).get('secondaryName'),
                'secondaryUnits': data.get('forecast', {}).get('secondaryUnits')
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to process NOAA stageflow data: {e}")
        raise Exception(f"NOAA stageflow data processing failed: {e}")

def interpolate_forecast_values(forecast_data, target_time):
    """Interpolate stage and flow values for a specific time between forecast points."""
    try:
        # Find the two points that bracket the target time
        before_point = None
        after_point = None
        
        target_timestamp = target_time.timestamp()
        
        for i, point in enumerate(forecast_data):
            point_time = datetime.fromisoformat(point['validTime'].replace('Z', '+00:00')).timestamp()
            
            if point_time <= target_timestamp:
                before_point = point
            elif point_time > target_timestamp and after_point is None:
                after_point = point
                break
        
        # If we can't find suitable points, return None
        if not before_point or not after_point:
            # If target is before all points, use first point
            if not before_point and after_point:
                return {
                    'stage': after_point.get('primary'),
                    'flow': after_point.get('secondary')
                }
            # If target is after all points, use last point
            elif before_point and not after_point:
                return {
                    'stage': before_point.get('primary'),
                    'flow': before_point.get('secondary')
                }
            return None
        
        # Linear interpolation
        before_timestamp = datetime.fromisoformat(before_point['validTime'].replace('Z', '+00:00')).timestamp()
        after_timestamp = datetime.fromisoformat(after_point['validTime'].replace('Z', '+00:00')).timestamp()
        
        # Avoid division by zero
        time_diff = after_timestamp - before_timestamp
        if time_diff == 0:
            return {
                'stage': before_point.get('primary'),
                'flow': before_point.get('secondary')
            }
        
        # Calculate interpolation factor
        factor = (target_timestamp - before_timestamp) / time_diff
        
        # Interpolate stage (primary)
        before_stage = before_point.get('primary')
        after_stage = after_point.get('primary')
        interpolated_stage = None
        if before_stage is not None and after_stage is not None:
            interpolated_stage = before_stage + factor * (after_stage - before_stage)
        
        # Interpolate flow (secondary)
        before_flow = before_point.get('secondary')
        after_flow = after_point.get('secondary')
        interpolated_flow = None
        if before_flow is not None and after_flow is not None:
            interpolated_flow = before_flow + factor * (after_flow - before_flow)
        
        return {
            'stage': interpolated_stage,
            'flow': interpolated_flow
        }
        
    except Exception as e:
        logger.warning(f"Failed to interpolate forecast values: {e}")
        return None

def fetch_extended_weather_forecast():
    """Fetches extended weather forecast to match NOAA stageflow forecast duration."""
    logger.info("FETCHER: Calling Open-Meteo API for extended forecast...")
    lat, lon = 39.8682, -75.5916
    
    # Determine how many days we need based on NOAA forecast
    # NOAA typically provides ~5-7 days, so we'll request 7 days to be safe
    forecast_days = 7
    
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,wind_speed_10m,"  
        "wind_direction_10m,wind_gusts_10m,precipitation,uv_index,visibility"
        "&hourly=temperature_2m,apparent_temperature,wind_speed_10m,"
        "wind_direction_10m,wind_gusts_10m,precipitation,uv_index,visibility,precipitation_probability,lightning_potential"
        "&windspeed_unit=mph&temperature_unit=fahrenheit"
        f"&timezone=America/New_York&forecast_days={forecast_days}"
    )
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch extended weather data: {e}")
        raise Exception(f"Extended weather API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extended weather data JSON: {e}")
        raise Exception(f"Extended weather API returned invalid JSON: {e}")
    
    # Fetch weather alerts from NWS API
    alerts = fetch_weather_alerts(lat, lon)
    
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
            'visibility': current.get('visibility'),
            'timestamp': current.get('time'),
            'weatherAlerts': alerts
        }
        
        # Extended hourly forecast data
        hourly = data.get("hourly", {})
        times = hourly.get('time', [])
        forecast = []
        
        # Process all available forecast hours
        for i in range(len(times)):
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
                'currentTemp': hourly.get('temperature_2m', [])[i] if i < len(hourly.get('temperature_2m', [])) else None,
                'visibility': hourly.get('visibility', [])[i] if i < len(hourly.get('visibility', [])) else None,
                'precipitationProbability': hourly.get('precipitation_probability', [])[i] if i < len(hourly.get('precipitation_probability', [])) else None,
                'lightningPotential': hourly.get('lightning_potential', [])[i] if i < len(hourly.get('lightning_potential', [])) else None,
                'weatherAlerts': alerts
            }
            forecast.append(forecast_hour)
        
        logger.info(f"Successfully fetched extended weather data with {len(forecast)} forecast hours and {len(alerts)} active alerts")
        return {
            'current': current_weather,
            'forecast': forecast,
            'alerts': alerts,
            'forecastDays': forecast_days
        }
    except Exception as e:
        logger.error(f"Failed to process extended weather data: {e}")
        raise Exception(f"Extended weather data processing failed: {e}")