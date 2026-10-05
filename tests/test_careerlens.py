"""
Integration test suite for CareerLens (Stage 1 & Stage 2).
Validates routes, API endpoints, error handling, templates,
real PDF and DOCX resume parsing, and section detection.
"""

import io
from pathlib import Path
import unittest
from app import create_app
from config import TestingConfig

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class CareerLensTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_health_check(self):
        """Verify /health returns 200 and expected metadata."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertGreaterEqual(data["stage"], 1)

    def test_landing_page(self):
        """Verify landing page loads correctly with key branding and CTAs."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("CareerLens", html)
        self.assertIn("Analyze My Resume", html)
        self.assertIn("Resume-to-JD Semantic Matching", html)
        self.assertIn("Skill Gap Analysis", html)
        self.assertIn("ATS-Style Verification", html)
        self.assertIn("Personalized Learning Roadmap", html)
        self.assertIn("How CareerLens Works", html)

    def test_analyzer_view(self):
        """Verify analyzer page renders upload dropzone and JD editor."""
        resp = self.client.get("/analyzer")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("resume-dropzone", html)
        self.assertIn("job_description", html)
        self.assertIn("PDF or DOCX", html)
        self.assertIn("Run Analysis", html)
        self.assertIn("parsed-resume-container", html)

    def test_dashboard_view(self):
        """Verify dashboard renders overall score, breakdown, and roadmap."""
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Overall Match", html)
        self.assertIn("Skills Match", html)
        self.assertIn("Experience Relevance", html)
        self.assertIn("Keyword Coverage", html)
        self.assertIn("ATS Compatibility", html)
        self.assertIn("Missing Skills", html)
        self.assertIn("Personalized Skill Gap Closure Roadmap", html)
        self.assertIn("Stage 1 Prototype Preview", html)

    def test_history_view(self):
        """Verify history page lists past analyses with search and delete UI."""
        resp = self.client.get("/history")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Analysis History", html)
        self.assertIn("history-card", html)
        self.assertIn("View Analysis", html)
        self.assertIn("delete-confirm-modal", html)

    def test_about_view(self):
        """Verify about and architecture page loads."""
        resp = self.client.get("/about")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("CareerLens Architecture", html)
        self.assertIn("Multi-Stage Product Roadmap", html)

    def test_sample_jd_endpoint(self):
        """Verify /api/sample-jd/<role> returns valid fixture data."""
        resp = self.client.get("/api/sample-jd/fullstack")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Senior Full Stack", data["data"]["title"])

    # =========================================================================
    # Stage 2: Real Resume Parsing Tests (PDF & DOCX)
    # =========================================================================

    def test_parse_resume_pdf_success(self):
        """Verify /api/parse-resume extracts text and sections from a real PDF file."""
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        self.assertTrue(pdf_path.exists(), "Sample PDF resume must exist")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        resp = self.client.post(
            "/api/parse-resume",
            data={"resume": (io.BytesIO(pdf_bytes), "alex_morgan.pdf")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["file_type"], "PDF Document")
        self.assertGreater(data["word_count"], 250)
        self.assertGreater(data["char_count"], 1500)
        self.assertIn("Alex Morgan", data["full_text"])
        self.assertIn("Skills", data["sections"])
        self.assertIn("Experience", data["sections"])
        self.assertIn("Education", data["sections"])
        self.assertIn("Projects", data["sections"])
        self.assertIn("alex.morgan@example.com", data["contact_details"]["emails"])

    def test_parse_resume_docx_success(self):
        """Verify /api/parse-resume extracts text and sections from a real DOCX file."""
        docx_path = SAMPLES_DIR / "sample_resume.docx"
        self.assertTrue(docx_path.exists(), "Sample DOCX resume must exist")

        with open(docx_path, "rb") as f:
            docx_bytes = f.read()

        resp = self.client.post(
            "/api/parse-resume",
            data={"resume": (io.BytesIO(docx_bytes), "alex_morgan.docx")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["file_type"], "Microsoft Word (DOCX)")
        self.assertGreater(data["word_count"], 250)
        self.assertIn("Alex Morgan", data["full_text"])
        self.assertIn("Skills", data["sections"])
        self.assertIn("Experience", data["sections"])
        self.assertIn("Education", data["sections"])
        self.assertIn("alex.morgan@example.com", data["contact_details"]["emails"])

    def test_parse_resume_empty_file_rejected(self):
        """Verify /api/parse-resume safely rejects an empty file (0 bytes)."""
        resp = self.client.post(
            "/api/parse-resume",
            data={"resume": (io.BytesIO(b""), "empty.pdf")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("empty (0 bytes)", data["error"])

    def test_parse_resume_corrupt_pdf_rejected(self):
        """Verify /api/parse-resume safely handles corrupted PDF files."""
        corrupt_data = io.BytesIO(b"This is not a real PDF structure at all.")
        resp = self.client.post(
            "/api/parse-resume",
            data={"resume": (corrupt_data, "bad.pdf")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("corrupted PDF", data["error"])

    def test_parse_resume_corrupt_docx_rejected(self):
        """Verify /api/parse-resume safely handles corrupted DOCX files."""
        corrupt_data = io.BytesIO(b"This is not a valid zip archive for Word.")
        resp = self.client.post(
            "/api/parse-resume",
            data={"resume": (corrupt_data, "bad.docx")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid DOCX", data["error"])

    def test_parse_resume_unsupported_file_rejected(self):
        """Verify /api/parse-resume safely rejects unsupported formats (e.g. .txt)."""
        text_data = io.BytesIO(b"Plain text resume")
        resp = self.client.post(
            "/api/parse-resume",
            data={"resume": (text_data, "resume.txt")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unsupported file format", data["error"])

    def test_analyze_flow_with_real_pdf_and_dashboard_display(self):
        """Verify complete pipeline: real PDF uploaded, parsed, and displayed on dashboard."""
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        resp = self.client.post(
            "/api/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
                "job_title": "Lead Python Engineer",
                "company": "Horizon Cloud",
                "job_description": "We are seeking a Lead Python Engineer with expertise in FastAPI, PostgreSQL, and Docker containerization."
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("parsed_resume", data["data"])
        self.assertEqual(data["data"]["parsed_resume"]["file_type"], "PDF Document")
        self.assertIn("alex.morgan@example.com", data["data"]["parsed_resume"]["contact_details"]["emails"])

        # Fetch dashboard view using returned analysis_id
        analysis_id = data["analysis_id"]
        dash_resp = self.client.get(f"/dashboard?id={analysis_id}&job_title=Lead+Python+Engineer")
        self.assertEqual(dash_resp.status_code, 200)
        dash_html = dash_resp.get_data(as_text=True)

        # Verify extracted text and sections are ACTUALLY displayed in the HTML
        self.assertIn("Parsed Resume Inspection", dash_html)
        self.assertIn("sample_resume.pdf", dash_html)
        self.assertIn("Alex Morgan", dash_html)
        self.assertIn("Extracted Text Preview", dash_html)

    def test_analyze_flow_with_real_docx_and_dashboard_display(self):
        """Verify complete pipeline: real DOCX uploaded, parsed, and displayed on dashboard."""
        docx_path = SAMPLES_DIR / "sample_resume.docx"
        with open(docx_path, "rb") as f:
            docx_bytes = f.read()

        resp = self.client.post(
            "/api/analyze",
            data={
                "resume": (io.BytesIO(docx_bytes), "sample_resume.docx"),
                "job_title": "Lead Full Stack Engineer",
                "company": "Horizon Cloud",
                "job_description": "We are seeking a Lead Full Stack Engineer with React, Python, and SQL experience."
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["parsed_resume"]["file_type"], "Microsoft Word (DOCX)")

        analysis_id = data["analysis_id"]
        dash_resp = self.client.get(f"/dashboard?id={analysis_id}&job_title=Lead+Full+Stack+Engineer")
        self.assertEqual(dash_resp.status_code, 200)
        dash_html = dash_resp.get_data(as_text=True)

        # Verify extracted text and sections are ACTUALLY displayed in the HTML
        self.assertIn("Parsed Resume Inspection", dash_html)
        self.assertIn("sample_resume.docx", dash_html)
        self.assertIn("Alex Morgan", dash_html)
        self.assertIn("Extracted Text Preview", dash_html)

    def test_api_analyze_missing_file(self):
        """Verify /api/analyze rejects requests missing a resume file."""
        resp = self.client.post("/api/analyze", data={
            "job_title": "Software Engineer",
            "job_description": "We need a Python and React engineer with 3+ years experience."
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("resume file", data["error"])

    def test_api_history_crud(self):
        """Verify retrieving history and deleting an item via API."""
        resp = self.client.get("/api/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["history"]), 0)

        record_id = data["history"][0]["id"]

        item_resp = self.client.get(f"/api/history/{record_id}")
        self.assertEqual(item_resp.status_code, 200)
        self.assertTrue(item_resp.get_json()["success"])

        del_resp = self.client.delete(f"/api/history/{record_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.get_json()["success"])

    def test_404_error_page(self):
        """Verify 404 handler returns HTML for browser and JSON for API."""
        html_resp = self.client.get("/non-existent-page")
        self.assertEqual(html_resp.status_code, 404)
        self.assertIn("Page or Resource Not Found", html_resp.get_data(as_text=True))

        json_resp = self.client.get("/api/non-existent-endpoint")
        self.assertEqual(json_resp.status_code, 404)
        data = json_resp.get_json()
        self.assertFalse(data["success"])


    # =========================================================================
    # Stage 3: Real Job Description Analysis Tests
    # =========================================================================

    def test_analyze_jd_endpoint_success(self):
        """Verify /api/analyze-jd extracts required skills, preferred skills, education, and experience."""
        jd_payload = {
            "job_title": "Full Stack Engineer",
            "job_description": """About the Role:
We are looking for a Full Stack Engineer to join our growing product team.

Responsibilities:
- Build and maintain responsive web frontends using modern React and TypeScript.
- Design backend microservices using Python, FastAPI, and PostgreSQL.
- Write unit and integration tests.

Requirements:
- 3+ years of software development experience in production web systems.
- Bachelor's degree in Computer Science or Software Engineering.
- Strong proficiency in Python, React, SQL, and Git.
- Excellent communication, problem solving, and agile collaboration skills.

Preferred Qualifications:
- Experience with Docker containerization and Kubernetes orchestration.
- Familiarity with Redis caching and GraphQL APIs."""
        }

        resp = self.client.post("/api/analyze-jd", json=jd_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["job_title"], "Full Stack Engineer")
        self.assertGreater(data["word_count"], 50)
        self.assertGreater(data["char_count"], 400)

        # 1. Required Technical Skills
        req_skills = data["required_skills"]
        self.assertIn("Python", req_skills)
        self.assertIn("React", req_skills)
        self.assertIn("SQL", req_skills)
        self.assertIn("Git", req_skills)

        # 2. Preferred Skills (separated from required)
        pref_skills = data["preferred_skills"]
        self.assertTrue(any(s in pref_skills for s in ["Docker", "Kubernetes", "GraphQL", "Redis"]))

        # 3. Soft Skills
        soft = data["soft_skills"]
        self.assertTrue(any(s in soft for s in ["Communication", "Problem Solving", "Agile"]))

        # 4. Education Requirements
        edu = data["education"]
        self.assertTrue(edu["is_specified"])
        self.assertTrue(any("Bachelor" in d for d in edu["degrees"]))
        self.assertTrue(any("Computer Science" in f for f in edu["fields_of_study"]))
        self.assertIn("Bachelor", edu["summary"])

        # 5. Experience Requirements
        exp = data["experience"]
        self.assertTrue(exp["is_specified"])
        self.assertEqual(exp["min_years"], 3)
        self.assertIn("3+", exp["summary"])

        # 6. Keywords
        kws = [k["keyword"].lower() for k in data["keywords"]]
        self.assertTrue(any(k in kws for k in ["software", "engineer", "web", "frontends", "react", "python"]))

    def test_analyze_jd_empty_text_rejected(self):
        """Verify /api/analyze-jd rejects empty text with 400 error."""
        resp = self.client.post("/api/analyze-jd", json={"job_description": "   "})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("empty", data["error"].lower())

    def test_analyze_jd_short_text_rejected(self):
        """Verify /api/analyze-jd rejects too-short text (<30 chars) with 400 error."""
        resp = self.client.post("/api/analyze-jd", json={"job_description": "Python dev needed"})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("short", data["error"].lower())

    def test_analyze_jd_form_encoded(self):
        """Verify /api/analyze-jd accepts standard form-urlencoded data."""
        resp = self.client.post(
            "/api/analyze-jd",
            data={
                "job_title": "Backend Developer",
                "job_description": "We require a skilled Backend Developer with 2-4 years experience in Java, Spring Boot, PostgreSQL, and AWS cloud infrastructure."
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Java", data["required_skills"])

    def test_full_pipeline_with_real_resume_and_real_jd_on_dashboard(self):
        """Verify end-to-end /api/analyze with real PDF resume and real JD produces real JD section in dashboard."""
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        jd_text = """About the Role:
We are hiring a Senior Python Engineer to lead our API backend architecture.

Requirements:
- 5+ years of software development experience in Python and Flask.
- Bachelor's degree in Computer Science or related STEM field.
- Strong knowledge of PostgreSQL, Redis, and RESTful API design.
- Excellent communication and leadership skills.

Preferred:
- Experience with Docker, Kubernetes, and AWS deployment pipelines."""

        resp = self.client.post(
            "/api/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
                "job_title": "Senior Python Engineer",
                "company": "Horizon Cloud",
                "job_description": jd_text
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("job_analysis", data["data"])
        self.assertIn("Python", data["data"]["job_analysis"]["required_skills"])
        self.assertIn("Docker", data["data"]["job_analysis"]["preferred_skills"])

        analysis_id = data["analysis_id"]
        dash_resp = self.client.get(f"/dashboard?id={analysis_id}&job_title=Senior+Python+Engineer")
        self.assertEqual(dash_resp.status_code, 200)
        dash_html = dash_resp.get_data(as_text=True)

        # Verify Stage 3 elements are rendered in HTML
        self.assertIn("Analyzed Job Description (Stage 3 Engine)", dash_html)
        self.assertIn("Required Technical Skills", dash_html)
        self.assertIn("Python", dash_html)
        self.assertIn("Preferred / Nice-to-Have Skills", dash_html)
        self.assertIn("Docker", dash_html)
        self.assertIn("Experience Requirement", dash_html)
        self.assertIn("Education Requirement", dash_html)
        self.assertIn("Stages 2 & 3 Live", dash_html)

    def test_api_analyze_with_invalid_short_jd_rejected(self):
        """Verify /api/analyze rejects valid resume when job description is missing or too short."""
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        resp = self.client.post(
            "/api/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
                "job_title": "Dev",
                "job_description": "Too short"
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("short", data["error"].lower())


if __name__ == "__main__":
    unittest.main()
