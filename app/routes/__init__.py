"""
Routes module for CareerLens AI.
Exports Blueprints for registration in the Flask application factory.
"""

from app.routes.main import main_bp
from app.routes.analyzer import analyzer_bp
from app.routes.api import api_bp
from app.routes.errors import errors_bp

__all__ = ["main_bp", "analyzer_bp", "api_bp", "errors_bp"]
