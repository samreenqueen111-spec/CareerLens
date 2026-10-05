"""
API Blueprint: RESTful endpoints for real resume parsing,
resume submission, history management, and test fixtures.
"""

import uuid
from flask import Blueprint, request, jsonify, current_app, g, session, make_response
from werkzeug.utils import secure_filename
from app.services.resume_parser import ResumeParser, ResumeParserError
from app.services.job_analyzer import JobAnalyzer, JobAnalyzerError
from app.services.matcher import ResumeJobMatcher, MatcherError
from app.services.skill_gap_analyzer import SkillGapAnalyzer, SkillGapError
from app.services.ats_analyzer import AtsAnalyzer, AtsAnalyzerError
from app.services.roadmap_generator import RoadmapGenerator, RoadmapError
from app.services.analysis_service import AnalysisService
from app.services.storage_service import storage_service

api_bp = Blueprint("api", __name__, url_prefix="/api")
analysis_service = AnalysisService()


SAMPLE_JDS = {
    "fullstack": {
        "title": "Senior Full Stack Software Engineer",
        "company": "Starlight Technologies",
        "description": """About the Role:
We are seeking an experienced Senior Full Stack Software Engineer to lead development of our distributed cloud web platform. You will collaborate with product designers, backend engineers, and DevOps to deliver reliable, high-performance web applications.

Responsibilities:
- Architect, build, and maintain scalable user interfaces using modern React and TypeScript.
- Design resilient RESTful microservices and backend data pipelines in Python (Flask/FastAPI) and SQL.
- Implement robust caching layers using Redis and manage messaging queues.
- Deploy and monitor microservices in containerized environments with Docker and Kubernetes (K8s).
- Write comprehensive unit, integration, and end-to-end tests; champion CI/CD best practices.

Requirements:
- 4+ years of production experience in full-stack web development.
- Deep proficiency in JavaScript/TypeScript, modern React, and Python or Node.js.
- Strong fundamentals in relational databases (PostgreSQL/MySQL) and query optimization.
- Working knowledge of containerization (Docker) and Kubernetes orchestration.
- Familiarity with modern API paradigms including REST and GraphQL.
- Excellent communication skills and passion for mentorship in an agile environment."""
    },
    "frontend": {
        "title": "Staff Frontend Platform Engineer",
        "company": "Veloce Cloud Systems",
        "description": """About the Role:
Join our Design Systems & Frontend Platform team to build the foundational component libraries, build tooling, and web performance infrastructure supporting millions of global users.

Responsibilities:
- Architect and evolve our enterprise Design System using React, TypeScript, and Tailwind CSS.
- Optimize web core vitals (LCP, FID, CLS) and client-side rendering performance.
- Partner with UX designers to ensure WCAG AA accessibility compliance across all components.
- Establish best practices for state management, micro-frontends, and automated UI testing.

Requirements:
- 5+ years of dedicated web frontend engineering experience.
- Mastery of modern JavaScript (ES6+), TypeScript, CSS architecture, and React.
- Proven track record of improving web performance and accessibility at scale.
- Experience with testing suites (Jest, Playwright, Storybook)."""
    },
    "devops": {
        "title": "Cloud Infrastructure & DevOps Engineer",
        "company": "Nordic Data Grid",
        "description": """About the Role:
We are looking for a DevOps Engineer to manage our multi-region AWS infrastructure, automate CI/CD release engineering, and strengthen cloud security posture.

Responsibilities:
- Write and maintain Infrastructure as Code using Terraform and CloudFormation.
- Manage Kubernetes clusters (EKS), ingress routing, and service mesh architectures.
- Build automated deployment pipelines using GitHub Actions and ArgoCD.
- Monitor infrastructure observability with Prometheus, Grafana, and Datadog.

Requirements:
- 3+ years experience managing cloud infrastructure (AWS/GCP).
- Strong command of Docker, Kubernetes, Linux systems, and bash/Python scripting.
- Hands-on experience with Terraform, CI/CD automation, and cloud security compliance."""
    }
}


