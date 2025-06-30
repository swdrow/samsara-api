# app/__init__.py

from flask import Flask
from app.routes import bp

def create_app():
    """
    Application factory: creates and configures the Flask app.
    """
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app
