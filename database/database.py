"""
Database connection and lifecycle management for CareerLens AI (Stage 7).
Uses standard library sqlite3 for zero-dependency, reliable, persistent storage.
Supports connection pooling via Flask's application context (g) and standalone script execution.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from flask import g, current_app

# Default database location at project root
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "careerlens.db"


def get_db_path() -> str:
    """Resolve the active SQLite database path from Flask config or environment."""
    try:
        if current_app and current_app.config.get("DATABASE_PATH"):
            return str(current_app.config["DATABASE_PATH"])
    except RuntimeError:
        # Working outside of application context
        pass

    return os.environ.get("DATABASE_PATH", str(DEFAULT_DB_PATH))


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Open or reuse a database connection.
    If called within a Flask application context, the connection is cached on `flask.g`.
    Rows are configured to use sqlite3.Row for dictionary-like column access.
    """
    resolved_path = db_path or get_db_path()

    # Inside Flask application context and using the default app db path
    try:
        if current_app and not db_path:
            if "db" not in g:
                conn = sqlite3.connect(resolved_path, timeout=10.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                g.db = conn
            return g.db
    except RuntimeError:
        pass

    # Outside application context or explicit custom db_path
    conn = sqlite3.connect(resolved_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def close_connection(conn: Optional[sqlite3.Connection]) -> None:
    """Close connection if it is not the active request-scoped g.db."""
    if conn is None:
        return
    try:
        if current_app and "db" in g and g.db is conn:
            return
    except RuntimeError:
        pass
    try:
        conn.close()
    except Exception:
        pass


def close_db(e=None):
    """Close the database connection at the end of the Flask request lifecycle."""
    try:
        db = g.pop("db", None)
        if db is not None:
            db.close()
    except RuntimeError:
        pass


def init_db(db_path: Optional[str] = None, seed_samples: bool = False) -> None:
    """
    Initialize SQLite database tables and indices.
    Ensures parameterized table creation safe for production deployment.
    """
    resolved_path = db_path or get_db_path()

    # Ensure parent directory exists
    if resolved_path != ":memory:":
        parent_dir = Path(resolved_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(resolved_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        cursor = conn.cursor()

        # 1. Create users table (Stage 8)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_at_iso TEXT NOT NULL
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """)

        # 2. Create analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                job_title TEXT NOT NULL,
                company TEXT,
                resume_filename TEXT NOT NULL,
                overall_score INTEGER NOT NULL,
                skills_score INTEGER NOT NULL,
                keyword_score INTEGER NOT NULL,
                education_score INTEGER NOT NULL,
                experience_score INTEGER NOT NULL,
                ats_score INTEGER NOT NULL,
                matched_skills TEXT,
                missing_required_skills TEXT,
                missing_preferred_skills TEXT,
                weak_matches TEXT,
                roadmap TEXT,
                improvement_suggestions TEXT,
                ats_checklist TEXT,
                full_analysis_json TEXT,
                created_at TEXT NOT NULL,
                created_at_iso TEXT NOT NULL
            );
        """)

        # Ensure user_id column exists if table was already created in earlier stages
        cursor.execute("PRAGMA table_info(analyses);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "user_id" not in columns:
            cursor.execute("ALTER TABLE analyses ADD COLUMN user_id TEXT;")

        # Indices for high-performance sorting and lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyses_created_at_iso ON analyses(created_at_iso DESC);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyses_job_title ON analyses(job_title);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
        """)

        conn.commit()

        if seed_samples:
            from database.models import AnalysisModel
            if AnalysisModel.count(db_path=resolved_path) == 0:
                from app.services.sample_data import get_sample_history, get_sample_analysis
                sample_items = get_sample_history()
                for s in sample_items:
                    sample_full = get_sample_analysis(job_title=s["job_title"], company=s["company"])
                    sample_full["id"] = s["id"]
                    AnalysisModel.create(
                        analysis_id=s["id"],
                        job_title=s["job_title"],
                        company=s["company"],
                        resume_filename=s.get("filename", "Alex_Morgan_Resume_2026.pdf"),
                        overall_score=s.get("overall_score", 80),
                        skills_score=s.get("skills_score", 85),
                        keyword_score=75,
                        education_score=90,
                        experience_score=85,
                        ats_score=s.get("ats_score", 88),
                        matched_skills=sample_full.get("matched_skills", []),
                        missing_required_skills=sample_full.get("missing_skills", [])[:2],
                        missing_preferred_skills=sample_full.get("missing_skills", [])[2:],
                        roadmap=sample_full.get("personalized_roadmap", {}),
                        full_analysis_json=sample_full,
                        created_at=s.get("created_at"),
                        created_at_iso=s.get("date_iso"),
                        db_path=resolved_path
                    )
    finally:
        conn.close()