@api_bp.route("/parse-resume", methods=["POST"])
def parse_resume():
    """
    Stage 2 Real Resume Parsing Endpoint.
    Accepts PDF or DOCX file upload, extracts raw text, computes counts,
    and detects common resume sections.
    """
    file = request.files.get("resume")
    if not file or file.filename == "":
        return jsonify({
            "success": False,
            "error": "No resume file selected. Please upload a PDF or DOCX document."
        }), 400

    filename = secure_filename(file.filename)
    
    # Calculate file size
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    try:
        # Real text extraction & section detection
        parsed_result = ResumeParser.parse_document(file.stream, filename, file_size)

        # Safely store upload in non-public directory
        upload_dir = current_app.config.get("UPLOAD_FOLDER")
        if upload_dir:
            file.seek(0)
            ResumeParser.save_secure_upload(file, upload_dir)

        # Store in active session cache for seamless re-analysis
        session_key = session.get("resume_session_id")
        if not session_key:
            session_key = uuid.uuid4().hex
            session["resume_session_id"] = session_key

        storage_service.set_active_resume(session_key, parsed_result)
        user = getattr(g, "user", None)
        if user:
            storage_service.set_active_resume(f"user_{user.id}", parsed_result)

        session["active_resume_name"] = filename
        session["active_resume_size_kb"] = parsed_result.get("file_size_kb", 0)

        return jsonify(parsed_result), 200

    except ResumeParserError as parse_err:
        return jsonify({
            "success": False,
            "error": parse_err.message,
            "code": parse_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred while parsing the document: {str(e)}",
            "code": "SERVER_ERROR"
        }), 500


@api_bp.route("/active-resume", methods=["GET", "DELETE"])
def active_resume_endpoint():
    """
    Manage the active resume in the current session.
    GET: Check if an active resume is currently loaded and return summary metadata.
    DELETE: Clear the active resume from the current session.
    """
    session_key = session.get("resume_session_id")
    user = getattr(g, "user", None)

    if request.method == "DELETE":
        if session_key:
            storage_service.clear_active_resume(session_key)
        if user:
            storage_service.clear_active_resume(f"user_{user.id}")
        session.pop("active_resume_name", None)
        session.pop("active_resume_size_kb", None)
        return jsonify({"success": True, "message": "Active resume cleared from session."})

    active = None
    if session_key:
        active = storage_service.get_active_resume(session_key)
    if not active and user:
        active = storage_service.get_active_resume(f"user_{user.id}")

    if active:
        return jsonify({
            "has_resume": True,
            "filename": active.get("filename", session.get("active_resume_name", "Uploaded_Resume.pdf")),
            "file_size_kb": active.get("file_size_kb", 0),
            "word_count": active.get("word_count", 0),
            "char_count": active.get("char_count", 0),
            "sections_count": active.get("sections_count", 0),
            "total_expected_sections": active.get("total_expected_sections", 8),
            "file_type": active.get("file_type", "Document")
        })

    return jsonify({"has_resume": False})


@api_bp.route("/analyze-jd", methods=["POST"])
def analyze_job_description():
    """
    Stage 3 Real Job Description Analysis Endpoint.
    Extracts required technical skills, preferred skills, soft skills,
    education requirements, experience requirements, and key domain keywords.
    """
    if request.is_json:
        payload = request.get_json() or {}
        jd_text = payload.get("job_description", "").strip()
        job_title = payload.get("job_title", "").strip()
    else:
        jd_text = request.form.get("job_description", "").strip()
        job_title = request.form.get("job_title", "").strip()

    try:
        analysis_data = JobAnalyzer.analyze_job_description(jd_text, job_title)
        return jsonify(analysis_data), 200
    except JobAnalyzerError as jd_err:
        return jsonify({
            "success": False,
            "error": jd_err.message,
            "code": jd_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred while analyzing the job description: {str(e)}",
            "code": "SERVER_ERROR"
        }), 500


