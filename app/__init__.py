# app/__init__.py

from flask import Flask
# Import instances from our new extensions file
from app.extensions import scheduler, redis_client
from app.routes import bp
import redis # <--- ADD THIS LINE to handle the exception type

def create_app():
    """
    Application factory: creates and configures the Flask app.
    """
    app = Flask(__name__)
    
    # --- Check Redis Connection ---
    try:
        redis_client.ping()
        print("Successfully connected to Redis!")
    except redis.exceptions.ConnectionError as e: # This will now work correctly
        print(f"Could not connect to Redis: {e}")
        pass

    # --- Register Blueprints ---
    app.register_blueprint(bp)

    # --- Initialize Scheduler and Add Jobs ---
    # Import tasks here, inside the factory, to ensure the app context is available
    # and to avoid circular imports.
    with app.app_context():
        from app.tasks import update_weather_data_job, update_water_data_job, update_forecast_scores_job

        if not scheduler.running:
            scheduler.init_app(app) # Initialize scheduler with the app
            scheduler.start()

        # Clear existing jobs to prevent duplicates during reloads
        scheduler.remove_all_jobs()
        
        # Add new jobs
        scheduler.add_job(
            id='Update Weather Data',
            func=update_weather_data_job,
            trigger='interval',
            minutes=10  # Reduced frequency for API rate limiting
        )
        scheduler.add_job(
            id='Update Water Data',
            func=update_water_data_job,
            trigger='interval',
            minutes=15  # Reduced frequency for API rate limiting
        )
        scheduler.add_job(
            id='Update Forecast Scores',
            func=update_forecast_scores_job,
            trigger='interval',
            minutes=10  # Calculate forecast scores after data updates
        )

    return app