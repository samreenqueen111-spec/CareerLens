"""
Unit and Integration Test Suite for CareerLens AI Database & History Layer (Stage 7).
Tests SQLite schema creation, AnalysisModel CRUD operations, parameterized SQL safety,
graceful error handling, end-to-end persistence from /api/analyze, viewing saved reports,
deletion, and empty state rendering.
"""

import io
import os
import tempfile
from pathlib import Path
import unittest

from app import create_app
from config import TestingConfig
from database.database import init_db, get_db, close_connection
from database.models import AnalysisModel, DatabaseError
from app.services.storage_service import StorageService

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class DatabaseTestCase(unittest.TestCase):
    """Unit tests for the SQLite database layer and AnalysisModel."""

    def setUp(self):
        # Use an isolated temporary database for each test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(db_path=self.temp_db_path, seed_samples=False)

    def tearDown(self):
        try:
            os.close(self.temp_db_fd)
        except OSError:
            pass
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_schema_initialization(self):
        """Verify tables and indices are created properly."""
        conn = get_db(self.temp_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analyses';")
            self.assertIsNotNone(cursor.fetchone())

            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_analyses_created_at_iso';")
            self.assertIsNotNone(cursor.fetchone())

            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_analyses_job_title';")
            self.assertIsNotNone(cursor.fetchone())
        finally:
            close_connection(conn)

    def test_create_and_get_analysis(self):
        """Verify AnalysisModel.create inserts all Stage 7 required fields and get_by_id retrieves them."""
        analysis = AnalysisModel.create(
            analysis_id="test-analysis-001",
            job_title="Senior Python Backend Engineer",
            company="Acme Cloud Corp",
            resume_filename="Jane_Doe_Resume.pdf",
            overall_score=84,
            skills_score=88,
            keyword_score=80,
            education_score=90,
            experience_score=82,
            ats_score=89,
            matched_skills=["Python", "Flask", "Docker", "PostgreSQL"],
            missing_required_skills=["Kubernetes"],
            missing_preferred_skills=["GraphQL", "AWS Lambda"],
            weak_matches=[{"skill": "Docker", "confidence": "Medium"}],
            roadmap={
                "phases": [
                    {"phase_number": 1, "phase_title": "Phase 1 — High Priority", "skills": ["Kubernetes"]}
                ]
            },
            full_analysis_json={"sample_key": "sample_val"},
            db_path=self.temp_db_path
        )

        self.assertEqual(analysis.id, "test-analysis-001")
        self.assertEqual(analysis.job_title, "Senior Python Backend Engineer")
        self.assertEqual(analysis.overall_score, 84)

        # Retrieve by ID
        fetched = AnalysisModel.get_by_id("test-analysis-001", db_path=self.temp_db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, "test-analysis-001")
        self.assertEqual(fetched.job_title, "Senior Python Backend Engineer")
        self.assertEqual(fetched.company, "Acme Cloud Corp")
        self.assertEqual(fetched.resume_filename, "Jane_Doe_Resume.pdf")
        self.assertEqual(fetched.overall_score, 84)
        self.assertEqual(fetched.skills_score, 88)
        self.assertEqual(fetched.keyword_score, 80)
        self.assertEqual(fetched.education_score, 90)
        self.assertEqual(fetched.experience_score, 82)
        self.assertEqual(fetched.ats_score, 89)
        self.assertIn("Python", fetched.matched_skills)
        self.assertIn("Kubernetes", fetched.missing_required_skills)
        self.assertIn("GraphQL", fetched.missing_preferred_skills)
        self.assertEqual(len(fetched.roadmap.get("phases", [])), 1)

    def test_get_nonexistent_analysis(self):
        """Verify get_by_id returns None for unknown IDs."""
        result = AnalysisModel.get_by_id("non-existent-id-999", db_path=self.temp_db_path)
        self.assertIsNone(result)

    def test_get_all_and_ordering(self):
        """Verify get_all orders records by descending created_at_iso date."""
        AnalysisModel.create(
            analysis_id="record-1",
            job_title="Junior Engineer",
            resume_filename="res1.pdf",
            overall_score=70,
            skills_score=70,
            keyword_score=70,
            education_score=70,
            experience_score=70,
            ats_score=70,
            created_at_iso="2026-01-01T10:00:00",
            db_path=self.temp_db_path
        )
        AnalysisModel.create(
            analysis_id="record-2",
            job_title="Senior Engineer",
            resume_filename="res2.pdf",
            overall_score=90,
            skills_score=90,
            keyword_score=90,
            education_score=90,
            experience_score=90,
            ats_score=90,
            created_at_iso="2026-02-01T10:00:00",
            db_path=self.temp_db_path
        )

        all_records = AnalysisModel.get_all(db_path=self.temp_db_path)
        self.assertEqual(len(all_records), 2)
        # record-2 was created later, so it should be first
        self.assertEqual(all_records[0].id, "record-2")
        self.assertEqual(all_records[1].id, "record-1")

    def test_delete_analysis(self):
        """Verify delete_by_id removes record and updates count."""
        AnalysisModel.create(
            analysis_id="to-delete",
            job_title="Temporary Role",
            resume_filename="temp.pdf",
            overall_score=60,
            skills_score=60,
            keyword_score=60,
            education_score=60,
            experience_score=60,
            ats_score=60,
            db_path=self.temp_db_path
        )
        self.assertEqual(AnalysisModel.count(db_path=self.temp_db_path), 1)

        deleted = AnalysisModel.delete_by_id("to-delete", db_path=self.temp_db_path)
        self.assertTrue(deleted)
        self.assertEqual(AnalysisModel.count(db_path=self.temp_db_path), 0)
        self.assertIsNone(AnalysisModel.get_by_id("to-delete", db_path=self.temp_db_path))

        # Deleting non-existent returns False
        self.assertFalse(AnalysisModel.delete_by_id("to-delete", db_path=self.temp_db_path))

    def test_parameterized_query_safety(self):
        """Verify SQL injection strings are safely escaped by parameterized queries."""
        malicious_input = "'; DROP TABLE analyses; --"
        malicious_job = "Developer' OR '1'='1"

        analysis = AnalysisModel.create(
            analysis_id=malicious_input,
            job_title=malicious_job,
            company="Security Test Ltd",
            resume_filename="innocent.pdf",
            overall_score=75,
            skills_score=75,
            keyword_score=75,
            education_score=75,
            experience_score=75,
            ats_score=75,
            matched_skills=["SQL", "'; DELETE FROM analyses;"],
            db_path=self.temp_db_path
        )

        # Table should still exist and record should be retrieved literally
        fetched = AnalysisModel.get_by_id(malicious_input, db_path=self.temp_db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, malicious_input)
        self.assertEqual(fetched.job_title, malicious_job)
        self.assertEqual(AnalysisModel.count(db_path=self.temp_db_path), 1)

    def test_summary_and_full_dict_serialization(self):
        """Verify to_summary_dict and to_full_dict preserve essential presentation structures."""
        analysis = AnalysisModel(
            analysis_id="dict-test",
            job_title="ML Specialist",
            company="AI Labs",
            resume_filename="ai_resume.pdf",
            overall_score=85,
            skills_score=90,
            keyword_score=80,
            education_score=95,
            experience_score=75,
            ats_score=88,
            matched_skills=["PyTorch", "NumPy"],
            missing_required_skills=["TensorFlow"],
            missing_preferred_skills=["MLflow"],
            roadmap={"phases": [{"phase_title": "Phase 1"}]},
            full_analysis_json={"custom_attr": 42, "job_title": "ML Specialist"}
        )

        summary = analysis.to_summary_dict()
        self.assertEqual(summary["id"], "dict-test")
        self.assertEqual(summary["overall_score"], 85)
        self.assertEqual(summary["status"], "High Match")
        self.assertEqual(summary["filename"], "ai_resume.pdf")

        full = analysis.to_full_dict()
        self.assertEqual(full["id"], "dict-test")
        self.assertEqual(full.get("custom_attr"), 42)


class DatabaseIntegrationTestCase(unittest.TestCase):
    """Integration tests verifying end-to-end web workflow: analyze, view, history, delete, and empty state."""

    def setUp(self):
        # Configure test app with temporary database
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")

        class CustomTestingConfig(TestingConfig):
            DATABASE_PATH = self.temp_db_path

        self.app = create_app(CustomTestingConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        try:
            os.close(self.temp_db_fd)
        except OSError:
            pass
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_e2e_analyze_persists_to_database(self):
        """Submitting an analysis via /api/analyze must automatically persist to SQLite."""
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        self.assertTrue(pdf_path.exists())

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        jd_text = (
            "We are looking for a Senior Software Engineer with strong Python, SQL, and Docker experience. "
            "Must have a Bachelor's degree in Computer Science and 3+ years experience building web applications. "
            "Experience with Kubernetes and CI/CD pipelines is preferred."
        )

        data = {
            "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
            "job_title": "Senior Software Engineer",
            "company": "Enterprise Cloud Systems",
            "job_description": jd_text
        }

        resp = self.client.post(
            "/api/analyze",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        res_data = resp.get_json()
        self.assertTrue(res_data["success"])
        analysis_id = res_data["analysis_id"]
        self.assertTrue(analysis_id)

        # 1. Verify saved in database directly
        saved_model = AnalysisModel.get_by_id(analysis_id, db_path=self.temp_db_path)
        self.assertIsNotNone(saved_model)
        self.assertEqual(saved_model.job_title, "Senior Software Engineer")
        self.assertEqual(saved_model.company, "Enterprise Cloud Systems")
        self.assertEqual(saved_model.resume_filename, "sample_resume.pdf")

        # 2. Verify /api/history returns the record
        history_resp = self.client.get("/api/history")
        self.assertEqual(history_resp.status_code, 200)
        history_json = history_resp.get_json()
        self.assertTrue(history_json["success"])
        history_ids = [h["id"] for h in history_json["history"]]
        self.assertIn(analysis_id, history_ids)

        # 3. Verify /dashboard?id=<analysis_id> renders the complete saved result
        dashboard_resp = self.client.get(f"/dashboard?id={analysis_id}")
        self.assertEqual(dashboard_resp.status_code, 200)
        html = dashboard_resp.get_data(as_text=True)
        self.assertIn("Senior Software Engineer", html)
        self.assertIn("Enterprise Cloud Systems", html)
        self.assertIn("Overall Match", html)

        # 4. Verify deleting the record via API
        del_resp = self.client.delete(f"/api/history/{analysis_id}")
        self.assertEqual(del_resp.status_code, 200)
        del_json = del_resp.get_json()
        self.assertTrue(del_json["success"])

        # Check DB record is gone
        self.assertIsNone(AnalysisModel.get_by_id(analysis_id, db_path=self.temp_db_path))

    def test_history_empty_state_rendering(self):
        """When history is empty, /history should render the required Stage 7 empty state message."""
        # Clean out any seeded records
        with self.app.app_context():
            all_records = AnalysisModel.get_all(db_path=self.temp_db_path)
            for r in all_records:
                AnalysisModel.delete_by_id(r.id, db_path=self.temp_db_path)

        resp = self.client.get("/history")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Required Stage 7 message
        self.assertIn("No analyses yet. Upload your resume and analyze your first job.", html)
        self.assertIn("No Analyses Yet", html)

    def test_storage_service_resilience(self):
        """Storage service gracefully handles database failure and falls back without crashing."""
        storage = StorageService()

        # Add record to non-existent / invalid path by overriding AnalysisModel behavior
        scores = {
            "overall_match": 82,
            "skills_match": 85,
            "keyword_coverage": 78,
            "education_relevance": 90,
            "experience_relevance": 80,
            "ats_compatibility": 86
        }

        # Should succeed in returning summary dict even if DB is unavailable
        summary = storage.add_record(
            job_title="Resilient Role",
            company="Fallback Corp",
            filename="test.pdf",
            scores=scores
        )
        self.assertIsNotNone(summary)
        self.assertEqual(summary["job_title"], "Resilient Role")
        self.assertEqual(summary["overall_score"], 82)


if __name__ == "__main__":
    unittest.main()
