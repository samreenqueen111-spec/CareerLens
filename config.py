import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration with shared application settings."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-careerlens-stage-1")
    
    # Upload configuration
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5 MB
    ALLOWED_EXTENSIONS = set(
        os.environ.get("ALLOWED_EXTENSIONS", "pdf,docx").lower().split(",")
    )
    UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads")
    
    # Application metadata
    APP_NAME = "CareerLens AI"
    APP_VERSION = "1.0.0-stage9"
    
    # Stage 7 Database Configuration (SQLite)
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "careerlens.db"))
    DATABASE_URL = os.environ.get("DATABASE_URL", None)

    # Stage 8 Session & Security Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    ENV = "development"


class ProductionConfig(Config):
    """Production environment configuration with hardened defaults."""
    DEBUG = False
    TESTING = False
    ENV = "production"
    
    # In production, require an explicit secure SECRET_KEY
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # Fallback to avoid crash in preview, but log warning
        SECRET_KEY = "production-must-set-explicit-secret-key"


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = False
    TESTING = True
    ENV = "testing"
    WTF_CSRF_ENABLED = False
    DATABASE_PATH = os.environ.get("TEST_DATABASE_PATH", str(BASE_DIR / "test_careerlens.db"))


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Retrieve configuration based on FLASK_ENV or default to development."""
    env_name = os.environ.get("FLASK_ENV", "development").lower()
    return config_by_name.get(env_name, DevelopmentConfig)
