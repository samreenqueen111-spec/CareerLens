"""
Test suite validating dynamic resume re-analysis with changing Job Descriptions (Stage 10 fix).
Verifies that changing Job Title, Company, or Job Description:
- Produces a brand new analysis record with unique ID
- Recalculates match scores, matched skills, missing skills, and roadmap
- Never reuses stale or cached analysis data
- Generates updated PDF reports reflecting the specific job data
"""

import io
import os
import tempfile
from pathlib import Path
import unittest
import pypdf

from app import create_app
from config import TestingConfig
from database.database import init_db
from database.models import AnalysisModel
from app.services.storage_service import storage_service

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class DynamicAnalysisTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")

        class CustomTestingConfig(TestingConfig):
            DATABASE_PATH = self.temp_db_path
            SECRET_KEY = "test-secret-key-dynamic-analysis"

        self.app = create_app(CustomTestingConfig)
        self.client = self.app.test_client()

        with open(SAMPLES_DIR / "sample_resume.pdf", "rb") as f:
            self.resume_bytes = f.read()

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

    def test_changing_job_data_produces_completely_new_analysis(self):
        """
        Verify that changing Job Title, Company, and Job Description
        produces completely different, freshly calculated analyses and PDFs.
        """
        # -------------------------------------------------------------
        # JOB 1: Python Full Stack Engineer at DataFlow Systems
        # -------------------------------------------------------------
        jd1_title = "Senior Python Full Stack Engineer"
        jd1_company = "DataFlow Systems"
        jd1_text = (
            "We are seeking an experienced Senior Python Full Stack Engineer. "
            "You must be proficient in Python, Django, React, TypeScript, Docker, "
            "PostgreSQL, and Redis. Responsible for architecting scalable cloud services."
        )

        resp1 = self.client.post("/api/analyze", data={
            "resume": (io.BytesIO(self.resume_bytes), "sample_resume.pdf"),
            "job_title": jd1_title,
            "company": jd1_company,
            "job_description": jd1_text
        }, content_type="multipart/form-data")

        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.get_json()
        self.assertTrue(data1["success"])
        analysis_id_1 = data1["analysis_id"]
        res_data_1 = data1["data"]

        # Check Job 1 metadata and scores
        self.assertEqual(res_data_1["job_title"], jd1_title)
        self.assertEqual(res_data_1["company"], jd1_company)
        scores_1 = res_data_1["scores"]
        matched_1 = [s["name"] for s in res_data_1["matched_skills"]]

        self.assertGreaterEqual(scores_1["overall_match"], 80)
        self.assertGreaterEqual(scores_1["skills_match"], 85)
        self.assertIn("Python", matched_1)
        self.assertIn("Docker", matched_1)
        self.assertIn("PostgreSQL", matched_1)

        # -------------------------------------------------------------
        # Verify /api/active-resume remembers resume in session
        # -------------------------------------------------------------
        active_resp = self.client.get("/api/active-resume")
        self.assertEqual(active_resp.status_code, 200)
        active_data = active_resp.get_json()
        self.assertTrue(active_data["has_resume"])
        self.assertEqual(active_data["filename"], "sample_resume.pdf")

        # -------------------------------------------------------------
        # JOB 2: Senior iOS Mobile Developer at AppCraft Studios
        # Notice: Resume file is NOT re-sent! Testing active session resume.
        # -------------------------------------------------------------
        jd2_title = "Senior iOS Mobile Developer"
        jd2_company = "AppCraft Studios"
        jd2_text = (
            "We are hiring a Senior iOS Mobile Developer to build high-performance mobile applications. "
            "Requirements include mastery in Swift, SwiftUI, Objective-C, Xcode, CoreData, "
            "and Apple TestFlight deployments."
        )

        resp2 = self.client.post("/api/analyze", data={
            "job_title": jd2_title,
            "company": jd2_company,
            "job_description": jd2_text
        }, content_type="multipart/form-data")

        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertTrue(data2["success"])
        analysis_id_2 = data2["analysis_id"]
        res_data_2 = data2["data"]

        # Check Job 2 metadata and scores
        self.assertNotEqual(analysis_id_1, analysis_id_2, "Every analysis must have a distinct ID")
        self.assertEqual(res_data_2["job_title"], jd2_title)
        self.assertEqual(res_data_2["company"], jd2_company)
        scores_2 = res_data_2["scores"]
        matched_2 = [s["name"] for s in res_data_2["matched_skills"]]
        missing_2 = [s["name"] for s in res_data_2["missing_required_skills"]]

        # Job 2 scores must reflect iOS requirements, NOT Python/Fullstack
        self.assertLess(scores_2["overall_match"], 60, "iOS role should have significantly lower match")
        self.assertLess(scores_2["skills_match"], 30, "iOS skills match should be low")
        self.assertNotIn("Python", matched_2, "Job 2 matched skills must not contain Python")
        self.assertIn("Swift", missing_2, "Job 2 missing required skills must contain Swift")

        # Roadmaps must differ
        roadmap_1 = res_data_1["personalized_roadmap"]
        roadmap_2 = res_data_2["personalized_roadmap"]
        self.assertNotEqual(
            roadmap_1["recommended_next_step"]["headline"],
            roadmap_2["recommended_next_step"]["headline"],
            "Roadmaps must be tailored to the new job description"
        )
        self.assertIn("Swift", roadmap_2["recommended_next_step"]["headline"])

        # -------------------------------------------------------------
        # Verify Dashboard View for both distinct analyses
        # -------------------------------------------------------------
        dash_resp_1 = self.client.get(f"/dashboard?id={analysis_id_1}")
        self.assertEqual(dash_resp_1.status_code, 200)
        dash_html_1 = dash_resp_1.get_data(as_text=True)
        self.assertIn(jd1_title, dash_html_1)
        self.assertIn(jd1_company, dash_html_1)
        self.assertIn(f"{scores_1['overall_match']}%", dash_html_1)
        self.assertEqual(dash_resp_1.headers.get("Cache-Control"), "no-cache, no-store, must-revalidate, max-age=0")

        dash_resp_2 = self.client.get(f"/dashboard?id={analysis_id_2}")
        self.assertEqual(dash_resp_2.status_code, 200)
        dash_html_2 = dash_resp_2.get_data(as_text=True)
        self.assertIn(jd2_title, dash_html_2)
        self.assertIn(jd2_company, dash_html_2)
        self.assertIn(f"{scores_2['overall_match']}%", dash_html_2)
        self.assertIn("Swift", dash_html_2)

        # -------------------------------------------------------------
        # Verify Downloaded PDFs contain the NEW and DISTINCT analysis data
        # -------------------------------------------------------------
        pdf_resp_1 = self.client.get(f"/dashboard/report/{analysis_id_1}")
        self.assertEqual(pdf_resp_1.status_code, 200)
        self.assertEqual(pdf_resp_1.mimetype, "application/pdf")
        reader1 = pypdf.PdfReader(io.BytesIO(pdf_resp_1.data))
        text1 = "\n".join([page.extract_text() or "" for page in reader1.pages])
        self.assertIn(jd1_title, text1)
        self.assertIn(jd1_company, text1)
        self.assertIn(f"{scores_1['overall_match']}%", text1)

        pdf_resp_2 = self.client.get(f"/dashboard/report/{analysis_id_2}")
        self.assertEqual(pdf_resp_2.status_code, 200)
        self.assertEqual(pdf_resp_2.mimetype, "application/pdf")
        reader2 = pypdf.PdfReader(io.BytesIO(pdf_resp_2.data))
        text2 = "\n".join([page.extract_text() or "" for page in reader2.pages])
        self.assertIn(jd2_title, text2)
        self.assertIn(jd2_company, text2)
        self.assertIn(f"{scores_2['overall_match']}%", text2)
        self.assertIn("Swift", text2)

    def test_analyzing_third_devops_role(self):
        """Verify analyzing a third completely different DevOps role recalculates properly."""
        # Prime session with resume
        self.client.post("/api/analyze", data={
            "resume": (io.BytesIO(self.resume_bytes), "sample_resume.pdf"),
            "job_title": "Full Stack Dev",
            "company": "Company A",
            "job_description": "We need a full stack developer with Python, React, and SQL experience."
        }, content_type="multipart/form-data")

        # Now analyze DevOps role
        devops_title = "Cloud Infrastructure & DevOps Engineer"
        devops_company = "Nordic Data Grid"
        devops_text = (
            "We are hiring a Cloud Infrastructure and DevOps Engineer. "
            "Must have experience with Terraform, Kubernetes, AWS cloud infrastructure, "
            "Prometheus observability, Docker containers, and CI/CD pipelines."
        )

        resp = self.client.post("/api/analyze", data={
            "job_title": devops_title,
            "company": devops_company,
            "job_description": devops_text
        }, content_type="multipart/form-data")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        analysis_id = data["analysis_id"]
        res_data = data["data"]

        self.assertEqual(res_data["job_title"], devops_title)
        self.assertEqual(res_data["company"], devops_company)
        matched_skills = [s["name"] for s in res_data["matched_skills"]]
        self.assertIn("Docker", matched_skills)
        self.assertIn("Kubernetes", matched_skills)

        # Download report
        pdf_resp = self.client.get(f"/dashboard/report/{analysis_id}")
        self.assertEqual(pdf_resp.status_code, 200)
        reader = pypdf.PdfReader(io.BytesIO(pdf_resp.data))
        text = "\n".join([p.extract_text() or "" for p in reader.pages])
        self.assertIn(devops_title, text)
        self.assertIn(devops_company, text)

    def test_clear_active_resume_endpoint(self):
        """Verify DELETE /api/active-resume removes resume from session."""
        self.client.post("/api/parse-resume", data={
            "resume": (io.BytesIO(self.resume_bytes), "sample_resume.pdf")
        }, content_type="multipart/form-data")

        status_before = self.client.get("/api/active-resume").get_json()
        self.assertTrue(status_before["has_resume"])

        del_resp = self.client.delete("/api/active-resume")
        self.assertEqual(del_resp.status_code, 200)

        status_after = self.client.get("/api/active-resume").get_json()
        self.assertFalse(status_after["has_resume"])


if __name__ == "__main__":
    unittest.main()
