"""
Unit and Integration Test Suite for Stage 4: Resume-to-Job Matching.
Tests scoring formulas, exact vs related skill matching, normalized synonyms,
missing required vs preferred skills, education & experience logic,
error handling, and end-to-end dashboard integration.
"""

import io
from pathlib import Path
import unittest
from app import create_app
from config import TestingConfig
from app.services.matcher import ResumeJobMatcher, MatcherError
from app.services.resume_parser import ResumeParser
from app.services.job_analyzer import JobAnalyzer

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class MatcherUnitTestCase(unittest.TestCase):
    """Direct unit tests for ResumeJobMatcher methods and formulas."""

    def test_canonical_skill_normalization(self):
        """Verify variations of skills are mapped to canonical names."""
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("Python"), "Python")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("python programming"), "Python")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("py"), "Python")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("JS"), "JavaScript")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("javascript"), "JavaScript")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("ts"), "TypeScript")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("ML"), "Machine Learning")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("machine learning"), "Machine Learning")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("Kubernetes (K8s)"), "Kubernetes")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("k8s"), "Kubernetes")
        self.assertEqual(ResumeJobMatcher.canonicalize_skill("JavaScript / JS"), "JavaScript")

    def test_exact_vs_related_skills_distinction(self):
        """Verify exact skills get 1.0 credit and related skills get 0.65 credit."""
        resume_data = {
            "full_text": "Experienced developer with Python, React, SQL, and Docker.",
            "section_contents": {
                "Skills": "Python, React, SQL, Docker",
                "Experience": "Built web applications in Python and React with SQL databases and Docker containers."
            }
        }

        # JD asks for Python (exact), PostgreSQL (related to SQL), and Rust (missing)
        jd_data = {
            "job_title": "Backend Engineer",
            "required_skills": ["Python", "PostgreSQL", "Rust"],
            "preferred_skills": [],
            "keywords": [{"keyword": "python", "count": 2}, {"keyword": "backend", "count": 1}],
            "education": {"is_specified": False},
            "experience": {"min_years": 2, "is_specified": True}
        }

        result = ResumeJobMatcher.match(resume_data, jd_data)
        self.assertTrue(result["success"])

        matched_dict = {m["name"]: m for m in result["matched_skills"]}

        # Python should be exact match (credit 1.0)
        self.assertIn("Python", matched_dict)
        self.assertEqual(matched_dict["Python"]["match_type"], "exact")
        self.assertEqual(matched_dict["Python"]["credit"], 1.0)

        # PostgreSQL should be related match via SQL (credit 0.65)
        self.assertIn("PostgreSQL", matched_dict)
        self.assertEqual(matched_dict["PostgreSQL"]["match_type"], "related")
        self.assertEqual(matched_dict["PostgreSQL"]["credit"], 0.65)
        self.assertIn("SQL", matched_dict["PostgreSQL"]["matched_via"])

        # Rust should be missing
        missing_names = [m["name"] for m in result["missing_required_skills"]]
        self.assertIn("Rust", missing_names)

        # Skills score = (1.0 + 0.65 + 0.0) / 3 * 100 = 55.0
        self.assertEqual(result["scores"]["skills_match"], 55)

    def test_required_vs_preferred_skills_separation(self):
        """Verify required and preferred skills are weighted and categorized separately."""
        resume_data = {
            "full_text": "Technical skills: Python, React, Node.js.",
            "section_contents": {"Skills": "Python, React, Node.js"}
        }

        jd_data = {
            "job_title": "Full Stack Engineer",
            "required_skills": ["Python", "React"],
            "preferred_skills": ["Docker", "GraphQL"],
            "keywords": [{"keyword": "web", "count": 1}],
            "education": {"is_specified": False},
            "experience": {"min_years": 1, "is_specified": False}
        }

        result = ResumeJobMatcher.match(resume_data, jd_data)

        # Candidate matches 100% of required (Python, React) and 0% of preferred
        # Skills score = 0.75 * 100 + 0.25 * 0 = 75%
        self.assertEqual(result["scores"]["skills_match"], 75)

        # Missing preferred should contain Docker and GraphQL, but missing required should be empty
        self.assertEqual(len(result["missing_required_skills"]), 0)
        self.assertEqual(len(result["missing_preferred_skills"]), 2)
        pref_missing = [s["name"] for s in result["missing_preferred_skills"]]
        self.assertIn("Docker", pref_missing)
        self.assertIn("GraphQL", pref_missing)

    def test_scoring_formula_weights(self):
        """Verify the overall match strictly adheres to documented weights: 40% skills, 25% exp, 20% kw, 15% edu."""
        formula = ResumeJobMatcher.WEIGHT_SKILLS + ResumeJobMatcher.WEIGHT_EXPERIENCE + ResumeJobMatcher.WEIGHT_KEYWORDS + ResumeJobMatcher.WEIGHT_EDUCATION
        self.assertAlmostEqual(formula, 1.0, places=4)
        self.assertEqual(ResumeJobMatcher.WEIGHT_SKILLS, 0.40)
        self.assertEqual(ResumeJobMatcher.WEIGHT_EXPERIENCE, 0.25)
        self.assertEqual(ResumeJobMatcher.WEIGHT_KEYWORDS, 0.20)
        self.assertEqual(ResumeJobMatcher.WEIGHT_EDUCATION, 0.15)

    def test_experience_matching_scenarios(self):
        """Verify experience scoring handles meeting, nearing, and missing tenure requirements."""
        # 1. Candidate meets requirement
        senior_resume = {"full_text": "Senior engineer with 6+ years of experience in distributed systems."}
        senior_jd = {"experience": {"min_years": 5, "is_specified": True}}
        self.assertEqual(ResumeJobMatcher.extract_candidate_experience_years(senior_resume), 6.0)

        # 2. Candidate junior to requirement
        junior_resume = {"full_text": "Junior developer with 1 year experience."}
        self.assertEqual(ResumeJobMatcher.extract_candidate_experience_years(junior_resume), 1.0)

    def test_education_matching_scenarios(self):
        """Verify degree hierarchy recognition (Doctorate > Master's > Bachelor's > Associate)."""
        resume_bs = {"full_text": "Education: Bachelor of Science in Computer Science, UC Berkeley."}
        edu_info = ResumeJobMatcher.extract_candidate_education(resume_bs)
        self.assertEqual(edu_info["level"], 2)
        self.assertEqual(edu_info["degree_name"], "Bachelor's")
        self.assertIn("Computer Science", edu_info["fields"])

        resume_ms = {"full_text": "Master of Science in Software Engineering."}
        edu_ms = ResumeJobMatcher.extract_candidate_education(resume_ms)
        self.assertEqual(edu_ms["level"], 3)
        self.assertEqual(edu_ms["degree_name"], "Master's")

    def test_keyword_matching(self):
        """Verify keyword matching accurately separates matched from missing terms."""
        resume_data = {
            "full_text": "Worked on microservices architecture and cloud infrastructure."
        }
        jd_data = {
            "keywords": [
                {"keyword": "microservices", "count": 3},
                {"keyword": "cloud", "count": 2},
                {"keyword": "kubernetes", "count": 2},
                {"keyword": "kafka", "count": 1}
            ]
        }
        result = ResumeJobMatcher.match(resume_data, jd_data)
        # 2 matched (microservices, cloud), 2 missing (kubernetes, kafka) -> 50%
        self.assertEqual(result["scores"]["keyword_match"], 50)
        matched_kw_names = [k["keyword"] for k in result["matched_keywords"]]
        missing_kw_names = [k["keyword"] for k in result["missing_keywords"]]
        self.assertIn("microservices", matched_kw_names)
        self.assertIn("cloud", matched_kw_names)
        self.assertIn("kubernetes", missing_kw_names)
        self.assertIn("kafka", missing_kw_names)

    def test_error_handling_empty_and_missing_inputs(self):
        """Verify Matcher raises MatcherError on invalid, empty, or missing inputs."""
        valid_resume = {"full_text": "Some resume text"}
        valid_jd = {"required_skills": ["Python"]}

        # Missing resume
        with self.assertRaises(MatcherError) as ctx:
            ResumeJobMatcher.match(None, valid_jd)
        self.assertEqual(ctx.exception.code, "MISSING_RESUME_DATA")

        # Missing JD
        with self.assertRaises(MatcherError) as ctx:
            ResumeJobMatcher.match(valid_resume, None)
        self.assertEqual(ctx.exception.code, "MISSING_JD_DATA")

        # Empty resume text
        with self.assertRaises(MatcherError) as ctx:
            ResumeJobMatcher.match({"full_text": "   "}, valid_jd)
        self.assertEqual(ctx.exception.code, "EMPTY_RESUME_TEXT")

    def test_no_detectable_skills_handled_safely(self):
        """Verify no division by zero occurs when JD has no detectable skills."""
        resume_data = {"full_text": "General business operations and sales management."}
        jd_data = {
            "job_title": "Operations Manager",
            "required_skills": [],
            "preferred_skills": [],
            "keywords": [],
            "education": {},
            "experience": {}
        }
        result = ResumeJobMatcher.match(resume_data, jd_data)
        self.assertTrue(result["success"])
        self.assertIsInstance(result["scores"]["overall_match"], int)
        self.assertIn("overall_match", result["scores"])


