"""
Storage Service for CareerLens AI (Stage 7).
Provides an interface for storing and managing analysis history and parsed resume reports
backed by persistent SQLite storage via AnalysisModel.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from database.models import AnalysisModel, DatabaseError


class StorageService:
    """
    Manages analysis records and full parsed reports using persistent SQLite storage
    with graceful fallback to in-memory cache if database exceptions occur.
    """

    def __init__(self):
        # In-memory mapping as resilient fallback
        self._history_store: List[Dict[str, Any]] = []
        self._analysis_store: Dict[str, Dict[str, Any]] = {}
        self._active_resumes: Dict[str, Dict[str, Any]] = {}

    def set_active_resume(self, key: str, resume_data: Dict[str, Any]) -> None:
        """Store the active parsed resume in memory indexed by session/user key."""
        if key and resume_data:
            self._active_resumes[str(key)] = dict(resume_data)

    def get_active_resume(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve the active parsed resume for a session/user key."""
        if not key:
            return None
        return self._active_resumes.get(str(key))

    def clear_active_resume(self, key: str) -> None:
        """Clear active resume for a session/user key."""
        if key:
            self._active_resumes.pop(str(key), None)

    def get_all_history(self, user_id: Optional[str] = None, public_only: bool = False) -> List[Dict[str, Any]]:
        """Return history records sorted by date descending from SQLite, optionally filtered by user_id or public_only."""
        try:
            models = AnalysisModel.get_all(user_id=user_id, public_only=public_only)
            if models:
                return [m.to_summary_dict() for m in models]
            return []
        except Exception:
            # Fallback to in-memory store if DB query fails
            if user_id:
                return [item for item in self._history_store if item.get("user_id") == user_id]
            if public_only:
                return [item for item in self._history_store if not item.get("user_id")]
            return list(self._history_store)

    def get_record(self, record_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find a summary record by ID from SQLite, verifying ownership if user_id is specified."""
        try:
            if user_id:
                model = AnalysisModel.get_by_id_and_user_id(record_id, user_id)
            else:
                model = AnalysisModel.get_by_id(record_id)
            if model:
                # If model is tied to a user but caller provided no user_id or mismatched user_id
                if model.user_id and user_id and model.user_id != user_id:
                    return None
                if model.user_id and not user_id:
                    return None
                return model.to_summary_dict()
        except Exception:
            pass

        # Fallback to in-memory store
        for item in self._history_store:
            if item.get("id") == record_id:
                if item.get("user_id") and user_id and item.get("user_id") != user_id:
                    return None
                if item.get("user_id") and not user_id:
                    return None
                return item
        return None

    def get_analysis_report(self, record_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve full report including parsed resume and JD details, enforcing user data privacy."""
        try:
            model = AnalysisModel.get_by_id(record_id)
            if model:
                # If the analysis belongs to a user, enforce ownership
                if model.user_id:
                    if not user_id or model.user_id != user_id:
                        return None
                return model.to_full_dict()
        except Exception:
            pass

        # Fallback to in-memory report store
        report = self._analysis_store.get(record_id)
        if report:
            rep_user = report.get("user_id")
            if rep_user and (not user_id or rep_user != user_id):
                return None
        return report

    def add_record(
        self,
        job_title: str,
        company: str,
        filename: str,
        scores: Dict[str, Any],
        full_analysis: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a new completed analysis along with its full report into SQLite.
        Associates evaluation with logged-in user_id when available.
        """
        now = datetime.now()
        overall = scores.get("overall_match", scores.get("overall_score", 75))
        status = "High Match" if overall >= 75 else ("Moderate Match" if overall >= 50 else "Needs Work")
        record_id = full_analysis.get("id") if full_analysis and "id" in full_analysis else f"analysis-{uuid.uuid4().hex[:8]}"

        summary_dict = {
            "id": record_id,
            "user_id": user_id,
            "job_title": job_title or "Target Role",
            "company": company or "Target Organization",
            "created_at": now.strftime("%b %d, %Y • %I:%M %p"),
            "date_iso": now.isoformat(),
            "overall_score": overall,
            "skills_score": scores.get("skills_match", scores.get("skills_score", 80)),
            "keyword_score": scores.get("keyword_coverage", scores.get("keyword_score", 75)),
            "education_score": scores.get("education_relevance", scores.get("education_score", 85)),
            "experience_score": scores.get("experience_relevance", scores.get("experience_score", 80)),
            "ats_score": scores.get("ats_compatibility", scores.get("ats_score", 85)),
            "status": status,
            "filename": filename or "Uploaded_Resume.pdf"
        }

        # Backup in-memory
        self._history_store.insert(0, summary_dict)
        if full_analysis:
            full_analysis["id"] = record_id
            full_analysis["user_id"] = user_id
            self._analysis_store[record_id] = full_analysis

        # Persist to SQLite
        try:
            matched_skills = full_analysis.get("matched_skills", []) if full_analysis else []
            missing_req = full_analysis.get("missing_required_skills", []) if full_analysis else []
            missing_pref = full_analysis.get("missing_preferred_skills", []) if full_analysis else []
            weak_matches = full_analysis.get("weak_matches", []) if full_analysis else []
            roadmap = (
                full_analysis.get("personalized_roadmap") or
                full_analysis.get("learning_roadmap", {})
            ) if full_analysis else {}
            improvement_sug = full_analysis.get("improvement_suggestions", []) if full_analysis else []
            ats_checklist = full_analysis.get("ats_checklist", []) if full_analysis else []

            model = AnalysisModel.create(
                analysis_id=record_id,
                user_id=user_id,
                job_title=job_title or "Target Role",
                company=company or "Target Organization",
                resume_filename=filename or "Uploaded_Resume.pdf",
                overall_score=overall,
                skills_score=scores.get("skills_match", scores.get("skills_score", 80)),
                keyword_score=scores.get("keyword_coverage", scores.get("keyword_score", 75)),
                education_score=scores.get("education_relevance", scores.get("education_score", 85)),
                experience_score=scores.get("experience_relevance", scores.get("experience_score", 80)),
                ats_score=scores.get("ats_compatibility", scores.get("ats_score", 85)),
                matched_skills=matched_skills,
                missing_required_skills=missing_req,
                missing_preferred_skills=missing_pref,
                weak_matches=weak_matches,
                roadmap=roadmap,
                improvement_suggestions=improvement_sug,
                ats_checklist=ats_checklist,
                full_analysis_json=full_analysis,
                created_at=summary_dict["created_at"],
                created_at_iso=summary_dict["date_iso"]
            )
            return model.to_summary_dict()
        except Exception:
            # Existing analysis still succeeds even if DB persistence fails
            return summary_dict

    def delete_record(self, record_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete an analysis record and its stored report from SQLite.
        Strictly enforces user privacy: an analysis owned by a user can only be deleted by that user.
        """
        # Check ownership first
        try:
            model = AnalysisModel.get_by_id(record_id)
            if model and model.user_id:
                if not user_id or model.user_id != user_id:
                    # Unauthorized deletion attempt
                    return False
        except Exception:
            pass

        deleted_from_db = False
        try:
            if user_id:
                deleted_from_db = AnalysisModel.delete_by_id_and_user_id(record_id, user_id)
            else:
                deleted_from_db = AnalysisModel.delete_by_id(record_id)
        except Exception:
            pass

        # Also purge from in-memory fallback
        initial_len = len(self._history_store)
        self._history_store = [item for item in self._history_store if item.get("id") != record_id]
        deleted_from_mem = len(self._history_store) < initial_len
        self._analysis_store.pop(record_id, None)

        return deleted_from_db or deleted_from_mem


# Global singleton
storage_service = StorageService()
