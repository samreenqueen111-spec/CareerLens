"""
Unit and Integration Test Suite for Stage 6:
Personalized Career Learning Roadmap for CareerLens AI.

Tests:
1. Roadmap generation using REAL missing and weak skills.
2. Dynamic adaptation across different Job Descriptions.
3. Verification that clearly demonstrated skills are NOT recommended.
4. Correct determination of Priority, Current Status, Learning Level, and Sequence.
5. 3-Phase roadmap structure (Phase 1: High, Phase 2: Medium, Phase 3: Optional).
6. "Why this roadmap?" explanation and employment disclaimer.
7. "Recommended Next Step" top callout card.
8. Handling of 100% match edge case without crashes.
9. Comprehensive input validation and RoadmapError exception handling.
10. REST API endpoint POST /api/roadmap and end-to-end dashboard integration.
"""

import io
from pathlib import Path
import unittest
from app import create_app
from config import TestingConfig
from app.services.roadmap_generator import RoadmapGenerator, RoadmapError
from app.services.matcher import ResumeJobMatcher
from app.services.job_analyzer import JobAnalyzer
from app.services.skill_gap_analyzer import SkillGapAnalyzer

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class RoadmapGeneratorUnitTestCase(unittest.TestCase):
    """Unit tests for Stage 6 RoadmapGenerator."""

    def setUp(self):
        # Candidate possessing Python, SQL, Docker, and Git
        self.candidate_resume = {
            "full_text": """
            Alex Morgan
            alex.morgan@example.com | (555) 234-5678 | San Francisco, CA
            Summary: Backend Software Engineer with 4 years experience building web microservices.
            Skills: Python, SQL, Docker, Git, REST APIs
            Experience:
            Backend Engineer - TechCorp (2021 – Present)
            - Built Python REST services handling 2M daily requests.
            - Containerized backend services with Docker and Docker Compose.
            - Wrote complex SQL queries and maintained database integrity.
            Education:
            Bachelor of Science in Computer Science, UC Berkeley (2017 – 2021)
            Projects:
            Task Scheduler built with Python and Docker.
            """,
            "section_contents": {
                "Skills": "Python, SQL, Docker, Git, REST APIs",
                "Experience": "Built Python REST services handling 2M daily requests. Containerized backend services with Docker and Docker Compose. Wrote complex SQL queries and maintained database integrity.",
                "Education": "Bachelor of Science in Computer Science, UC Berkeley (2017 – 2021)",
                "Projects": "Task Scheduler built with Python and Docker."
            },
            "sections_detected": ["Skills", "Experience", "Education", "Projects"]
        }

        # Target Job A: Backend role requiring Kafka, PostgreSQL, Kubernetes (preferred: Redis)
        self.job_analysis_backend = {
            "job_title": "Senior Backend Engineer",
            "required_skills": ["Python", "PostgreSQL", "Kafka"],
            "preferred_skills": ["Kubernetes", "Redis"],
            "soft_skills": ["Communication", "Teamwork"],
            "keywords": [
                {"keyword": "python", "count": 3},
                {"keyword": "kafka", "count": 2},
                {"keyword": "postgresql", "count": 2}
            ],
            "experience": {"min_years": 4, "is_specified": True}
        }

        # Target Job B: Frontend role requiring React, TypeScript, GraphQL (preferred: Next.js)
        self.job_analysis_frontend = {
            "job_title": "Senior Frontend Engineer",
            "required_skills": ["React", "TypeScript", "JavaScript"],
            "preferred_skills": ["GraphQL", "Next.js"],
            "soft_skills": ["Collaboration", "Agile"],
            "keywords": [
                {"keyword": "react", "count": 3},
                {"keyword": "typescript", "count": 3}
            ],
            "experience": {"min_years": 3, "is_specified": True}
        }

    def test_roadmap_generation_with_real_gaps(self):
        """Verify roadmap is generated containing ONLY missing/weak skills with 3 phases and recommended next step."""
        result = RoadmapGenerator.generate(
            parsed_resume=self.candidate_resume,
            job_analysis=self.job_analysis_backend,
            target_job_title="Senior Backend Engineer"
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(result["phases"]), 3)

        # Recommended Next Step must be present
        next_step = result["recommended_next_step"]
        self.assertIsNotNone(next_step)
        self.assertIn("skill_name", next_step)
        self.assertIn("headline", next_step)
        self.assertIn("why", next_step)
        self.assertIn("immediate_action", next_step)
        self.assertEqual(next_step["priority"], "High")

        # "Why this roadmap?" explanation must be populated
        why = result["why_this_roadmap"]
        self.assertIn("Senior Backend Engineer", why)
        self.assertIn("Disclaimer:", why)
        self.assertIn("not an employment guarantee", why.lower())

        # Check all recommended skills
        recommended_skills = result["all_recommended_skills"]
        skill_names = [s["skill_name"] for s in recommended_skills]

        # Kafka is a missing required skill -> must be in roadmap
        self.assertIn("Kafka", skill_names)
        kafka_item = next(s for s in recommended_skills if s["skill_name"] == "Kafka")
        self.assertEqual(kafka_item["priority"], "High")
        self.assertEqual(kafka_item["current_status"], "Missing")
        self.assertIn(kafka_item["recommended_level"], ["Beginner", "Intermediate"])
        self.assertGreater(len(kafka_item["learning_steps"]), 0)

        # PostgreSQL is required with SQL in candidate resume -> Related skill found
        self.assertIn("PostgreSQL", skill_names)
        pg_item = next(s for s in recommended_skills if s["skill_name"] == "PostgreSQL")
        self.assertEqual(pg_item["priority"], "High")
        self.assertEqual(pg_item["current_status"], "Related skill found")
        self.assertEqual(pg_item["recommended_level"], "Intermediate")
        self.assertTrue(pg_item["prerequisite_bridge"]["has_bridge"])
        self.assertEqual(pg_item["prerequisite_bridge"]["candidate_skill"], "SQL")

    def test_roadmap_adapts_to_different_job_descriptions(self):
        """Verify that the roadmap dynamically adapts to different Job Descriptions for the same candidate."""
        backend_roadmap = RoadmapGenerator.generate(
            parsed_resume=self.candidate_resume,
            job_analysis=self.job_analysis_backend,
            target_job_title="Senior Backend Engineer"
        )
        backend_skills = [s["skill_name"] for s in backend_roadmap["all_recommended_skills"]]

        frontend_roadmap = RoadmapGenerator.generate(
            parsed_resume=self.candidate_resume,
            job_analysis=self.job_analysis_frontend,
            target_job_title="Senior Frontend Engineer"
        )
        frontend_skills = [s["skill_name"] for s in frontend_roadmap["all_recommended_skills"]]

        # Backend roadmap should focus on Kafka, PostgreSQL, Kubernetes, Redis
        self.assertIn("Kafka", backend_skills)
        self.assertNotIn("React", backend_skills)
        self.assertNotIn("TypeScript", backend_skills)

        # Frontend roadmap should focus on React, TypeScript, GraphQL, Next.js
        self.assertIn("React", frontend_skills)
        self.assertIn("TypeScript", frontend_skills)
        self.assertNotIn("Kafka", frontend_skills)
        self.assertNotIn("PostgreSQL", frontend_skills)

    def test_skills_already_in_resume_are_not_recommended(self):
        """Verify candidate's verified skills (Python, Docker, SQL) are NOT recommended in roadmap."""
        result = RoadmapGenerator.generate(
            parsed_resume=self.candidate_resume,
            job_analysis=self.job_analysis_backend,
            target_job_title="Senior Backend Engineer"
        )
        rec_names = [s["skill_name"] for s in result["all_recommended_skills"]]

        # Python is verified with concrete experience -> must NOT be recommended
        self.assertNotIn("Python", rec_names)
        # Docker is verified with concrete experience -> must NOT be recommended
        self.assertNotIn("Docker", rec_names)

    def test_no_arbitrary_popular_skills_recommended(self):
        """Verify that popular skills not mentioned in the JD are never arbitrarily injected."""
        minimal_jd = {
            "job_title": "Java Developer",
            "required_skills": ["Java", "Spring Boot"],
            "preferred_skills": ["Hibernate"],
            "keywords": [{"keyword": "java", "count": 2}]
        }
        result = RoadmapGenerator.generate(
            parsed_resume=self.candidate_resume,
            job_analysis=minimal_jd,
            target_job_title="Java Developer"
        )
        rec_names = [s["skill_name"] for s in result["all_recommended_skills"]]

        # Should only recommend Java, Spring Boot, Hibernate
        self.assertIn("Java", rec_names)
        self.assertIn("Spring Boot", rec_names)
        self.assertNotIn("Kubernetes", rec_names)
        self.assertNotIn("React", rec_names)
        self.assertNotIn("Kafka", rec_names)

    def test_phases_organization_and_priority_mapping(self):
        """Verify Phase 1 contains High priority, Phase 2 contains Medium priority, Phase 3 contains Low priority."""
        result = RoadmapGenerator.generate(
            parsed_resume=self.candidate_resume,
            job_analysis=self.job_analysis_backend,
            target_job_title="Senior Backend Engineer"
        )

        phase_1 = result["phases"][0]
        phase_2 = result["phases"][1]
        phase_3 = result["phases"][2]

        self.assertEqual(phase_1["phase_number"], 1)
        self.assertEqual(phase_2["phase_number"], 2)
        self.assertEqual(phase_3["phase_number"], 3)

        for s in phase_1["skills"]:
            self.assertEqual(s["priority"], "High")

        for s in phase_2["skills"]:
            self.assertEqual(s["priority"], "Medium")

        for s in phase_3["skills"]:
            self.assertEqual(s["priority"], "Low")

    def test_suggested_learning_sequence_assignment(self):
        """Verify that each recommended skill is assigned an incremental suggested sequence number."""
        result = RoadmapGenerator.generate(
            parsed_resume=self.candidate_resume,
            job_analysis=self.job_analysis_backend,
            target_job_title="Senior Backend Engineer"
        )
        skills = result["all_recommended_skills"]
        for idx, skill in enumerate(skills, start=1):
            self.assertEqual(skill["suggested_sequence"], idx)

    def test_all_skills_matched_edge_case(self):
        """Verify candidate with 100% matched skills produces interview/architecture guidance without error."""
        full_match_resume = {
            "full_text": """
            Senior Engineer
            Skills: Python, PostgreSQL, Kafka, Kubernetes, Redis
            Experience:
            Built Python and Kafka event pipelines with PostgreSQL and Kubernetes. Managed Redis cache.
            """,
            "section_contents": {
                "Skills": "Python, PostgreSQL, Kafka, Kubernetes, Redis",
                "Experience": "Built Python and Kafka event pipelines with PostgreSQL and Kubernetes. Managed Redis cache."
            }
        }
        result = RoadmapGenerator.generate(
            parsed_resume=full_match_resume,
            job_analysis=self.job_analysis_backend,
            target_job_title="Senior Backend Engineer"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["total_recommended_skills"], 0)
        self.assertIn("System Architecture", result["recommended_next_step"]["skill_name"])
        self.assertIn("all specified technical criteria", result["why_this_roadmap"].lower())

    def test_error_handling_empty_and_missing_payloads(self):
        """Verify RoadmapGenerator raises RoadmapError on missing or invalid inputs."""
        with self.assertRaises(RoadmapError) as ctx:
            RoadmapGenerator.generate(None, self.job_analysis_backend)
        self.assertEqual(ctx.exception.code, "MISSING_PARSED_RESUME")

        with self.assertRaises(RoadmapError) as ctx:
            RoadmapGenerator.generate(self.candidate_resume, None)
        self.assertEqual(ctx.exception.code, "MISSING_JD_ANALYSIS")


