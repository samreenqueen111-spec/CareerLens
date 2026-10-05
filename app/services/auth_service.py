"""
Authentication and Authorization Service for CareerLens (Stage 8).
Manages user signup, login, session state, password validation, and route security decorators.
"""

import re
from functools import wraps
from typing import Optional, Tuple
from flask import session, request, redirect, url_for, flash, jsonify, g, has_request_context
from database.models import UserModel, DatabaseError

# RFC 5322 compliant simplified email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class AuthService:
    """Manages user authentication lifecycle and session credentials."""

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate email string structure and length."""
        if not email or not isinstance(email, str):
            return False, "Email address is required."
        clean = email.strip()
        if len(clean) > 254:
            return False, "Email address is too long."
        if not EMAIL_REGEX.match(clean):
            return False, "Please enter a valid email address (e.g. user@domain.com)."
        return True, None

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """Validate password meets security constraints."""
        if not password or not isinstance(password, str):
            return False, "Password is required."
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        if len(password) > 128:
            return False, "Password cannot exceed 128 characters."
        return True, None

    @classmethod
    def signup_user(
        cls,
        name: str,
        email: str,
        password: str,
        db_path: Optional[str] = None
    ) -> Tuple[Optional[UserModel], Optional[str]]:
        """
        Register a new user account with validated credentials and hashed password.
        Sets session user upon success if within request context.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            return None, "Please provide your full name."

        valid_email, email_err = cls.validate_email(email)
        if not valid_email:
            return None, email_err

        valid_pw, pw_err = cls.validate_password(password)
        if not valid_pw:
            return None, pw_err

        clean_email = email.strip().lower()

        # Check if email is already taken
        try:
            existing = UserModel.get_by_email(clean_email, db_path=db_path)
            if existing:
                return None, "An account with this email address already exists. Please log in."

            user = UserModel.create(
                name=clean_name,
                email=clean_email,
                password=password,
                db_path=db_path
            )
            # Establish session if in request context
            if has_request_context():
                session["user_id"] = user.id
                session.permanent = True
                g.user = user
            return user, None
        except DatabaseError as dbe:
            if dbe.code == "USER_EXISTS":
                return None, "An account with this email address already exists. Please log in."
            return None, dbe.message
        except Exception as e:
            return None, f"An unexpected database error occurred during registration: {str(e)}"

    @classmethod
    def login_user(
        cls,
        email: str,
        password: str,
        db_path: Optional[str] = None
    ) -> Tuple[Optional[UserModel], Optional[str]]:
        """
        Authenticate user credentials and establish session.
        Uses constant-time password comparison to prevent timing attacks.
        """
        if not email or not password:
            return None, "Both email and password are required."

        clean_email = email.strip().lower()

        try:
            user = UserModel.get_by_email(clean_email, db_path=db_path)
            if not user or not user.check_password(password):
                # Generic message to prevent account enumeration
                return None, "Invalid email or password. Please check your credentials."

            # Establish session if in request context
            if has_request_context():
                session["user_id"] = user.id
                session.permanent = True
                g.user = user
            return user, None
        except Exception as e:
            return None, f"An unexpected error occurred during login: {str(e)}"

    @staticmethod
    def logout_user() -> None:
        """Clear user session and reset context."""
        if has_request_context():
            session.pop("user_id", None)
            session.clear()
            g.user = None

    @staticmethod
    def get_current_user(db_path: Optional[str] = None) -> Optional[UserModel]:
        """Resolve the currently authenticated user from Flask session."""
        if not has_request_context():
            return None
        user_id = session.get("user_id")
        if not user_id:
            return None

        try:
            user = UserModel.get_by_id(user_id, db_path=db_path)
            if not user:
                # User was deleted or session is stale
                session.pop("user_id", None)
                return None
            return user
        except Exception:
            return None


def get_current_user(db_path: Optional[str] = None) -> Optional[UserModel]:
    """Helper forwarding to AuthService.get_current_user."""
    return AuthService.get_current_user(db_path=db_path)


def login_required(f):
    """Decorator requiring active user authentication for HTML view routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "user", None):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login_view", next=request.full_path if request.query_string else request.path))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """Decorator requiring active user authentication for JSON API routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "user", None):
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in to proceed.",
                "code": "UNAUTHORIZED"
            }), 401
        return f(*args, **kwargs)
    return decorated_function
