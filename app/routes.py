from flask import Blueprint, jsonify
from app.fetchers import fetch_weather_data, fetch_water_data
from app.rowcast import compute_rowcast, merge_params

bp = Blueprint("api", __name__)

@bp.route("/api/weather")
def weather():
    return jsonify(fetch_weather_data())

@bp.route("/api/water")
def water():
    return jsonify(fetch_water_data())

@bp.route("/api/rowcast")
def rowcast():
    weather = fetch_weather_data()
    water = fetch_water_data()
    params = merge_params(weather, water)
    score = compute_rowcast(params)
    return jsonify({ "rowcastScore": score, "params": params })