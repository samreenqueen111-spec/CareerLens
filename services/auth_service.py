"""
CareerLens AI - Authentication & Authorization Service Proxy (Stage 8).
Re-exports AuthService and decorators from app.services.auth_service.
"""

from app.services.auth_service import (
    AuthService,
    get_current_user,
    login_required,
    api_login_required,
    EMAIL_REGEX,
)

__all__ = [
    "AuthService",
    "get_current_user",
    "login_required",
    "api_login_required",
    "EMAIL_REGEX",
]
