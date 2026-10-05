"""
Parser Service Wrapper (Stage 2).
Re-exports ResumeParser and ResumeParserError from app.services.resume_parser
to provide a seamless interface across the codebase.
"""

from app.services.resume_parser import ResumeParser, ResumeParserError

# Alias for compatibility
ResumeParserService = ResumeParser

__all__ = ["ResumeParser", "ResumeParserService", "ResumeParserError"]
