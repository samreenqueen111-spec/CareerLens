"""
Analysis Service Architecture (Stage 4).
Coordinates resume-to-job matching using the deterministic ResumeJobMatcher engine,
integrating parsed resume data (Stage 2) and analyzed Job Description data (Stage 3).
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from app.services.sample_data import get_sample_analysis
from app.services.matcher import ResumeJobMatcher
from app.services.skill_gap_analyzer import SkillGapAnalyzer
from app.services.ats_analyzer import AtsAnalyzer
from app.services.roadmap_generator import RoadmapGenerator


class AnalysisService:
    """
    Main service coordinating resume-to-job matching, skill gap analysis, and ATS checks.
    Uses Stage 4 deterministic ResumeJobMatcher, Stage 5 SkillGapAnalyzer, and AtsAnalyzer
    when real data is available, with clean fallback for preview fixtures.
    """

    def __init__(self, engine: str = "deterministic"):
        self.engine = engine

    def run_analysis(
        self,
        resume_filename: str,
        job_title: str,
        job_description: str,
        company: Optional[str] = None,
        parsed_resume: Optional[Dict[str, Any]] = None,
        job_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute full matching and analysis pipeline.
        When parsed_resume and job_analysis are provided, executes Stages 4 & 5 Real Engines.
        Otherwise falls back to sample preview data.
        """
        sample_fallback = get_sample_analysis(
            job_title=job_title or "Software Engineer",
            company=company or "Target Organization"
        )

        analysis_id = f"analysis-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().strftime("%b %d, %Y - %I:%M %p")
        resolved_title = (job_title or "Target Role").strip()
        resolved_company = (company or "Target Company").strip()
        snippet = (job_description[:180] + "...") if len(job_description) > 180 else job_description

        if parsed_resume and job_analysis:
            # Stage 4: Multi-Dimensional Matching
            match_data = ResumeJobMatcher.match(parsed_resume, job_analysis)

            # Stage 5: Skill Gap Analysis & Transferable Competency Mapping
            gap_data = SkillGapAnalyzer.analyze(match_data, job_analysis, parsed_resume)

            # Stage 5: Transparent ATS-Style Compatibility Audit
            ats_data = AtsAnalyzer.analyze(
                parsed_resume=parsed_resume,
                job_analysis=job_analysis,
                target_job_title=resolved_title
            )

            # Stage 6: Personalized Career Learning Roadmap
            roadmap_data = RoadmapGenerator.generate(
                parsed_resume=parsed_resume,
                job_analysis=job_analysis,
                match_result=match_data,
                skill_gap_analysis=gap_data,
                ats_analysis=ats_data,
                target_job_title=resolved_title
            )

            # Integrate real ATS score into scores dict
            scores = dict(match_data["scores"])
            scores["ats_score"] = ats_data["ats_score"]
            scores["ats_compatibility"] = ats_data["ats_score"]

            # Merge improvement suggestions (ATS formatting + skill alignment)
            combined_suggestions = ats_data["improvement_suggestions"] + match_data["improvement_suggestions"]

            return {
                "id": analysis_id,
                "job_title": resolved_title,
                "company": resolved_company,
                "analyzed_at": timestamp,
                "resume_filename": resume_filename or "Uploaded_Resume.pdf",
                "job_description_snippet": snippet,
                "is_preview": False,
                "scores": scores,
                "scoring_formula": match_data["scoring_formula"],
                "score_verdict": match_data["score_verdict"],
                "match_explanation": match_data["match_explanation"],
                "scores_explanation": match_data["scores_explanation"],
                "matched_skills": match_data["matched_skills"],
                "missing_required_skills": gap_data["missing_required_skills"],
                "missing_preferred_skills": gap_data["missing_preferred_skills"],
                "missing_skills": gap_data["missing_required_skills"] + gap_data["missing_preferred_skills"],
                "weak_matches": gap_data["weak_matches"],
                "partially_satisfied_requirements": gap_data["partially_satisfied_requirements"],
                "skill_gap_summary": gap_data["readiness_verdict"],
                "matched_keywords": match_data["matched_keywords"],
                "missing_keywords": match_data["missing_keywords"],
                "improvement_suggestions": combined_suggestions,
                "candidate_stats": match_data["candidate_stats"],
                "ats_checklist": ats_data["checklist"],
                "ats_summary": ats_data["summary"],
                "formatting_issues": ats_data["formatting_issues"],
                "learning_roadmap": gap_data["learning_roadmap"],
                "personalized_roadmap": roadmap_data
            }

        # Fallback to structured preview
        sample_fallback["id"] = analysis_id
        sample_fallback["job_title"] = resolved_title
        sample_fallback["company"] = resolved_company
        sample_fallback["analyzed_at"] = timestamp
        sample_fallback["resume_filename"] = resume_filename or "Uploaded_Resume.pdf"
        sample_fallback["job_description_snippet"] = snippet
        return sample_fallback

    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific analysis by its identifier."""
        sample = get_sample_analysis()
        sample["id"] = analysis_id
        return sample
