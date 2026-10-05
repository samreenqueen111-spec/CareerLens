"""
Unit and Integration Test Suite for Stage 5:
Skill Gap Analysis + Transparent ATS-Style Resume Analysis.
Tests missing required/preferred skills, weak match diagnostics,
transferable competency bridges, ATS-friendly characteristics,
and end-to-end dashboard integration.
"""

import io
from pathlib import Path
import unittest
from app import create_app
from config import TestingConfig
from app.services.skill_gap_analyzer import SkillGapAnalyzer, SkillGapError
from app.services.ats_analyzer import AtsAnalyzer, AtsAnalyzerError
from app.services.matcher import ResumeJobMatcher
from app.services.job_analyzer import JobAnalyzer

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class SkillGapAnalyzerUnitTestCase(unittest.TestCase):
    """Unit tests for Stage 5 SkillGapAnalyzer."""

    def setUp(self):
        self.parsed_resume = {
            "full_text": """
            Alex Morgan
            alex.morgan@example.com | (555) 234-5678 | San Francisco, CA | linkedin.com/in/alexmorgan
            Summary: Senior Software Engineer with 5+ years building web platforms.
            Skills: Python, React, SQL, Docker, Git
            Experience:
            Senior Engineer - Tech Corp (2021 – Present)
            - Built REST APIs in Python serving 1M daily requests.
            - Designed React user interfaces with modern component architecture.
            - Managed PostgreSQL databases with SQL queries and Docker containers.
            Education:
            Bachelor of Science in Computer Science, UC Berkeley (2017 – 2021)
            Projects:
            Distributed Queue in Python and Redis.
            """,
            "section_contents": {
                "Skills": "Python, React, SQL, Docker, Git",
                "Experience": "Built REST APIs in Python serving 1M daily requests. Designed React user interfaces with modern component architecture. Managed PostgreSQL databases with SQL queries and Docker containers.",
                "Education": "Bachelor of Science in Computer Science, UC Berkeley (2017 – 2021)",
                "Projects": "Distributed Queue in Python and Redis."
            },
            "sections_detected": ["Skills", "Experience", "Education", "Projects"]
        }

        self.job_analysis = {
            "job_title": "Senior Backend Engineer",
            "required_skills": ["Python", "PostgreSQL", "Kafka"],
            "preferred_skills": ["Kubernetes", "GraphQL"],
            "soft_skills": ["Communication", "Teamwork"],
            "keywords": [
                {"keyword": "python", "count": 3},
                {"keyword": "postgresql", "count": 2},
                {"keyword": "kafka", "count": 2}
            ],
            "education": {"degrees": ["Bachelor's"], "fields_of_study": ["Computer Science"], "is_specified": True},
            "experience": {"min_years": 4, "is_specified": True}
        }

    def test_missing_required_skills_prioritization_and_learning_direction(self):
        """Verify missing required skills are flagged as High priority with why it matters and learning direction."""
        match_result = ResumeJobMatcher.match(self.parsed_resume, self.job_analysis)
        gap_result = SkillGapAnalyzer.analyze(match_result, self.job_analysis, self.parsed_resume)

        self.assertTrue(gap_result["success"])
        missing_req = gap_result["missing_required_skills"]
        req_names = [m["name"] for m in missing_req]

        # Kafka is a hard required skill missing from candidate resume
        self.assertIn("Kafka", req_names)
        kafka_item = next(m for m in missing_req if m["name"] == "Kafka")
        self.assertEqual(kafka_item["priority"], "High")
        self.assertEqual(kafka_item["relevance"], "Required")
        self.assertTrue(len(kafka_item["why_it_matters"]) > 20)
        self.assertTrue(len(kafka_item["suggested_learning_direction"]) > 20)

    def test_missing_preferred_skills_prioritization_and_learning_direction(self):
        """Verify missing preferred skills are categorized with Medium/Low priority and learning directions."""
        # Modify resume so Kubernetes and GraphQL are truly missing (remove Docker and REST APIs)
        minimal_resume = {
            "full_text": "Python developer with SQL experience.",
            "section_contents": {"Skills": "Python, SQL", "Experience": "Wrote Python and SQL code."}
        }
        match_result = ResumeJobMatcher.match(minimal_resume, self.job_analysis)
        gap_result = SkillGapAnalyzer.analyze(match_result, self.job_analysis, minimal_resume)

        pref_missing = gap_result["missing_preferred_skills"]
        pref_names = [m["name"] for m in pref_missing]

        self.assertIn("Kubernetes", pref_names)
        k8s_item = next(m for m in pref_missing if m["name"] == "Kubernetes")
        self.assertIn(k8s_item["priority"], ["Medium", "Low"])
        self.assertEqual(k8s_item["relevance"], "Preferred")
        self.assertTrue(len(k8s_item["why_it_matters"]) > 20)
        self.assertTrue(len(k8s_item["suggested_learning_direction"]) > 20)

    def test_weak_and_shallow_matches_detected(self):
        """Verify related skill matches and shallow keyword mentions are categorized as weak matches."""
        match_result = ResumeJobMatcher.match(self.parsed_resume, self.job_analysis)
        gap_result = SkillGapAnalyzer.analyze(match_result, self.job_analysis, self.parsed_resume)

        weak_matches = gap_result["weak_matches"]
        self.assertGreater(len(weak_matches), 0)

        # Kubernetes was matched via Docker (related match)
        weak_names = [w["name"] for w in weak_matches]
        self.assertIn("Kubernetes", weak_names)
        k8s_weak = next(w for w in weak_matches if w["name"] == "Kubernetes")
        self.assertEqual(k8s_weak["match_type"], "related_skill")
        self.assertIn("Docker", k8s_weak["matched_via"])
        self.assertTrue(len(k8s_weak["why_weak"]) > 15)
        self.assertTrue(len(k8s_weak["suggested_improvement"]) > 15)

    def test_related_skills_partially_satisfying_requirements(self):
        """Verify candidate's verified skills are mapped to target requirements with transferable concepts and deltas."""
        # JD asks for Kubernetes (candidate has Docker)
        match_result = ResumeJobMatcher.match(self.parsed_resume, self.job_analysis)
        gap_result = SkillGapAnalyzer.analyze(match_result, self.job_analysis, self.parsed_resume)

        bridges = gap_result["partially_satisfied_requirements"]
        target_skills = [b["target_skill"] for b in bridges]
        self.assertIn("Kubernetes", target_skills)

        k8s_bridge = next(b for b in bridges if b["target_skill"] == "Kubernetes")
        self.assertEqual(k8s_bridge["candidate_skill"], "Docker")
        self.assertIn("Partial Match", k8s_bridge["satisfaction_level"])
        self.assertTrue(len(k8s_bridge["transferable_concepts"]) > 15)
        self.assertTrue(len(k8s_bridge["delta_to_bridge"]) > 15)
        self.assertTrue(len(k8s_bridge["interview_strategy"]) > 15)

    def test_no_invented_skills_guarantee(self):
        """Verify analyzer strictly relies on verified candidate skills and does not claim skills not in resume."""
        candidate_skills = ResumeJobMatcher.extract_candidate_skills(self.parsed_resume)
        match_result = ResumeJobMatcher.match(self.parsed_resume, self.job_analysis)
        gap_result = SkillGapAnalyzer.analyze(match_result, self.job_analysis, self.parsed_resume)

        for bridge in gap_result["partially_satisfied_requirements"]:
            # Every candidate skill claimed in a bridge MUST actually exist in candidate_skills
            self.assertIn(bridge["candidate_skill"], candidate_skills, f"Claimed unverified skill: {bridge['candidate_skill']}")

    def test_learning_roadmap_generation_from_real_gaps(self):
        """Verify structured 3-phase roadmap is formulated using the identified gap skills."""
        match_result = ResumeJobMatcher.match(self.parsed_resume, self.job_analysis)
        gap_result = SkillGapAnalyzer.analyze(match_result, self.job_analysis, self.parsed_resume)

        roadmap = gap_result["learning_roadmap"]
        self.assertEqual(len(roadmap), 3)

        for phase in roadmap:
            self.assertIn("phase", phase)
            self.assertIn("phase_title", phase)
            self.assertIn("target_skill", phase)
            self.assertIn("duration_weeks", phase)
            self.assertIn("estimated_hours", phase)
            self.assertIn("milestones", phase)
            self.assertGreater(len(phase["milestones"]), 0)
            self.assertIn("recommended_resource", phase)

    def test_error_handling_empty_and_missing_payloads(self):
        """Verify SkillGapAnalyzer raises SkillGapError on invalid inputs."""
        with self.assertRaises(SkillGapError) as ctx:
            SkillGapAnalyzer.analyze(None, self.job_analysis, self.parsed_resume)
        self.assertEqual(ctx.exception.code, "MISSING_MATCH_RESULT")

        with self.assertRaises(SkillGapError) as ctx:
            SkillGapAnalyzer.analyze({}, None, self.parsed_resume)
        self.assertEqual(ctx.exception.code, "MISSING_JD_ANALYSIS")

        with self.assertRaises(SkillGapError) as ctx:
            SkillGapAnalyzer.analyze({}, self.job_analysis, None)
        self.assertEqual(ctx.exception.code, "MISSING_PARSED_RESUME")


