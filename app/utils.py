# app/utils.py

def clamp(val, min_val, max_val):
    if val is None:
        return None
    return max(min_val, min(max_val, val))


def fmt(v, decs=0, unit=""):
    if v is None:
        return "N/A"
    try:
        return f"{v:.{decs}f}{unit}"
    except (TypeError, ValueError):
        return str(v)


def deg_to_cardinal(deg):
    try:
        dirs = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        idx = int((float(deg) % 360) / 22.5 + 0.5) % 16
        return dirs[idx]
    except Exception:
        return "N/A"