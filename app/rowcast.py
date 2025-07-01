from math import exp
from app.utils import clamp, fmt


def temp_score(temp):
    t = [74, 80, 85, 90, 95, 100, 105]
    k = [0.02, 0.03, 0.09, 0.13, 0.28, 0.40]
    if temp is None or temp < 20 or temp >= 105:
        return 0
    s = 1
    for i in range(len(t) - 1):
        if temp <= t[i + 1]:
            return s * exp(-k[i] * (temp - t[i]))
        s *= exp(-k[i] * (t[i + 1] - t[i]))
    return s


def exp_fall(val, lo, hi):
    if val is None:
        return 1
    if val <= lo:
        return 1
    if val >= hi:
        return 0
    return exp(-2.5 * (val - lo) / (hi - lo))


def safety_alert_score(weather_alerts, visibility, lightning_potential, precip_prob):
    """Calculate safety score based on dangerous weather conditions."""
    # Start with perfect safety score
    safety_score = 1.0
    
    # Check for dangerous weather alerts
    if weather_alerts:
        for alert in weather_alerts:
            alert_type = alert.get('type', '').lower()
            severity = alert.get('severity', '').lower()
            urgency = alert.get('urgency', '').lower()
            
            # Immediate danger conditions that should zero out the score
            immediate_danger = [
                'tornado', 'severe thunderstorm', 'flash flood', 
                'flood warning', 'hurricane', 'tropical storm', 
                'gale warning', 'storm warning'
            ]
            
            # High danger conditions
            high_danger = [
                'high wind', 'small craft advisory', 'wind advisory',
                'flood watch', 'thunderstorm watch'
            ]
            
            if any(danger in alert_type for danger in immediate_danger):
                if severity in ['extreme', 'severe'] or urgency == 'immediate':
                    return 0  # Zero score for immediate danger
                elif severity == 'moderate':
                    safety_score *= 0.05  # Almost zero for moderate immediate danger
                else:
                    safety_score *= 0.1  # Very low for minor immediate danger
                    
            elif any(danger in alert_type for danger in high_danger):
                if severity in ['extreme', 'severe']:
                    safety_score *= 0.1  # Very low score for severe high danger
                elif severity == 'moderate':
                    safety_score *= 0.3  # Low score for moderate high danger
                else:
                    safety_score *= 0.6  # Reduced score for minor high danger
    
    # Visibility score - critical for safety on water
    if visibility is not None:
        if visibility < 0.25:  # Less than 1/4 mile - extremely dangerous
            return 0  # Zero score for extremely poor visibility
        elif visibility < 0.5:  # Less than 1/2 mile - very dangerous
            safety_score *= 0.05
        elif visibility < 1.0:  # Less than 1 mile - dangerous
            safety_score *= 0.2
        elif visibility < 2.0:  # Less than 2 miles - reduced visibility
            safety_score *= 0.5
        elif visibility < 5.0:  # Less than 5 miles - slightly reduced
            safety_score *= 0.8
    
    # Lightning potential score - extremely dangerous on water
    if lightning_potential is not None:
        if lightning_potential > 80:  # Very high lightning risk
            return 0  # Zero score - lightning is deadly on water
        elif lightning_potential > 60:  # High lightning risk
            safety_score *= 0.02  # Almost zero score
        elif lightning_potential > 40:  # Moderate lightning risk
            safety_score *= 0.1
        elif lightning_potential > 20:  # Low lightning risk
            safety_score *= 0.4
        elif lightning_potential > 10:  # Very low lightning risk
            safety_score *= 0.7
    
    # Precipitation probability - affects conditions and safety
    if precip_prob is not None:
        if precip_prob > 90:  # Very high chance of precipitation
            safety_score *= 0.3
        elif precip_prob > 70:  # High chance of precipitation
            safety_score *= 0.5
        elif precip_prob > 50:  # Moderate chance of precipitation
            safety_score *= 0.7
    
    return safety_score

def compute_rowcast(params):
    # Safely extract parameters, defaulting appropriately
    temp = params.get('apparentTemp')
    wind_speed = params.get('windSpeed', 0)
    wind_gust = params.get('windGust', 0)
    flow = params.get('discharge', 0)
    water_temp = params.get('waterTemp')
    prec = params.get('precipitation', 0)
    uv = params.get('uvIndex', 0)
    
    # Safety parameters
    weather_alerts = params.get('weatherAlerts', [])
    visibility = params.get('visibility')
    lightning_potential = params.get('lightningPotential')
    precip_prob = params.get('precipitationProbability')

    # Temperature score - optimal range 74-85°F
    tempSc = temp_score(temp)

    # Wind score - ideal: low wind speed and gusts
    # Using minimum ensures both speed and gusts are reasonable
    windSc = min(
        exp_fall(wind_speed, 5, 25),  # Ideal: <5mph, poor: >25mph
        exp_fall(wind_gust, 10, 35)   # Ideal: <10mph, poor: >35mph
    )

    # Flow (discharge) score - optimal flow for rowing
    if flow <= 8000:  # Good flow conditions
        flowSc = 1
    elif flow < 13000:  # Moderate flow - exponential decay
        flowSc = exp(-2 * (flow - 8000) / 5000)
    else:  # High flow - dangerous
        flowSc = 0

    # Water temperature score - warmer is generally better for safety
    if water_temp is None:
        waterTempSc = 0.5  # Unknown water temp - moderate penalty
    elif water_temp >= 65:  # Comfortable water temperature
        waterTempSc = 1
    elif water_temp >= 50:  # Cold but manageable
        waterTempSc = 0.7
    else:  # Very cold water - safety concern
        waterTempSc = exp(-2 * (50 - water_temp) / 15)

    # Precipitation score - any significant precipitation is problematic
    if prec >= 10:  # Heavy precipitation
        precipSc = 0
    elif prec >= 5:  # Moderate precipitation
        precipSc = 0.2
    elif prec >= 1:  # Light precipitation
        precipSc = 0.5
    else:  # Light to no precipitation
        precipSc = exp(-1.5 * prec)

    # UV index score - high UV affects comfort and safety
    if uv < 3:  # Low UV
        uvSc = 1
    elif uv < 6:  # Moderate UV
        uvSc = 0.9
    elif uv < 8:  # High UV
        uvSc = 0.7
    elif uv < 11:  # Very high UV
        uvSc = 0.4
    else:  # Extreme UV
        uvSc = 0.1
    
    # Safety score - can override all other factors
    safetySc = safety_alert_score(weather_alerts, visibility, lightning_potential, precip_prob)

    # Compute combined score - safety score can zero out the entire score
    raw_score = 10 * tempSc * windSc * flowSc * precipSc * uvSc * waterTempSc * safetySc
    score = clamp(round(raw_score, 2), 0, 10)
    return score


def merge_params(weather, water):
    return { **weather, **water }