class AtsAnalyzerUnitTestCase(unittest.TestCase):
    """Unit tests for Stage 5 AtsAnalyzer."""

    def setUp(self):
        self.clean_resume = {
            "full_text": """
            Alex Morgan
            alex.morgan@example.com | (555) 234-5678 | San Francisco, CA | linkedin.com/in/alexmorgan | github.com/alexmorgan

            Professional Summary
            Results-driven Senior Software Engineer with 5+ years of experience designing and scaling web platforms.
            Specialized in Python, React, PostgreSQL, and cloud microservices with a track record of improving latency by 35%.

            Technical Skills
            Languages: Python, JavaScript, TypeScript, SQL
            Frameworks: React, Flask, FastAPI, Node.js
            Databases: PostgreSQL, Redis, MySQL
            DevOps & Tools: Docker, Git, CI/CD, AWS

            Work Experience
            Senior Software Engineer – CloudScale Labs (2021 – Present)
            - Architected high-throughput REST APIs in Python serving 2.5M daily requests with 99.98% uptime.
            - Spearheaded migration of legacy frontend to React and TypeScript, accelerating page load speeds by 42%.
            - Optimized PostgreSQL query execution plans, reducing median endpoint latency by 28%.

            Education
            Bachelor of Science in Computer Science – University of California, Berkeley (2017 – 2021)

            Key Projects
            Distributed Task Queue Engine (2024)
            Built an asynchronous task runner in Python and Redis supporting priority scheduling.

            Certifications
            AWS Certified Solutions Architect – Associate (2024)
            """,
            "word_count": 180,
            "char_count": 1300,
            "section_contents": {
                "Summary/Profile": "Results-driven Senior Software Engineer with 5+ years of experience.",
                "Skills": "Languages: Python, JavaScript, TypeScript, SQL. Frameworks: React, Flask, FastAPI. Databases: PostgreSQL, Redis. Tools: Docker, Git, AWS.",
                "Experience": "Senior Software Engineer – CloudScale Labs (2021 – Present). Architected high-throughput REST APIs in Python serving 2.5M daily requests with 99.98% uptime. Spearheaded migration of legacy frontend to React and TypeScript, accelerating page load speeds by 42%. Optimized PostgreSQL query execution plans, reducing median endpoint latency by 28%.",
                "Education": "Bachelor of Science in Computer Science – University of California, Berkeley (2017 – 2021)",
                "Projects": "Distributed Task Queue Engine (2024) Built an asynchronous task runner in Python and Redis.",
                "Certifications": "AWS Certified Solutions Architect – Associate (2024)"
            },
            "sections_detected": ["Summary/Profile", "Skills", "Experience", "Education", "Projects", "Certifications"]
        }

        self.jd = {
            "job_title": "Senior Software Engineer",
            "keywords": [
                {"keyword": "python", "count": 3},
                {"keyword": "react", "count": 2},
                {"keyword": "postgresql", "count": 2},
                {"keyword": "rest", "count": 2}
            ]
        }

    def test_clean_resume_scores_high_ats_compatibility(self):
        """Verify a well-structured resume achieves high score (>= 85) across transparent criteria."""
        result = AtsAnalyzer.analyze(self.clean_resume, self.jd, "Senior Software Engineer")
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["ats_score"], 85)
        self.assertEqual(result["grade"], "A")
        self.assertEqual(len(result["checklist"]), 11)

    def test_missing_contact_info_lowers_score_and_flags_checklist(self):
        """Verify missing email and phone triggers a failed contact check and lowers score."""
        no_contact_resume = {
            "full_text": "Alex Morgan. Software developer in San Francisco. Skills: Python, React. Experience: 2021-Present at Tech Corp.",
            "word_count": 20,
            "char_count": 120,
            "section_contents": {"Experience": "2021-Present at Tech Corp.", "Skills": "Python, React"}
        }
        result = AtsAnalyzer.analyze(no_contact_resume)
        contact_check = next(c for c in result["checklist"] if c["id"] == "contact_info")
        self.assertEqual(contact_check["status"], "fail")
        self.assertLess(contact_check["score"], 5)

    def test_keyword_stuffing_detection(self):
        """Verify unnatural repetition (>10x) of a single keyword triggers an ATS warning."""
        stuffed_text = ("python " * 25) + "Experienced developer with Python, React, and SQL."
        stuffed_resume = {
            "full_text": stuffed_text,
            "word_count": len(stuffed_text.split()),
            "char_count": len(stuffed_text),
            "section_contents": {"Skills": "Python, React, SQL", "Experience": "Wrote Python code."}
        }
        result = AtsAnalyzer.analyze(stuffed_resume, self.jd)
        kw_check = next(c for c in result["checklist"] if c["id"] == "keyword_density")
        self.assertEqual(kw_check["status"], "warning")
        self.assertIn("stuffing", kw_check["details"].lower())

    def test_action_verbs_and_metrics_verification(self):
        """Verify experience section check rewards strong action verbs and quantified impact."""
        result = AtsAnalyzer.analyze(self.clean_resume, self.jd)
        exp_check = next(c for c in result["checklist"] if c["id"] == "experience_impact")
        self.assertEqual(exp_check["status"], "pass")
        self.assertGreaterEqual(exp_check["score"], 17)

    def test_transparent_audit_does_not_claim_proprietary_system(self):
        """Verify audit summary explicitly states it is a heuristic rule-based audit and not a proprietary ATS."""
        result = AtsAnalyzer.analyze(self.clean_resume, self.jd)
        self.assertIn("ATS compatibility score", result["summary"])
        self.assertNotIn("Proprietary ATS Certified", result["summary"])

    def test_error_handling_empty_resume(self):
        """Verify AtsAnalyzer raises AtsAnalyzerError on empty or None input."""
        with self.assertRaises(AtsAnalyzerError) as ctx:
            AtsAnalyzer.analyze(None)
        self.assertEqual(ctx.exception.code, "MISSING_RESUME_DATA")

        with self.assertRaises(AtsAnalyzerError) as ctx:
            AtsAnalyzer.analyze({"full_text": "   "})
        self.assertEqual(ctx.exception.code, "EMPTY_RESUME_TEXT")


