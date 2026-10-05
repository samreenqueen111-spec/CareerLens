"""
Services module for CareerLens.
Encapsulates business logic, data parsing, analysis coordination, and storage.
"""

from app.services.resume_parser import ResumeParser, ResumeParserError
from app.services.parser_service import ResumeParserService
from app.services.job_analyzer import JobAnalyzer, JobAnalyzerError
from app.services.matcher import ResumeJobMatcher, Matcher, MatcherError
from app.services.skill_gap_analyzer import SkillGapAnalyzer, SkillGapError
from app.services.ats_analyzer import AtsAnalyzer, AtsAnalyzerError
from app.services.roadmap_generator import RoadmapGenerator, RoadmapError
from app.services.analysis_service import AnalysisService
from app.services.storage_service import storage_service
from app.services.sample_data import get_sample_analysis, get_sample_history

__all__ = [
    "ResumeParser",
    "ResumeParserService",
    "ResumeParserError",
    "JobAnalyzer",
    "JobAnalyzerError",
    "ResumeJobMatcher",
    "Matcher",
    "MatcherError",
    "SkillGapAnalyzer",
    "SkillGapError",
    "AtsAnalyzer",
    "AtsAnalyzerError",
    "RoadmapGenerator",
    "RoadmapError",
    "AnalysisService",
    "storage_service",
    "get_sample_analysis",
    "get_sample_history"
]
