"""
Auth Blueprint for CareerLens (Stage 8).
Provides web routes and JSON API endpoints for user registration, login, logout,
and session validation with secure password handling.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup_view():
    """Render and process the user registration form."""
    if getattr(g, "user", None):
        return redirect(url_for("analyzer.analyzer_view"))

    error_msg = None
    name = ""
    email = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user, err = AuthService.signup_user(name=name, email=email, password=password)
        if err:
            error_msg = err
        else:
            flash(f"Welcome to CareerLens, {user.name}! Your account has been created.", "success")
            next_url = request.args.get("next")
            # Basic open redirect guard
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("analyzer.analyzer_view"))

    return render_template(
        "pages/signup.html",
        page_title="Create Account - CareerLens",
        active_page="signup",
        error=error_msg,
        name=name,
        email=email
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login_view():
    """Render and process the user login form."""
    if getattr(g, "user", None):
        return redirect(url_for("analyzer.analyzer_view"))

    error_msg = None
    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user, err = AuthService.login_user(email=email, password=password)
        if err:
            error_msg = err
        else:
            flash(f"Welcome back, {user.name}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("analyzer.analyzer_view"))

    return render_template(
        "pages/login.html",
        page_title="Sign In - CareerLens",
        active_page="login",
        error=error_msg,
        email=email
    )


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout_view():
    """Terminate current user session and redirect to landing or login."""
    AuthService.logout_user()
    flash("You have been signed out securely.", "info")
    return redirect(url_for("auth.login_view"))


# --- JSON API Endpoints for Asynchronous / SPA interactions ---

@auth_bp.route("/api/auth/signup", methods=["POST"])
def api_signup():
    """JSON API endpoint for registering a new user."""
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    user, err = AuthService.signup_user(name=name, email=email, password=password)
    if err:
        return jsonify({
            "success": False,
            "error": err,
            "code": "SIGNUP_FAILED"
        }), 400

    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "user": user.to_dict()
    }), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    """JSON API endpoint for user authentication."""
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    user, err = AuthService.login_user(email=email, password=password)
    if err:
        return jsonify({
            "success": False,
            "error": err,
            "code": "AUTH_FAILED"
        }), 401

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.name}!",
        "user": user.to_dict()
    }), 200


@auth_bp.route("/api/auth/logout", methods=["POST"])
def api_logout():
    """JSON API endpoint to end current session."""
    AuthService.logout_user()
    return jsonify({
        "success": True,
        "message": "Signed out successfully."
    }), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_me():
    """Return currently authenticated user profile or null."""
    user = getattr(g, "user", None)
    if not user:
        return jsonify({
            "success": False,
            "authenticated": False,
            "user": None
        }), 200

    return jsonify({
        "success": True,
        "authenticated": True,
        "user": user.to_dict()
    }), 200