class MatcherIntegrationTestCase(unittest.TestCase):
    """Integration tests verifying /api/match and the complete matching pipeline."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_api_match_endpoint_with_raw_text(self):
        """Verify POST /api/match works cleanly with raw text inputs."""
        resp = self.client.post("/api/match", json={
            "resume_text": "Alex Morgan. Software Engineer with 4 years experience in Python, Flask, React, and PostgreSQL. Bachelor's in Computer Science.",
            "job_title": "Full Stack Python Engineer",
            "job_description": "We are seeking a Full Stack Python Engineer with 3+ years experience in Python, React, and SQL. Bachelor's degree required."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("scores", data)
        self.assertGreater(data["scores"]["overall_match"], 70)
        self.assertEqual(data["scores"]["education_match"], 100)
        self.assertIn("match_explanation", data)

    def test_api_match_endpoint_validation_errors(self):
        """Verify POST /api/match rejects missing resume or JD."""
        resp = self.client.post("/api/match", json={"job_description": "We need Python."})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["code"], "MISSING_RESUME_DATA")

        resp = self.client.post("/api/match", json={"resume_text": "Python coder."})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["code"], "MISSING_JD_DATA")

    def test_end_to_end_analyze_and_dashboard_stage4_display(self):
        """Verify end-to-end resume upload, real matching, and Stage 4 dashboard rendering."""
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        self.assertTrue(pdf_path.exists())

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        jd_text = """About the Role:
We are looking for a Senior Full Stack Engineer.

