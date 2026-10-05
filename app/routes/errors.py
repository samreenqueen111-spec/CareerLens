"""
Error Handlers: Clean, user-friendly responses for HTTP errors
with automatic JSON fallback for API requests.
"""

from flask import Blueprint, render_template, request, jsonify

errors_bp = Blueprint("errors", __name__)


def is_json_request():
    """Check if incoming request expects JSON or targets /api/."""
    return (
        request.path.startswith("/api/")
        or request.accept_mimetypes.best == "application/json"
    )


@errors_bp.app_errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request."""
    if is_json_request():
        return jsonify({
            "success": False,
            "error": "Bad Request",
            "message": str(error)
        }), 400
    return render_template(
        "errors/400.html",
        page_title="Bad Request - CareerLens AI",
        error_code=400,
        error_message="The request could not be processed due to invalid parameters or formatting."
    ), 400


@errors_bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found."""
    if is_json_request():
        return jsonify({
            "success": False,
            "error": "Resource Not Found",
            "message": "The requested endpoint or resource does not exist."
        }), 404
    return render_template(
        "errors/404.html",
        page_title="Page Not Found - CareerLens AI",
        error_code=404,
        error_message="The page or resource you are looking for does not exist or has been relocated."
    ), 404


@errors_bp.app_errorhandler(413)
def request_entity_too_large(error):
    """Handle 413 Payload / File Too Large."""
    if is_json_request():
        return jsonify({
            "success": False,
            "error": "File Too Large",
            "message": "The uploaded resume exceeds the maximum 5MB size limit."
        }), 413
    return render_template(
        "errors/413.html",
        page_title="File Size Exceeded - CareerLens AI",
        error_code=413,
        error_message="The uploaded document exceeds the maximum allowed size of 5 MB. Please compress your PDF or DOCX file."
    ), 413


@errors_bp.app_errorhandler(500)
def internal_server_error(error):
    """Handle 500 Internal Server Error."""
    if is_json_request():
        return jsonify({
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing the request."
        }), 500
    return render_template(
        "errors/500.html",
        page_title="Server Error - CareerLens AI",
        error_code=500,
        error_message="An internal server error occurred. Our engineering logs have been notified."
    ), 500
