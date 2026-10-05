"""
Comprehensive Unit and Integration Test Suite for:
- Stage 8: User Authentication + Privacy + Security
- Stage 9: Professional Analysis Report (PDF Generation & Authorization)
"""

import io
import os
import tempfile
from pathlib import Path
import unittest
import pypdf

from app import create_app
from config import TestingConfig
from database.database import init_db, get_db, close_connection
from database.models import UserModel, AnalysisModel
from app.services.auth_service import AuthService
from services.report_generator import ReportGenerator, ReportGeneratorError

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class Stage8And9TestCase(unittest.TestCase):
    """Test suite covering Stage 8 Authentication, Privacy, and Stage 9 PDF Reporting."""

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")

        class CustomTestingConfig(TestingConfig):
            DATABASE_PATH = self.temp_db_path
            SECRET_KEY = "test-secret-key-stage8-and-9"

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

    # ==========================================================
    # STAGE 8 TESTS: AUTHENTICATION, PRIVACY, SECURITY
    # ==========================================================

    def test_signup_validation_and_creation(self):
        """Verify user registration validates email, password length, and uniqueness."""
        # 1. Invalid email
        user, err = AuthService.signup_user("Alice", "invalid-email", "password123", db_path=self.temp_db_path)
        self.assertIsNone(user)
        self.assertIn("valid email", err.lower())

        # 2. Short password (< 6 chars)
        user, err = AuthService.signup_user("Alice", "alice@example.com", "12345", db_path=self.temp_db_path)
        self.assertIsNone(user)
        self.assertIn("at least 6 characters", err.lower())

        # 3. Successful signup
        user, err = AuthService.signup_user("Alice", "alice@example.com", "password123", db_path=self.temp_db_path)
        self.assertIsNotNone(user)
        self.assertIsNone(err)
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(user.check_password("password123"))
        self.assertFalse(user.check_password("wrongpassword"))

        # Password hash must not be plain text
        self.assertNotEqual(user.password_hash, "password123")
        self.assertTrue(user.password_hash.startswith("pbkdf2:sha256"))

        # 4. Duplicate signup rejected
        user2, err2 = AuthService.signup_user("Alice Clone", "alice@example.com", "password123", db_path=self.temp_db_path)
        self.assertIsNone(user2)
        self.assertIn("already exists", err2.lower())

    def test_login_and_logout_flow(self):
        """Verify user login verifies password securely and logout terminates session."""
        with self.app.test_request_context():
            # Create user
            AuthService.signup_user("Bob", "bob@example.com", "securepass123", db_path=self.temp_db_path)

            # Wrong password
            user, err = AuthService.login_user("bob@example.com", "wrongpassword", db_path=self.temp_db_path)
            self.assertIsNone(user)
            self.assertIn("invalid email or password", err.lower())

            # Non-existent user
            user, err = AuthService.login_user("nobody@example.com", "securepass123", db_path=self.temp_db_path)
            self.assertIsNone(user)
            self.assertIn("invalid email or password", err.lower())

            # Correct login
            user, err = AuthService.login_user("bob@example.com", "securepass123", db_path=self.temp_db_path)
            self.assertIsNotNone(user)
            self.assertIsNone(err)

            # Current user resolved
            current = AuthService.get_current_user(db_path=self.temp_db_path)
            self.assertIsNotNone(current)
            self.assertEqual(current.email, "bob@example.com")

            # Logout
            AuthService.logout_user()
            self.assertIsNone(AuthService.get_current_user(db_path=self.temp_db_path))

    def test_user_ownership_and_data_privacy(self):
        """
        Verify end-to-end user isolation:
        - User 1 creates analysis -> saved with user 1 ID
        - User 1 can view and delete their analysis
        - User 2 cannot access or delete User 1's analysis (403 Forbidden)
        - Unauthenticated visitor cannot access personal analysis
        """
        # Register User 1 & User 2
        with self.app.app_context():
            user1 = UserModel.create("User One", "user1@example.com", "pass1234", db_path=self.temp_db_path)
            user2 = UserModel.create("User Two", "user2@example.com", "pass1234", db_path=self.temp_db_path)

        # 1. Login as User 1 via API
        resp = self.client.post("/api/auth/login", json={"email": "user1@example.com", "password": "pass1234"})
        self.assertEqual(resp.status_code, 200)

        # 2. User 1 submits an analysis
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        jd_text = (
            "We are seeking a Backend Python Engineer with Docker, SQL, and FastAPI experience. "
            "Must have a Bachelor's degree in Computer Science."
        )
        post_data = {
            "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
            "job_title": "Backend Python Engineer",
            "company": "SecureTech Ltd",
            "job_description": jd_text
        }
        analyze_resp = self.client.post("/api/analyze", data=post_data, content_type="multipart/form-data")
        self.assertEqual(analyze_resp.status_code, 200)
        u1_analysis_id = analyze_resp.get_json()["analysis_id"]

        # Check DB has user1_id attached
        saved = AnalysisModel.get_by_id(u1_analysis_id, db_path=self.temp_db_path)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.user_id, user1.id)

        # 3. User 1 can view in history and dashboard
        h_resp = self.client.get("/api/history")
        self.assertEqual(h_resp.status_code, 200)
        self.assertIn(u1_analysis_id, [x["id"] for x in h_resp.get_json()["history"]])

        d_resp = self.client.get(f"/dashboard?id={u1_analysis_id}")
        self.assertEqual(d_resp.status_code, 200)

        # 4. User 1 logs out
        self.client.post("/api/auth/logout")

        # 5. Unauthenticated visitor cannot view personal analysis
        unauth_dash = self.client.get(f"/dashboard?id={u1_analysis_id}")
        self.assertEqual(unauth_dash.status_code, 302)  # Redirects to login
        self.assertIn("/login", unauth_dash.location)

        unauth_del = self.client.delete(f"/api/history/{u1_analysis_id}")
        self.assertEqual(unauth_del.status_code, 401)  # Unauthorized

        # 6. Login as User 2
        self.client.post("/api/auth/login", json={"email": "user2@example.com", "password": "pass1234"})

        # User 2 history MUST NOT include User 1's analysis
        u2_history = self.client.get("/api/history")
        self.assertEqual(u2_history.status_code, 200)
        self.assertNotIn(u1_analysis_id, [x["id"] for x in u2_history.get_json()["history"]])

        # User 2 attempting to view User 1's dashboard -> 403 Forbidden
        u2_dash = self.client.get(f"/dashboard?id={u1_analysis_id}")
        self.assertEqual(u2_dash.status_code, 403)

        # User 2 attempting to delete User 1's analysis -> 403 Forbidden
        u2_del = self.client.delete(f"/api/history/{u1_analysis_id}")
        self.assertEqual(u2_del.status_code, 403)

        # User 1's record must still be intact in DB
        self.assertIsNotNone(AnalysisModel.get_by_id(u1_analysis_id, db_path=self.temp_db_path))

    # ==========================================================
    # STAGE 9 TESTS: PROFESSIONAL ANALYSIS REPORT (PDF GENERATION)
    # ==========================================================

    def test_report_generator_contains_all_14_sections(self):
        """Verify ReportGenerator compiles valid PDF containing all 14 required sections."""
        analysis_data = {
            "id": "analysis-test-stage9",
            "job_title": "Lead Cloud Infrastructure Engineer",
            "company": "Apex Distributed Networks",
            "analyzed_at": "October 04, 2026 • 11:30 PM",
            "resume_filename": "Jane_Cloud_Architect.pdf",
            "scores": {
                "overall_match": 86,
                "skills_match": 90,
                "keyword_coverage": 82,
                "education_relevance": 95,
                "experience_relevance": 85,
                "ats_score": 92
            },
            "matched_skills": ["Python", "Docker", "Kubernetes", "PostgreSQL", "Terraform", "CI/CD"],
            "missing_required_skills": [
                {
                    "name": "ArgoCD",
                    "priority": "High",
                    "why_it_matters": "Core GitOps continuous deployment engine required for cluster management.",
                    "learning_direction": "Deploy sample helm chart via ArgoCD application controller."
                }
            ],
            "missing_preferred_skills": [
                {
                    "name": "Prometheus",
                    "priority": "Medium",
                    "why_it_matters": "Preferred metrics collection and alerting stack."
                }
            ],
            "improvement_suggestions": [
                "Include quantifiable latency improvements on container deployment pipelines.",
                "Detail multi-region cluster failover testing in recent experience section."
            ],
            "personalized_roadmap": {
                "top_recommended_next_step": {
                    "skill_name": "ArgoCD",
                    "recommended_learning_level": "Intermediate",
                    "estimated_time_commitment": "8-12 hours",
                    "immediate_first_action": "Set up minikube and install ArgoCD operator."
                },
                "phases": [
                    {
                        "phase_number": 1,
                        "phase_title": "Phase 1 — Critical Requirements",
                        "skills": ["ArgoCD"]
                    },
                    {
                        "phase_number": 2,
                        "phase_title": "Phase 2 — Core Job Readiness",
                        "skills": ["Prometheus"]
                    }
                ]
            },
            "parsed_resume": {
                "word_count": 485,
                "char_count": 3120,
                "contact_details": {
                    "name": "Jane Doe",
                    "email": "jane.doe@example.com",
                    "phone": "+1 (555) 234-5678"
                },
                "sections": {
                    "summary": "Experienced Cloud Architect specializing in automated container delivery."
                }
            }
        }

        # Generate PDF
        pdf_bytes = ReportGenerator.generate_pdf(analysis_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 2000)

        # Parse and verify contents with pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        self.assertGreaterEqual(len(reader.pages), 1)

        extracted_text = "".join(page.extract_text() for page in reader.pages)

        # Verify all 14 required sections
        self.assertIn("Lead Cloud Infrastructure Engineer", extracted_text)  # Target Job Title
        self.assertIn("Jane Doe", extracted_text)  # Candidate / Resume summary
        self.assertIn("86%", extracted_text)  # Overall Match Score
        self.assertIn("90%", extracted_text)  # Skills Match Score
        self.assertIn("82%", extracted_text)  # Keyword Match Score
        self.assertIn("95%", extracted_text)  # Education Match
        self.assertIn("85%", extracted_text)  # Experience Match
        self.assertIn("92%", extracted_text)  # ATS Readiness Score
        self.assertIn("Matched Skills", extracted_text)  # Matched Skills section
        self.assertIn("Docker", extracted_text)  # Matched Skill item
        self.assertIn("Missing Required Skills", extracted_text)  # Missing Required Skills
        self.assertIn("ArgoCD", extracted_text)  # Missing Required item
        self.assertIn("Missing Preferred Skills", extracted_text)  # Missing Preferred Skills
        self.assertIn("Prometheus", extracted_text)  # Missing Preferred item
        self.assertIn("Resume Strengths", extracted_text)  # Resume Strengths
        self.assertIn("Improvement Recommendations", extracted_text)  # Improvement Suggestions
        self.assertIn("Personalized Career Learning Roadmap", extracted_text)  # Roadmap
        self.assertIn("Page", extracted_text)  # Page numbers

    def test_report_download_endpoint_and_authorization(self):
        """
        Verify PDF report download endpoint:
        - Owner can download PDF report (200, Content-Type: application/pdf)
        - Another user receives 403 Forbidden
        - Unauthenticated visitor receives 302 or 401
        """
        with self.app.app_context():
            u1 = UserModel.create("Dev One", "dev1@example.com", "password123", db_path=self.temp_db_path)
            u2 = UserModel.create("Dev Two", "dev2@example.com", "password123", db_path=self.temp_db_path)

        # Login as User 1
        self.client.post("/api/auth/login", json={"email": "dev1@example.com", "password": "password123"})

        # Submit analysis
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        data = {
            "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
            "job_title": "Full Stack Engineer",
            "company": "Tech Innovations",
            "job_description": "We need a Full Stack Engineer with Python, React, and SQL."
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        analysis_id = res.get_json()["analysis_id"]

        # 1. User 1 downloads report -> Success (200, PDF)
        dl_resp = self.client.get(f"/report/{analysis_id}/download")
        self.assertEqual(dl_resp.status_code, 200)
        self.assertEqual(dl_resp.content_type, "application/pdf")
        self.assertIn("attachment", dl_resp.headers.get("Content-Disposition", ""))
        self.assertGreater(len(dl_resp.data), 1000)

        # 2. User 1 logs out
        self.client.post("/api/auth/logout")

        # 3. Unauthenticated visitor downloading personal report -> Redirects to login
        unauth_resp = self.client.get(f"/report/{analysis_id}/download")
        self.assertEqual(unauth_resp.status_code, 302)

        # API endpoint returns 401
        api_unauth = self.client.get(f"/api/reports/{analysis_id}/download")
        self.assertEqual(api_unauth.status_code, 401)

        # 4. User 2 logs in and attempts download -> 403 Forbidden
        self.client.post("/api/auth/login", json={"email": "dev2@example.com", "password": "password123"})
        u2_dl = self.client.get(f"/report/{analysis_id}/download")
        self.assertEqual(u2_dl.status_code, 403)

        u2_api_dl = self.client.get(f"/api/reports/{analysis_id}/download")
        self.assertEqual(u2_api_dl.status_code, 403)


if __name__ == "__main__":
    unittest.main()