@api_bp.route("/analyze", methods=["POST"])
def analyze_resume():
    """
    Handle resume upload and job description submission.
    Parses document text, analyzes current job description requirements, coordinates report,
    and stores entry in analysis history with real extracted content.
    Supports recalculation from new Job Title, Company, or Job Description using newly uploaded
    or currently active session resume.
    """
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        job_title = payload.get("job_title", "").strip()
        job_description = payload.get("job_description", "").strip()
        company = payload.get("company", "").strip()
    else:
        job_title = request.form.get("job_title", "").strip()
        job_description = request.form.get("job_description", "").strip()
        company = request.form.get("company", "").strip()

    file = request.files.get("resume") if request.files else None

    parsed_doc = None
    filename = None

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        # 1. Perform real resume parsing & validation
        try:
            parsed_doc = ResumeParser.parse_document(file.stream, filename, file_size)
        except ResumeParserError as parse_err:
            return jsonify({
                "success": False,
                "error": parse_err.message,
                "code": parse_err.code
            }), 400
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to parse resume document: {str(e)}",
                "code": "PARSING_FAILED"
            }), 400

        # Safely save upload
        upload_dir = current_app.config.get("UPLOAD_FOLDER")
        if upload_dir:
            file.seek(0)
            ResumeParser.save_secure_upload(file, upload_dir)

        # Cache active parsed resume for this session & user
        session_key = session.get("resume_session_id")
        if not session_key:
            session_key = uuid.uuid4().hex
            session["resume_session_id"] = session_key

        storage_service.set_active_resume(session_key, parsed_doc)
        user = getattr(g, "user", None)
        if user:
            storage_service.set_active_resume(f"user_{user.id}", parsed_doc)

        session["active_resume_name"] = filename
        session["active_resume_size_kb"] = parsed_doc.get("file_size_kb", 0)

    else:
        # Check active resume from current session or user profile
        session_key = session.get("resume_session_id")
        user = getattr(g, "user", None)
        active_doc = None
        if session_key:
            active_doc = storage_service.get_active_resume(session_key)
        if not active_doc and user:
            active_doc = storage_service.get_active_resume(f"user_{user.id}")

        if active_doc:
            parsed_doc = active_doc
            filename = active_doc.get("filename", session.get("active_resume_name", "Uploaded_Resume.pdf"))
        else:
            return jsonify({
                "success": False,
                "error": "Please select a resume file (.pdf or .docx) to proceed."
            }), 400

    # 2. Perform real job description analysis & validation on current inputs (Stage 3)
    try:
        jd_analysis = JobAnalyzer.analyze_job_description(job_description, job_title)
    except JobAnalyzerError as jd_err:
        return jsonify({
            "success": False,
            "error": jd_err.message,
            "code": jd_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to analyze job description: {str(e)}",
            "code": "JD_ANALYSIS_FAILED"
        }), 400

    if not job_title:
        job_title = jd_analysis.get("job_title") or "Target Role"

    # 3. Perform real Resume-to-Job Matching with newly provided data (Stage 4, 5, 6)
    try:
        analysis_result = analysis_service.run_analysis(
            resume_filename=filename,
            job_title=job_title,
            job_description=job_description,
            company=company,
            parsed_resume=parsed_doc,
            job_analysis=jd_analysis
        )
    except MatcherError as match_err:
        return jsonify({
            "success": False,
            "error": match_err.message,
            "code": match_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to match resume with job description: {str(e)}",
            "code": "MATCHING_FAILED"
        }), 500

    # Attach real parsed resume metadata (Stage 2)
    analysis_result["resume_filename"] = filename
    analysis_result["resume_size_kb"] = parsed_doc["file_size_kb"]
    analysis_result["parsed_resume"] = {
        "filename": filename,
        "file_type": parsed_doc["file_type"],
        "char_count": parsed_doc["char_count"],
        "word_count": parsed_doc["word_count"],
        "line_count": parsed_doc["line_count"],
        "preview_text": parsed_doc["preview_text"],
        "full_text": parsed_doc["full_text"],
        "sections": parsed_doc["sections"],
        "missing_sections": parsed_doc["missing_sections"],
        "sections_count": parsed_doc["sections_count"],
        "total_expected_sections": parsed_doc["total_expected_sections"],
        "section_contents": parsed_doc["section_contents"],
        "contact_details": parsed_doc["contact_details"]
    }

    # Attach real job description analysis (Stage 3)
    analysis_result["job_analysis"] = jd_analysis

    # Record into history store with full report attached
    user = getattr(g, "user", None)
    user_id = user.id if user else None

    history_record = storage_service.add_record(
        job_title=analysis_result["job_title"],
        company=analysis_result["company"],
        filename=filename,
        scores=analysis_result["scores"],
        full_analysis=analysis_result,
        user_id=user_id
    )
    analysis_result["id"] = history_record["id"]
    session["last_analysis_id"] = analysis_result["id"]

    resp = make_response(jsonify({
        "success": True,
        "message": f"Analysis complete. Overall match: {analysis_result['scores']['overall_match']}%, Skills: {analysis_result['scores']['skills_match']}%, Keywords: {analysis_result['scores']['keyword_match']}%.",
        "analysis_id": analysis_result["id"],
        "redirect_url": f"/dashboard?id={analysis_result['id']}&job_title={job_title}",
        "data": analysis_result
    }), 200)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@api_bp.route("/history", methods=["GET"])
