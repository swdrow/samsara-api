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

    # Temperature score - optimal range 65-85°F (more realistic for rowing comfort)
    if temp is None:
        tempSc = 0.3  # Unknown temp penalty
    elif 65 <= temp <= 85:  # Ideal rowing temperature range
        tempSc = 1.0
    elif 55 <= temp < 65:  # Cool but acceptable
        tempSc = 0.8 - (65 - temp) * 0.05  # Gradual decline
    elif 85 < temp <= 95:  # Warm but manageable
        tempSc = 0.9 - (temp - 85) * 0.08  # Gradual decline for heat
    elif temp < 55:  # Too cold for comfortable rowing
        tempSc = max(0.1, 0.8 - (55 - temp) * 0.1)
    else:  # temp > 95 - too hot
        tempSc = max(0.05, 0.1 - (temp - 95) * 0.02)

    # Wind score - more nuanced for rowing conditions
    # Rowing is heavily affected by wind, especially gusts
    max_wind = max(wind_speed, wind_gust * 0.7)  # Weight gusts less but still important
    
    if max_wind <= 5:  # Ideal conditions
        windSc = 1.0
    elif max_wind <= 10:  # Light wind - still good
        windSc = 0.9
    elif max_wind <= 15:  # Moderate wind - manageable but challenging
        windSc = 0.6 - (max_wind - 10) * 0.06
    elif max_wind <= 25:  # Strong wind - difficult conditions
        windSc = 0.3 - (max_wind - 15) * 0.02
    else:  # Very strong wind - dangerous
        windSc = max(0.01, 0.1 - (max_wind - 25) * 0.01)

    # Flow (discharge) score - updated ranges with HARD SAFETY CUTOFF
    if flow >= 13000:  # HARD CUTOFF - NOT SAFE TO ROW
        flowSc = 0  # Zero score - absolutely not safe
    elif 2000 <= flow <= 8000:  # Optimal flow range for rowing
        flowSc = 1.0
    elif 8000 < flow < 13000:  # Higher flow - increasingly dangerous
        # Exponential decay from 8000 to 13000 cfs
        flowSc = max(0.05, exp(-3 * (flow - 8000) / 5000))
    elif 1000 <= flow < 2000:  # Low flow - may be shallow
        flowSc = 0.7 + (flow - 1000) * 0.3 / 1000
    elif flow < 1000:  # Very low flow - navigation issues
        flowSc = max(0.1, flow / 1000 * 0.7)
    else:  # Should not reach here, but safety fallback
        flowSc = 0

    # Water temperature score - safety-focused for rowing
    if water_temp is None:
        waterTempSc = 0.5  # Unknown water temp - moderate penalty
    elif water_temp >= 70:  # Warm water - safe for immersion
        waterTempSc = 1.0
    elif water_temp >= 60:  # Cool but safe with proper gear
        waterTempSc = 0.9
    elif water_temp >= 50:  # Cold - hypothermia risk increases
        waterTempSc = 0.6
    elif water_temp >= 40:  # Very cold - serious safety concern
        waterTempSc = 0.3
    else:  # Extremely cold water - life-threatening if immersed
        waterTempSc = 0.1

    # Precipitation score - more realistic for outdoor activity
    if prec >= 5:  # Heavy rain - dangerous and uncomfortable
        precipSc = 0.05
    elif prec >= 2:  # Moderate rain - poor conditions
        precipSc = 0.2
    elif prec >= 0.5:  # Light rain - manageable but not ideal
        precipSc = 0.5
    elif prec >= 0.1:  # Very light rain/drizzle
        precipSc = 0.8
    else:  # No precipitation
        precipSc = 1.0

    # UV index score - comfort and safety consideration
    if uv <= 2:  # Low UV - ideal
        uvSc = 1.0
    elif uv <= 5:  # Moderate UV - good conditions
        uvSc = 0.95
    elif uv <= 7:  # High UV - need sun protection
        uvSc = 0.8
    elif uv <= 10:  # Very high UV - significant sun protection needed
        uvSc = 0.5
    else:  # Extreme UV - dangerous exposure
        uvSc = 0.2
    
    # Safety score - can override all other factors
    safetySc = safety_alert_score(weather_alerts, visibility, lightning_potential, precip_prob)

    # Compute combined score with weighted factors
    # Wind and safety are most critical, followed by temperature and flow
    raw_score = 10 * (
        tempSc * 0.8 *      # Temperature weight: 0.8
        windSc * 1.0 *      # Wind weight: 1.0 (most important)
        flowSc * 0.9 *      # Flow weight: 0.9 (very important)
        precipSc * 0.8 *    # Precipitation weight: 0.8
        uvSc * 0.6 *        # UV weight: 0.6 (comfort factor)
        waterTempSc * 0.7 * # Water temp weight: 0.7 (safety factor)
        safetySc * 1.2      # Safety weight: 1.2 (override factor)
    ) / (0.8 + 1.0 + 0.9 + 0.8 + 0.6 + 0.7 + 1.2)  # Normalize weights
    
    score = clamp(round(raw_score, 2), 0, 10)
    return score


def merge_params(weather, water):
    return { **weather, **water }