class Stage5IntegrationTestCase(unittest.TestCase):
    """Integration tests verifying /api/skill-gap, /api/ats-audit, and end-to-end dashboard integration."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_api_skill_gap_endpoint(self):
        """Verify POST /api/skill-gap returns structured gap analysis."""
        resp = self.client.post("/api/skill-gap", json={
            "resume_text": "Software Engineer with 4 years experience in Python, Flask, React, and SQL.",
            "job_title": "Senior Backend Engineer",
            "job_description": "We need a Senior Backend Engineer with 5+ years in Python, PostgreSQL, Kafka, and Docker. Preferred: Kubernetes."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("missing_required_skills", data)
        self.assertIn("partially_satisfied_requirements", data)
        self.assertIn("learning_roadmap", data)

    def test_api_ats_audit_endpoint(self):
        """Verify POST /api/ats-audit returns 11-point diagnostic checklist and ATS score."""
        resp = self.client.post("/api/ats-audit", json={
            "resume_text": "Alex Morgan. alex@example.com. (555) 000-1111. San Francisco, CA. Senior Developer. Skills: Python, React, SQL. Experience: 2020-Present at Labs. Built APIs improving latency by 30%. Education: BS in Computer Science.",
            "target_job_title": "Senior Developer"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("ats_score", data)
        self.assertIn("checklist", data)
        self.assertEqual(len(data["checklist"]), 11)

    def test_end_to_end_pipeline_with_stage5_dashboard_rendering(self):
        """Verify end-to-end submission populates real Stage 5 ATS and Skill Gap cards in the dashboard."""
        pdf_path = SAMPLES_DIR / "sample_resume.pdf"
        self.assertTrue(pdf_path.exists())

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        jd_text = """About the Role:
We are seeking a Senior Full Stack Engineer.
Requirements:
- 4+ years of experience with Python, TypeScript, React, PostgreSQL, and Kafka.
- Bachelor's degree in Computer Science.
Preferred:
- Experience with Kubernetes and Rust."""

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

        # Check real Stage 5 fields in API response
        analysis_data = data["data"]
        self.assertIn("ats_checklist", analysis_data)
        self.assertIn("weak_matches", analysis_data)
        self.assertIn("partially_satisfied_requirements", analysis_data)
        self.assertIn("ats_score", analysis_data["scores"])

        # Load dashboard view
        analysis_id = data["analysis_id"]
        dash_resp = self.client.get(f"/dashboard?id={analysis_id}&job_title=Senior+Full+Stack+Engineer")
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.get_data(as_text=True)

        # 1. Missing skills priority and learning directions
        self.assertIn("Missing Required Skills", html)
        self.assertIn("Kafka", html)
        self.assertIn("Why it matters:", html)
        self.assertIn("Learning Direction:", html)

        # 2. Stage 5 Weak Matches & Skill Transferability
        self.assertIn("Skill Transferability &amp; Bridges", html)

        # 3. Real ATS checklist
        self.assertIn("ATS Compatibility Audit", html)
        self.assertIn("Essential Contact Anchors", html)
        self.assertIn("Technical Skills Formatting &amp; Density", html)
        self.assertIn("Personalized Skill Gap Closure Roadmap", html)


if __name__ == "__main__":
    unittest.main()