class Stage6IntegrationTestCase(unittest.TestCase):
    """Integration tests verifying /api/roadmap endpoint and end-to-end dashboard integration."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_api_roadmap_endpoint_with_raw_text(self):
        """Verify POST /api/roadmap generates structured roadmap from raw text."""
        resp = self.client.post("/api/roadmap", json={
            "resume_text": "Software developer with 3 years experience in Python, Flask, and SQL.",
            "job_title": "Cloud Backend Engineer",
            "job_description": "We require a Cloud Backend Engineer with Python, PostgreSQL, Kafka, and Docker. Preferred: AWS and Kubernetes."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("phases", data)
        self.assertEqual(len(data["phases"]), 3)
        self.assertIn("recommended_next_step", data)
        self.assertIn("why_this_roadmap", data)

    def test_end_to_end_pipeline_with_stage6_dashboard_rendering(self):
        """Verify end-to-end resume upload and JD analysis renders Stage 6 Roadmap in dashboard."""
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
- Experience with Kubernetes and Redis."""

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

        # Check real Stage 6 fields in API response
        analysis_data = data["data"]
        self.assertIn("personalized_roadmap", analysis_data)
        p_roadmap = analysis_data["personalized_roadmap"]
        self.assertTrue(p_roadmap["success"])
        self.assertIn("recommended_next_step", p_roadmap)
        self.assertIn("phases", p_roadmap)

        # Load dashboard view
        analysis_id = data["analysis_id"]
        dash_resp = self.client.get(f"/dashboard?id={analysis_id}&job_title=Senior+Full+Stack+Engineer")
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.get_data(as_text=True)

        # 1. Stage 6 Header and Section
        self.assertIn("Personalized Career Roadmap", html)
        self.assertIn("Why this roadmap?", html)
        self.assertIn("Recommended Next Step", html)

        # 2. Phases
        self.assertIn("Phase 1: High Priority", html)
        self.assertIn("Phase 2: Medium Priority", html)
        self.assertIn("Phase 3: Optional / Nice-to-Have", html)

        # 3. Backward compatibility check for Stage 5 test assertion
        self.assertIn("Personalized Skill Gap Closure Roadmap", html)


if __name__ == "__main__":
    unittest.main()
