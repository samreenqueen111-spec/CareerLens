"""
Database Models for CareerLens (Stage 7).
Implements the AnalysisModel entity storing complete evaluations, match scores,
skill gap breakdowns, ATS audit checklists, and career roadmaps in SQLite.

All operations use parameterized queries to ensure database safety.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import uuid
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from database.database import get_db, close_connection


class DatabaseError(Exception):
    """Custom exception raised for database persistence or query errors."""
    def __init__(self, message: str, code: str = "DATABASE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class UserModel:
    """
    User entity for CareerLens (Stage 8).
    Handles secure account creation, password verification via PBKDF2, and safe serialization.
    """

    def __init__(
        self,
        user_id: str,
        name: str,
        email: str,
        password_hash: str,
        created_at: Optional[str] = None,
        created_at_iso: Optional[str] = None
    ):
        self.id = user_id
        self.name = (name or "").strip()
        self.email = (email or "").strip().lower()
        self.password_hash = password_hash
        now = datetime.now()
        self.created_at = created_at or now.strftime("%b %d, %Y • %I:%M %p")
        self.created_at_iso = created_at_iso or now.isoformat()

    @classmethod
    def create(
        cls,
        name: str,
        email: str,
        password: str,
        user_id: Optional[str] = None,
        created_at: Optional[str] = None,
        created_at_iso: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> "UserModel":
        """
        Create a new user with securely hashed password and persist via parameterized query.
        """
        clean_email = (email or "").strip().lower()
        clean_name = (name or "").strip()
        if not clean_email or "@" not in clean_email:
            raise DatabaseError("A valid email address is required.", code="INVALID_EMAIL")
        if not password or len(password) < 6:
            raise DatabaseError("Password must be at least 6 characters long.", code="INVALID_PASSWORD")

        # Check existing user
        existing = cls.get_by_email(clean_email, db_path=db_path)
        if existing:
            raise DatabaseError("An account with this email already exists.", code="USER_EXISTS")

        pw_hash = generate_password_hash(password, method="pbkdf2:sha256")
        record_id = user_id or f"user-{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        formatted_date = created_at or now.strftime("%b %d, %Y • %I:%M %p")
        iso_date = created_at_iso or now.isoformat()

        user = cls(
            user_id=record_id,
            name=clean_name,
            email=clean_email,
            password_hash=pw_hash,
            created_at=formatted_date,
            created_at_iso=iso_date
        )

        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO users (id, name, email, password_hash, created_at, created_at_iso)
                VALUES (?, ?, ?, ?, ?, ?);
            """
            cursor.execute(query, (user.id, user.name, user.email, user.password_hash, user.created_at, user.created_at_iso))
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise DatabaseError("An account with this email already exists.", code="USER_EXISTS") from e
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Failed to create user account: {str(e)}") from e
        finally:
            close_connection(conn)

        return user

    @classmethod
    def get_by_id(cls, user_id: str, db_path: Optional[str] = None) -> Optional["UserModel"]:
        """Retrieve user by ID via parameterized query."""
        if not user_id:
            return None
        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._from_row(row)
        finally:
            close_connection(conn)

    @classmethod
    def get_by_email(cls, email: str, db_path: Optional[str] = None) -> Optional["UserModel"]:
        """Retrieve user by normalized email via parameterized query."""
        if not email:
            return None
        clean_email = email.strip().lower()
        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?;", (clean_email,))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._from_row(row)
        finally:
            close_connection(conn)

    def check_password(self, password: str) -> bool:
        """Verify candidate password against securely stored hash."""
        if not password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @classmethod
    def _from_row(cls, row: Any) -> "UserModel":
        return cls(
            user_id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
            created_at_iso=row["created_at_iso"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """Safe dictionary representation — strictly never exposes password_hash."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at
        }


class AnalysisModel:
    """
    Data model representing a completed resume-to-job analysis record.
    Stores multi-dimensional match scores, ATS audit metrics, categorized skill gaps,
    and personalized learning roadmaps with full JSON snapshot preservation.
    """

    def __init__(
        self,
        analysis_id: str,
        job_title: str,
        resume_filename: str,
        overall_score: int,
        skills_score: int,
        keyword_score: int,
        education_score: int,
        experience_score: int,
        ats_score: int,
        matched_skills: Any = None,
        missing_required_skills: Any = None,
        missing_preferred_skills: Any = None,
        roadmap: Any = None,
        company: Optional[str] = None,
        weak_matches: Any = None,
        improvement_suggestions: Any = None,
        ats_checklist: Any = None,
        full_analysis_json: Any = None,
        user_id: Optional[str] = None,
        created_at: Optional[str] = None,
        created_at_iso: Optional[str] = None
    ):
        self.id = analysis_id
        self.user_id = user_id
        self.job_title = job_title or "Target Role"
        self.company = company or "Target Organization"
        self.resume_filename = resume_filename or "Uploaded_Resume.pdf"
        self.overall_score = int(overall_score)
        self.skills_score = int(skills_score)
        self.keyword_score = int(keyword_score)
        self.education_score = int(education_score)
        self.experience_score = int(experience_score)
        self.ats_score = int(ats_score)

        # Deserialize or store structured fields
        self.matched_skills = self._ensure_deserialized(matched_skills, default=[])
        self.missing_required_skills = self._ensure_deserialized(missing_required_skills, default=[])
        self.missing_preferred_skills = self._ensure_deserialized(missing_preferred_skills, default=[])
        self.weak_matches = self._ensure_deserialized(weak_matches, default=[])
        self.roadmap = self._ensure_deserialized(roadmap, default={})
        self.improvement_suggestions = self._ensure_deserialized(improvement_suggestions, default=[])
        self.ats_checklist = self._ensure_deserialized(ats_checklist, default=[])
        self.full_analysis_json = self._ensure_deserialized(full_analysis_json, default={})

        now = datetime.now()
        self.created_at = created_at or now.strftime("%b %d, %Y • %I:%M %p")
        self.created_at_iso = created_at_iso or now.isoformat()

    @staticmethod
    def _ensure_deserialized(val: Any, default: Any = None) -> Any:
        """Safely parse JSON text into python objects if stored as string."""
        if val is None:
            return default if default is not None else []
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return default if default is not None else []
        return default

    @staticmethod
    def _ensure_serialized(val: Any) -> str:
        """Serialize python objects into JSON text for SQLite storage."""
        if val is None:
            return "{}"
        if isinstance(val, str):
            return val
        return json.dumps(val, ensure_ascii=False)

    @classmethod
    def create(
        cls,
        analysis_id: Optional[str],
        job_title: str,
        resume_filename: str,
        overall_score: int,
        skills_score: int,
        keyword_score: int,
        education_score: int,
        experience_score: int,
        ats_score: int,
        matched_skills: Any = None,
        missing_required_skills: Any = None,
        missing_preferred_skills: Any = None,
        roadmap: Any = None,
        company: Optional[str] = None,
        weak_matches: Any = None,
        improvement_suggestions: Any = None,
        ats_checklist: Any = None,
        full_analysis_json: Any = None,
        user_id: Optional[str] = None,
        created_at: Optional[str] = None,
        created_at_iso: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> "AnalysisModel":
        """
        Insert a new analysis record into the SQLite database using parameterized SQL.
        """
        record_id = analysis_id or f"analysis-{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        formatted_date = created_at or now.strftime("%b %d, %Y • %I:%M %p")
        iso_date = created_at_iso or now.isoformat()

        model = cls(
            analysis_id=record_id,
            job_title=job_title,
            company=company,
            resume_filename=resume_filename,
            overall_score=overall_score,
            skills_score=skills_score,
            keyword_score=keyword_score,
            education_score=education_score,
            experience_score=experience_score,
            ats_score=ats_score,
            matched_skills=matched_skills,
            missing_required_skills=missing_required_skills,
            missing_preferred_skills=missing_preferred_skills,
            weak_matches=weak_matches,
            roadmap=roadmap,
            improvement_suggestions=improvement_suggestions,
            ats_checklist=ats_checklist,
            full_analysis_json=full_analysis_json,
            user_id=user_id,
            created_at=formatted_date,
            created_at_iso=iso_date
        )

        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            query = """
                INSERT OR REPLACE INTO analyses (
                    id, user_id, job_title, company, resume_filename,
                    overall_score, skills_score, keyword_score, education_score,
                    experience_score, ats_score, matched_skills, missing_required_skills,
                    missing_preferred_skills, weak_matches, roadmap,
                    improvement_suggestions, ats_checklist, full_analysis_json,
                    created_at, created_at_iso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
            params = (
                model.id,
                model.user_id,
                model.job_title,
                model.company,
                model.resume_filename,
                model.overall_score,
                model.skills_score,
                model.keyword_score,
                model.education_score,
                model.experience_score,
                model.ats_score,
                cls._ensure_serialized(model.matched_skills),
                cls._ensure_serialized(model.missing_required_skills),
                cls._ensure_serialized(model.missing_preferred_skills),
                cls._ensure_serialized(model.weak_matches),
                cls._ensure_serialized(model.roadmap),
                cls._ensure_serialized(model.improvement_suggestions),
                cls._ensure_serialized(model.ats_checklist),
                cls._ensure_serialized(model.full_analysis_json),
                model.created_at,
                model.created_at_iso
            )
            cursor.execute(query, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Failed to persist analysis record {record_id}: {str(e)}") from e
        finally:
            close_connection(conn)

        return model

    @classmethod
    def get_by_id(cls, analysis_id: str, db_path: Optional[str] = None) -> Optional["AnalysisModel"]:
        """
        Query a single analysis record by its primary key ID using parameterized SQL.
        """
        if not analysis_id:
            return None

        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM analyses WHERE id = ?;"
            cursor.execute(query, (analysis_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._from_row(row)
        finally:
            close_connection(conn)

    @classmethod
    def get_by_id_and_user_id(
        cls,
        analysis_id: str,
        user_id: str,
        db_path: Optional[str] = None
    ) -> Optional["AnalysisModel"]:
        """
        Query an analysis record strictly verifying ownership by user_id using parameterized SQL.
        """
        if not analysis_id or not user_id:
            return None

        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM analyses WHERE id = ? AND user_id = ?;"
            cursor.execute(query, (analysis_id, user_id))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._from_row(row)
        finally:
            close_connection(conn)

    @classmethod
    def get_all(
        cls,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        public_only: bool = False,
        db_path: Optional[str] = None
    ) -> List["AnalysisModel"]:
        """
        Query analysis records ordered by descending date using parameterized SQL.
        Optionally filters strictly by user_id for authenticated users,
        or retrieves only public/unassigned records when public_only=True.
        """
        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            if user_id:
                query = "SELECT * FROM analyses WHERE user_id = ? ORDER BY created_at_iso DESC LIMIT ? OFFSET ?;"
                cursor.execute(query, (user_id, limit, offset))
            elif public_only:
                query = "SELECT * FROM analyses WHERE user_id IS NULL ORDER BY created_at_iso DESC LIMIT ? OFFSET ?;"
                cursor.execute(query, (limit, offset))
            else:
                query = "SELECT * FROM analyses ORDER BY created_at_iso DESC LIMIT ? OFFSET ?;"
                cursor.execute(query, (limit, offset))
            rows = cursor.fetchall()
            return [cls._from_row(row) for row in rows]
        finally:
            close_connection(conn)

    @classmethod
    def delete_by_id(cls, analysis_id: str, db_path: Optional[str] = None) -> bool:
        """
        Delete an analysis record by its primary key ID using parameterized SQL.
        Returns True if a row was deleted, False otherwise.
        """
        if not analysis_id:
            return False

        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            query = "DELETE FROM analyses WHERE id = ?;"
            cursor.execute(query, (analysis_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Failed to delete analysis record {analysis_id}: {str(e)}") from e
        finally:
            close_connection(conn)

    @classmethod
    def delete_by_id_and_user_id(
        cls,
        analysis_id: str,
        user_id: str,
        db_path: Optional[str] = None
    ) -> bool:
        """
        Delete an analysis record strictly verifying user ownership via parameterized SQL.
        """
        if not analysis_id or not user_id:
            return False

        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            query = "DELETE FROM analyses WHERE id = ? AND user_id = ?;"
            cursor.execute(query, (analysis_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Failed to delete analysis record {analysis_id}: {str(e)}") from e
        finally:
            close_connection(conn)

    @classmethod
    def count(cls, user_id: Optional[str] = None, db_path: Optional[str] = None) -> int:
        """Return the total count of stored analyses, optionally filtered by user_id."""
        conn = get_db(db_path)
        try:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("SELECT COUNT(*) FROM analyses WHERE user_id = ?;", (user_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM analyses;")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            close_connection(conn)

    @classmethod
    def _from_row(cls, row: Any) -> "AnalysisModel":
        """Instantiate an AnalysisModel from an sqlite3.Row instance."""
        user_id = row["user_id"] if "user_id" in row.keys() else None
        return cls(
            analysis_id=row["id"],
            user_id=user_id,
            job_title=row["job_title"],
            company=row["company"],
            resume_filename=row["resume_filename"],
            overall_score=row["overall_score"],
            skills_score=row["skills_score"],
            keyword_score=row["keyword_score"],
            education_score=row["education_score"],
            experience_score=row["experience_score"],
            ats_score=row["ats_score"],
            matched_skills=row["matched_skills"],
            missing_required_skills=row["missing_required_skills"],
            missing_preferred_skills=row["missing_preferred_skills"],
            weak_matches=row["weak_matches"],
            roadmap=row["roadmap"],
            improvement_suggestions=row["improvement_suggestions"],
            ats_checklist=row["ats_checklist"],
            full_analysis_json=row["full_analysis_json"],
            created_at=row["created_at"],
            created_at_iso=row["created_at_iso"]
        )

    def to_summary_dict(self) -> Dict[str, Any]:
        """
        Convert to a summary dictionary for history list displays,
        API history arrays, and cards.
        """
        overall = self.overall_score
        status = "High Match" if overall >= 75 else ("Moderate Match" if overall >= 50 else "Needs Work")

        return {
            "id": self.id,
            "user_id": self.user_id,
            "job_title": self.job_title,
            "company": self.company,
            "filename": self.resume_filename,
            "overall_score": self.overall_score,
            "skills_score": self.skills_score,
            "keyword_score": self.keyword_score,
            "education_score": self.education_score,
            "experience_score": self.experience_score,
            "ats_score": self.ats_score,
            "status": status,
            "created_at": self.created_at,
            "date_iso": self.created_at_iso
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """
        Convert to full report dictionary for Results Dashboard view (/dashboard?id=...).
        Restores full analysis snapshot when available, enriched with DB fields.
        """
        if self.full_analysis_json and isinstance(self.full_analysis_json, dict) and bool(self.full_analysis_json):
            full = dict(self.full_analysis_json)
            full["id"] = self.id
            full["user_id"] = self.user_id
            full["job_title"] = self.job_title
            full["company"] = self.company
            full["resume_filename"] = self.resume_filename
            return full

        # Synthesize fallback full structure
        return {
            "id": self.id,
            "user_id": self.user_id,
            "job_title": self.job_title,
            "company": self.company,
            "resume_filename": self.resume_filename,
            "analyzed_at": self.created_at,
            "is_preview": False,
            "scores": {
                "overall_match": self.overall_score,
                "skills_match": self.skills_score,
                "keyword_coverage": self.keyword_score,
                "education_relevance": self.education_score,
                "experience_relevance": self.experience_score,
                "ats_score": self.ats_score,
                "ats_compatibility": self.ats_score
            },
            "matched_skills": self.matched_skills,
            "missing_required_skills": self.missing_required_skills,
            "missing_preferred_skills": self.missing_preferred_skills,
            "missing_skills": self.missing_required_skills + self.missing_preferred_skills,
            "weak_matches": self.weak_matches,
            "personalized_roadmap": self.roadmap,
            "learning_roadmap": self.roadmap.get("phases", []) if isinstance(self.roadmap, dict) else [],
            "improvement_suggestions": self.improvement_suggestions,
            "ats_checklist": self.ats_checklist
        }