def get_history():
    """Retrieve historical analyses for current user or public demo records."""
    user = getattr(g, "user", None)
    if user:
        records = storage_service.get_all_history(user_id=user.id)
    else:
        records = storage_service.get_all_history(public_only=True)
    return jsonify({
        "success": True,
        "count": len(records),
        "history": records
    })


@api_bp.route("/history/<record_id>", methods=["GET"])
def get_history_item(record_id: str):
    """Retrieve details for a specific history record enforcing ownership."""
    from database.models import AnalysisModel
    model = AnalysisModel.get_by_id(record_id)
    if not model:
        return jsonify({
            "success": False,
            "error": f"Analysis record '{record_id}' not found."
        }), 404

    user = getattr(g, "user", None)
    if model.user_id:
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required to access this personal analysis.",
                "code": "UNAUTHORIZED"
            }), 401
        if user.id != model.user_id:
            return jsonify({
                "success": False,
                "error": "Forbidden: You do not have permission to view this analysis.",
                "code": "FORBIDDEN"
            }), 403

    return jsonify({
        "success": True,
        "data": model.to_summary_dict()
    })


@api_bp.route("/history/<record_id>", methods=["DELETE"])
def delete_history_item(record_id: str):
    """Remove a history record by ID enforcing ownership."""
    from database.models import AnalysisModel
    model = AnalysisModel.get_by_id(record_id)
    if not model:
        return jsonify({
            "success": False,
            "error": f"Analysis record '{record_id}' not found."
        }), 404

    user = getattr(g, "user", None)
    if model.user_id:
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required to delete this personal analysis.",
                "code": "UNAUTHORIZED"
            }), 401
        if user.id != model.user_id:
            return jsonify({
                "success": False,
                "error": "Forbidden: You do not have permission to delete this analysis.",
                "code": "FORBIDDEN"
            }), 403
        deleted = storage_service.delete_record(record_id, user_id=user.id)
    else:
        deleted = storage_service.delete_record(record_id)

    if not deleted:
        return jsonify({
            "success": False,
            "error": f"Analysis record '{record_id}' not found."
        }), 404

    return jsonify({
        "success": True,
        "message": f"Analysis record '{record_id}' successfully removed."
    })


@api_bp.route("/sample-jd/<role_key>", methods=["GET"])
def get_sample_job_description(role_key: str):
    """Retrieve sample job description for quick testing in UI."""
    sample = SAMPLE_JDS.get(role_key.lower())
    if not sample:
        sample = SAMPLE_JDS["fullstack"]
    return jsonify({
        "success": True,
        "data": sample
    })


@api_bp.route("/match", methods=["POST"])
def match_resume_and_job():
    """
    Stage 4 Real Resume-to-Job Matching Endpoint.
    Accepts structured or raw resume and JD data, evaluates skills,
    keywords, education, and experience, returning transparent scores.
    """
    payload = request.get_json(silent=True) or {}

    parsed_resume = payload.get("parsed_resume")
    job_analysis = payload.get("job_analysis")

    # If raw resume text is provided, build a minimal structured container
    if not parsed_resume:
        resume_text = payload.get("resume_text") or request.form.get("resume_text", "")
        if not resume_text:
            return jsonify({
                "success": False,
                "error": "Missing resume data. Provide 'parsed_resume' object or 'resume_text'.",
                "code": "MISSING_RESUME_DATA"
            }), 400
        parsed_resume = {
            "full_text": resume_text,
            "section_contents": {
                "Skills": resume_text,
                "Experience": resume_text,
                "Education": resume_text
            }
        }

    # If raw JD text is provided, analyze using JobAnalyzer
    if not job_analysis:
        jd_text = payload.get("job_description") or request.form.get("job_description", "")
        job_title = payload.get("job_title") or request.form.get("job_title", "")
        if not jd_text:
            return jsonify({
                "success": False,
                "error": "Missing job description data. Provide 'job_analysis' object or 'job_description'.",
                "code": "MISSING_JD_DATA"
            }), 400
        try:
            job_analysis = JobAnalyzer.analyze_job_description(jd_text, job_title)
        except JobAnalyzerError as jd_err:
            return jsonify({
                "success": False,
                "error": jd_err.message,
                "code": jd_err.code
            }), 400

    try:
        match_result = ResumeJobMatcher.match(parsed_resume, job_analysis)
        return jsonify(match_result), 200
    except MatcherError as match_err:
        return jsonify({
            "success": False,
            "error": match_err.message,
            "code": match_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred during matching: {str(e)}",
            "code": "SERVER_ERROR"
        }), 500


