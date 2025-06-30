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


def compute_rowcast(params):
    # Safely extract parameters, defaulting to 0 for numeric calculations
    temp = params.get('apparentTemp')
    wind_speed = params.get('windSpeed')
    wind_gust = params.get('windGust')
    flow = params.get('discharge') if params.get('discharge') is not None else 0
    water_temp = params.get('waterTemp')
    prec = params.get('precipitation') if params.get('precipitation') is not None else 0
    uv = params.get('uvIndex') if params.get('uvIndex') is not None else 0

    # Temperature score
    tempSc = temp_score(temp)

    # Wind score
    windSc = min(
        exp_fall(wind_speed, 5, 25),
        exp_fall(wind_gust, 10, 35)
    )

    # Flow (discharge) score
    if flow <= 8000:
        flowSc = 1
    elif flow < 13000:
        flowSc = exp(-2 * (flow - 8000) / 5000)
    else:
        flowSc = 0

    # Water temperature score
    if water_temp is None or water_temp >= 50:
        waterTempSc = 1
    else:
        waterTempSc = exp(-2 * (50 - water_temp) / 15)

    # Precipitation score
    precipSc = exp(-1.5 * prec) if prec < 10 else 0

    # UV index score
    uvSc = 1 if uv < 8 else exp(-0.5 * (uv - 8))

    # Compute combined score
    raw_score = 10 * tempSc * windSc * flowSc * precipSc * uvSc * waterTempSc
    score = clamp(round(raw_score, 2), 0, 10)
    return score


def merge_params(weather, water):
    return { **weather, **water }