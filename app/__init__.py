"""
CareerLens AI - Application Factory.
Initializes Flask app, registers blueprints, configures extensions,
and provides context processors.
"""

import os
from datetime import datetime
from flask import Flask
from config import get_config


def create_app(config_class=None):
    """
    Construct and configure the Flask application instance using the Application Factory pattern.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Ensure uploads directory exists
    upload_dir = app.config.get("UPLOAD_FOLDER")
    if upload_dir:
        os.makedirs(upload_dir, exist_ok=True)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.analyzer import analyzer_bp
    from app.routes.api import api_bp
    from app.routes.errors import errors_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(analyzer_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(auth_bp)

    # Initialize SQLite database (Stage 7 & Stage 8)
    from database.database import init_db, close_db
    with app.app_context():
        init_db(seed_samples=True)

    app.teardown_appcontext(close_db)

    # User session loader for Stage 8
    from app.services.auth_service import get_current_user
    from flask import g

    @app.before_request
    def load_logged_in_user():
        g.user = get_current_user()

    # Global context processors for Jinja templates
    @app.context_processor
    def inject_global_template_vars():
        return {
            "app_name": app.config.get("APP_NAME", "CareerLens AI"),
            "app_version": app.config.get("APP_VERSION", "1.0.0-stage8"),
            "current_year": datetime.now().year,
            "current_user": getattr(g, "user", None),
            "max_file_size_mb": int(app.config.get("MAX_CONTENT_LENGTH", 5242880) / (1024 * 1024))
        }

    return app