@api_bp.route("/skill-gap", methods=["POST"])
def analyze_skill_gap():
    """
    Stage 5 Skill Gap Analysis Endpoint.
    Analyzes missing required skills, preferred qualifications, weak/shallow matches,
    and transferable competencies with concrete learning directions.
    """
    payload = request.get_json(silent=True) or {}

    parsed_resume = payload.get("parsed_resume")
    job_analysis = payload.get("job_analysis")
    match_result = payload.get("match_result")

    # If raw resume text is provided, build structured container
    if not parsed_resume:
        resume_text = payload.get("resume_text") or request.form.get("resume_text", "")
        if not resume_text:
            return jsonify({
                "success": False,
                "error": "Missing resume data. Provide 'parsed_resume' or 'resume_text'.",
                "code": "MISSING_RESUME_DATA"
            }), 400
        parsed_resume = {
            "full_text": resume_text,
            "section_contents": {
                "Skills": resume_text,
                "Experience": resume_text,
                "Education": resume_text
            }
        }

    # If raw JD text is provided, analyze using JobAnalyzer
    if not job_analysis:
        jd_text = payload.get("job_description") or request.form.get("job_description", "")
        job_title = payload.get("job_title") or request.form.get("job_title", "")
        if not jd_text:
            return jsonify({
                "success": False,
                "error": "Missing job description data. Provide 'job_analysis' or 'job_description'.",
                "code": "MISSING_JD_DATA"
            }), 400
        try:
            job_analysis = JobAnalyzer.analyze_job_description(jd_text, job_title)
        except JobAnalyzerError as jd_err:
            return jsonify({
                "success": False,
                "error": jd_err.message,
                "code": jd_err.code
            }), 400

    # If match_result is not pre-computed, execute ResumeJobMatcher
    if not match_result:
        try:
            match_result = ResumeJobMatcher.match(parsed_resume, job_analysis)
        except MatcherError as match_err:
            return jsonify({
                "success": False,
                "error": match_err.message,
                "code": match_err.code
            }), 400

    try:
        gap_data = SkillGapAnalyzer.analyze(match_result, job_analysis, parsed_resume)
        return jsonify(gap_data), 200
    except SkillGapError as gap_err:
        return jsonify({
            "success": False,
            "error": gap_err.message,
            "code": gap_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred during skill gap analysis: {str(e)}",
            "code": "SERVER_ERROR"
        }), 500


@api_bp.route("/ats-audit", methods=["POST"])
def analyze_ats_compatibility():
    """
    Stage 5 Transparent ATS-Style Resume Audit Endpoint.
    Analyzes contact anchors, section structure, impact metrics, keywords,
    and readability, returning a 0-100 score and diagnostic checklist.
    """
    payload = request.get_json(silent=True) or {}

    parsed_resume = payload.get("parsed_resume")
    job_analysis = payload.get("job_analysis")
    target_job_title = payload.get("target_job_title") or payload.get("job_title")

    # If raw resume text is provided, build structured container
    if not parsed_resume:
        resume_text = payload.get("resume_text") or request.form.get("resume_text", "")
        if not resume_text:
            return jsonify({
                "success": False,
                "error": "Missing resume data. Provide 'parsed_resume' or 'resume_text'.",
                "code": "MISSING_RESUME_DATA"
            }), 400
        parsed_resume = {
            "full_text": resume_text,
            "word_count": len(resume_text.split()),
            "char_count": len(resume_text),
            "section_contents": {
                "Skills": resume_text,
                "Experience": resume_text,
                "Education": resume_text
            },
            "sections_detected": ["Skills", "Experience", "Education"]
        }

    # If raw JD text is provided, analyze using JobAnalyzer
    if not job_analysis and (payload.get("job_description") or request.form.get("job_description")):
        jd_text = payload.get("job_description") or request.form.get("job_description")
        try:
            job_analysis = JobAnalyzer.analyze_job_description(jd_text, target_job_title or "")
        except JobAnalyzerError:
            job_analysis = None

    try:
        ats_result = AtsAnalyzer.analyze(
            parsed_resume=parsed_resume,
            job_analysis=job_analysis,
            target_job_title=target_job_title
        )
        return jsonify(ats_result), 200
    except AtsAnalyzerError as ats_err:
        return jsonify({
            "success": False,
            "error": ats_err.message,
            "code": ats_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred during ATS audit: {str(e)}",
            "code": "SERVER_ERROR"
        }), 500


