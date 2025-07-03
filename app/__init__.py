# app/__init__.py

from flask import Flask
# Import instances from our new extensions file
from app.extensions import scheduler, redis_client
from app.routes import bp
import redis # <--- ADD THIS LINE to handle the exception type
import os

def create_app():
    """
    Application factory: creates and configures the Flask app.
    """
    app = Flask(__name__)
    
    # Configuration for development vs production
    env = os.getenv('FLASK_ENV', 'development')
    
    if env == 'production':
        # Production: serve built frontend files from dist/
        app.static_folder = os.path.join(os.path.dirname(app.root_path), 'dist')
        app.static_url_path = '/static'
        app.template_folder = os.path.join(os.path.dirname(app.root_path), 'dist')
    else:
        # Development: use standard Flask static/templates folders
        # Frontend dev server will handle static assets on port 3000
        pass

    # --- Check Redis Connection ---
    try:
        redis_client.ping()
        print("Successfully connected to Redis!")
    except redis.exceptions.ConnectionError as e: # This will now work correctly
        error_message = f"Could not connect to Redis: {e}"
        print(error_message)
        # Raise an exception to prevent the app from starting with a failed Redis connection:
        raise Exception(error_message)

    # --- Register Blueprints ---
    app.register_blueprint(bp)

    # --- Initialize Scheduler and Add Jobs ---
    # Import tasks here, inside the factory, to ensure the app context is available
    # and to avoid circular imports.
    with app.app_context():
        from app.tasks import update_weather_data_job, update_water_data_job, update_forecast_scores_job, update_short_term_forecast_job, update_noaa_stageflow_job, update_extended_weather_data_job, update_extended_forecast_scores_job

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
        scheduler.add_job(
            id='Update Short-term Forecast',
            func=update_short_term_forecast_job,
            trigger='interval',
            minutes=5  # Update 15-minute forecast more frequently
        )
        scheduler.add_job(
            id='Update NOAA Stageflow Data',
            func=update_noaa_stageflow_job,
            trigger='interval',
            minutes=30  # NOAA data updates less frequently
        )
        scheduler.add_job(
            id='Update Extended Weather Data',
            func=update_extended_weather_data_job,
            trigger='interval',
            minutes=60  # Extended weather data updates hourly
        )
        scheduler.add_job(
            id='Update Extended Forecast Scores',
            func=update_extended_forecast_scores_job,
            trigger='interval',
            minutes=30  # Calculate extended forecast scores after NOAA updates
        )
        # Run initial data fetch and forecasting immediately
        update_weather_data_job()
        update_water_data_job()
        update_noaa_stageflow_job()
        update_extended_weather_data_job()
        update_forecast_scores_job()
        update_extended_forecast_scores_job()
        update_short_term_forecast_job()

    return app