"""
Main Blueprint: Landing page, product overview, and application health.
"""

from flask import Blueprint, render_template, jsonify, current_app

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Render the high-converting SaaS landing page."""
    return render_template(
        "pages/index.html",
        page_title="CareerLens - Intelligent Resume & Job Description Matching",
        active_page="home"
    )


@main_bp.route("/about")
def about():
    """Render product philosophy, methodology, and architectural roadmap."""
    return render_template(
        "pages/about.html",
        page_title="About CareerLens - Methodology & Architecture",
        active_page="about"
    )


@main_bp.route("/privacy")
def privacy_view():
    """Render the Candidate Privacy & Data Security policy."""
    return render_template(
        "pages/privacy.html",
        page_title="Privacy & Data Protection - CareerLens",
        active_page="privacy"
    )


@main_bp.route("/health")
def health():
    """Application liveness and configuration health check."""
    return jsonify({
        "status": "healthy",
        "app": current_app.config.get("APP_NAME", "CareerLens"),
        "version": current_app.config.get("APP_VERSION", "1.0.0-stage9"),
        "stage": 9,
        "environment": current_app.config.get("ENV", "development"),
        "max_upload_bytes": current_app.config.get("MAX_CONTENT_LENGTH"),
        "allowed_extensions": list(current_app.config.get("ALLOWED_EXTENSIONS", []))
    })