@api_bp.route("/roadmap", methods=["POST"])
def generate_career_roadmap():
    """
    Stage 6 Personalized Career Learning Roadmap Endpoint.
    Accepts raw text or structured resume, JD, and matching payloads, returning
    a 3-phase progression with Recommended Next Step and beginner-friendly steps.
    """
    payload = request.get_json(silent=True) or {}

    parsed_resume = payload.get("parsed_resume")
    job_analysis = payload.get("job_analysis")
    match_result = payload.get("match_result")
    skill_gap_analysis = payload.get("skill_gap_analysis")
    ats_analysis = payload.get("ats_analysis")
    target_job_title = payload.get("target_job_title") or payload.get("job_title")

    # If raw resume text is provided, build structured container
    if not parsed_resume:
        resume_text = payload.get("resume_text") or request.form.get("resume_text", "")
        if not resume_text:
            return jsonify({
                "success": False,
                "error": "Missing resume data. Provide 'parsed_resume' or 'resume_text'.",
                "code": "MISSING_PARSED_RESUME"
            }), 400
        parsed_resume = {
            "full_text": resume_text,
            "word_count": len(resume_text.split()),
            "char_count": len(resume_text),
            "section_contents": {
                "Skills": resume_text,
                "Experience": resume_text,
                "Education": resume_text
            },
            "sections_detected": ["Skills", "Experience", "Education"]
        }

    # If raw JD text is provided, analyze using JobAnalyzer
    if not job_analysis:
        jd_text = payload.get("job_description") or request.form.get("job_description", "")
        if not jd_text:
            return jsonify({
                "success": False,
                "error": "Missing job description. Provide 'job_analysis' or 'job_description'.",
                "code": "MISSING_JD_ANALYSIS"
            }), 400
        try:
            job_analysis = JobAnalyzer.analyze_job_description(jd_text, target_job_title or "")
        except JobAnalyzerError as jd_err:
            return jsonify({
                "success": False,
                "error": jd_err.message,
                "code": jd_err.code
            }), 400

    try:
        roadmap_data = RoadmapGenerator.generate(
            parsed_resume=parsed_resume,
            job_analysis=job_analysis,
            match_result=match_result,
            skill_gap_analysis=skill_gap_analysis,
            ats_analysis=ats_analysis,
            target_job_title=target_job_title
        )
        return jsonify(roadmap_data), 200
    except RoadmapError as r_err:
        return jsonify({
            "success": False,
            "error": r_err.message,
            "code": r_err.code
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred during roadmap generation: {str(e)}",
            "code": "SERVER_ERROR"
        }), 500


@api_bp.route("/reports/<analysis_id>/download", methods=["GET"])
def api_download_report(analysis_id: str):
    """
    API endpoint to download candidate evaluation report as PDF (Stage 9).
    Enforces that only the logged-in owner can download their report.
    """
    from database.models import AnalysisModel
    from services.report_generator import ReportGenerator
    from flask import send_file
    import io

    user = getattr(g, "user", None)
    user_id = user.id if user else None

    if analysis_id == "sample-preview":
        from app.services.sample_data import get_sample_analysis
        report_data = get_sample_analysis()
        report_data["id"] = "sample-preview"
    else:
        model = AnalysisModel.get_by_id(analysis_id)
        if not model:
            return jsonify({
                "success": False,
                "error": f"Analysis record '{analysis_id}' not found.",
                "code": "NOT_FOUND"
            }), 404

        if model.user_id:
            if not user:
                return jsonify({
                    "success": False,
                    "error": "Authentication required to download this report.",
                    "code": "UNAUTHORIZED"
                }), 401
            if model.user_id != user.id:
                return jsonify({
                    "success": False,
                    "error": "Forbidden: You do not have permission to download this report.",
                    "code": "FORBIDDEN"
                }), 403

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
        return jsonify({
            "success": False,
            "error": f"Failed to generate PDF report: {str(e)}",
            "code": "PDF_GENERATION_FAILED"
        }), 500


