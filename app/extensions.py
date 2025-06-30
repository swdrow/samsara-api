# app/extensions.py

from flask_apscheduler import APScheduler
import redis

# --- Initialize Extensions ---
# Create the extension instances here, but don't initialize them with the app yet.
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
scheduler = APScheduler()