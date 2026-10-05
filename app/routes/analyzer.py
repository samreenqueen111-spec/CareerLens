"""
Analyzer Blueprint: Core application interface routes for
Resume Analysis, Results Dashboard, and Analysis History.
"""

from flask import Blueprint, render_template, request, redirect, url_for
from app.services.sample_data import get_sample_analysis
from app.services.storage_service import storage_service

analyzer_bp = Blueprint("analyzer", __name__)


@analyzer_bp.route("/analyzer")
def analyzer_view():
    """Render the primary Resume Analyzer interface with active resume pre-population."""
    from flask import session, g
    session_key = session.get("resume_session_id")
    user = getattr(g, "user", None)
    active_resume = None
    if session_key:
        active_resume = storage_service.get_active_resume(session_key)
    if not active_resume and user:
        active_resume = storage_service.get_active_resume(f"user_{user.id}")

    return render_template(
        "pages/analyzer.html",
        page_title="Resume Analyzer - CareerLens",
        active_page="analyzer",
        active_resume=active_resume
    )


@analyzer_bp.route("/dashboard")
def dashboard_view():
    """
    Render the comprehensive Results Dashboard.
    Supports query param ?id=<analysis_id> to view specific reports.
    If no id is provided, automatically loads the user's latest analysis if present.
    Enforces privacy: personal analyses are only accessible to their owner.
    Guarantees no stale browser caching.
    """
    from database.models import AnalysisModel
    from flask import abort, flash, g, session, make_response

    user = getattr(g, "user", None)
    user_id = user.id if user else None

    # Resolve requested analysis id
    analysis_id = request.args.get("id")
    if not analysis_id:
        # Check if user just completed an analysis in session
        if session.get("last_analysis_id"):
            analysis_id = session.get("last_analysis_id")
        else:
            analysis_id = "sample-preview"

    job_title = request.args.get("job_title", "Senior Full Stack Software Engineer")
    company = request.args.get("company", "Starlight Technologies")

    # Check if a real stored analysis report exists
    stored_report = None
    if analysis_id and analysis_id != "sample-preview":
        model = AnalysisModel.get_by_id(analysis_id)
        if model:
            if model.user_id:
                # Personal analysis owned by a user
                if not user:
                    flash("Please sign in to access your personal analysis report.", "warning")
                    return redirect(url_for("auth.login_view", next=request.full_path if request.query_string else request.path))
                if model.user_id != user.id:
                    abort(403)
            stored_report = storage_service.get_analysis_report(analysis_id, user_id=user_id)
            if not stored_report:
                stored_report = model.to_full_dict()

    if stored_report:
        analysis_data = stored_report
    else:
        # Fallback to structured preview data
        analysis_data = get_sample_analysis(job_title=job_title, company=company)
        if analysis_id and analysis_id != "sample-preview":
            analysis_data["id"] = analysis_id

    html = render_template(
        "pages/dashboard.html",
        page_title=f"Analysis Results: {analysis_data['job_title']} - CareerLens",
        active_page="dashboard",
        analysis=analysis_data
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@analyzer_bp.route("/history")
def history_view():
    """Render the user's historical analyses dashboard."""
    from flask import g
    user = getattr(g, "user", None)
    if user:
        history_items = storage_service.get_all_history(user_id=user.id)
    else:
        # Show public demo items or empty state
        history_items = storage_service.get_all_history(public_only=True)

    return render_template(
        "pages/history.html",
        page_title="Analysis History - CareerLens",
        active_page="history",
        history_items=history_items
    )


@analyzer_bp.route("/report/<analysis_id>/download", methods=["GET"])
@analyzer_bp.route("/dashboard/report/<analysis_id>", methods=["GET"])
def download_report_view(analysis_id: str):
    """
    Download official candidate evaluation report as PDF (Stage 9).
    Strictly verifies ownership: only the logged-in owner can download their report.
    """
    from database.models import AnalysisModel
    from services.report_generator import ReportGenerator, ReportGeneratorError
    from flask import abort, flash, g, send_file
    import io

    user = getattr(g, "user", None)
    user_id = user.id if user else None

    # Retrieve analysis record
    if analysis_id == "sample-preview":
        report_data = get_sample_analysis()
        report_data["id"] = "sample-preview"
    else:
        model = AnalysisModel.get_by_id(analysis_id)
        if not model:
            flash("The requested analysis record was not found.", "error")
            return redirect(url_for("analyzer.analyzer_view"))

        if model.user_id:
            if not user:
                flash("Please sign in to download your personal evaluation report.", "warning")
                return redirect(url_for("auth.login_view", next=request.full_path if request.query_string else request.path))
            if model.user_id != user.id:
                abort(403)

        report_data = storage_service.get_analysis_report(analysis_id, user_id=user_id)
        if not report_data:
            report_data = model.to_full_dict()

    try:
        pdf_bytes = ReportGenerator.generate_pdf(report_data)
        safe_title = "".join(c if c.isalnum() else "_" for c in report_data.get("job_title", "Evaluation"))[:30]
        filename = f"CareerLens_Report_{safe_title}_{analysis_id}.pdf"

        resp = send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    except Exception as e:
        flash(f"Failed to generate PDF report: {str(e)}", "error")
        return redirect(url_for("analyzer.dashboard_view", id=analysis_id))