Requirements:
- 4+ years of production experience with Python, TypeScript, React, and PostgreSQL.
- Bachelor's degree in Computer Science.
- Excellent communication and agile collaboration skills.

Preferred:
- Experience with Kubernetes, GraphQL, and Rust."""

        resp = self.client.post(
            "/api/analyze",
            data={
                "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
                "job_title": "Senior Full Stack Engineer",
                "company": "Starlight Technologies",
                "job_description": jd_text
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])

        # Verify real scores are returned in API
        scores = data["data"]["scores"]
        self.assertGreaterEqual(scores["overall_match"], 75)
        self.assertGreaterEqual(scores["skills_match"], 75)
        self.assertEqual(scores["education_match"], 100)
        self.assertEqual(scores["experience_match"], 100)

        # Verify dashboard renders all Stage 4 sections
        analysis_id = data["analysis_id"]
        dash_resp = self.client.get(f"/dashboard?id={analysis_id}&job_title=Senior+Full+Stack+Engineer")
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.get_data(as_text=True)

        # 1. Scores
        self.assertIn("Overall Match", html)
        self.assertIn("Skills Match", html)
        self.assertIn("Experience Match", html)
        self.assertIn("Keyword Match", html)
        self.assertIn("Education Match", html)

        # 2. Match explanation
        self.assertIn("Match Explanation &amp; Score Rationale", html)

        # 3. Matched skills & exact vs related tags
        self.assertIn("Matched Skills", html)
        self.assertIn("Python", html)
        self.assertIn("React", html)

        # 4. Missing required vs preferred skills
        self.assertIn("Missing Preferred Skills", html)

        # 5. Keywords grid
        self.assertIn("Matched Keywords", html)
        self.assertIn("Missing Keywords", html)

        # 6. Banner status
        self.assertIn("Stage 4 Engine Active", html)


if __name__ == "__main__":
    unittest.main()
