"""
Forwarding module for ReportGenerator to maintain consistent package imports.
"""

from services.report_generator import ReportGenerator, ReportGeneratorError, NumberedCanvas

__all__ = [
    "ReportGenerator",
    "ReportGeneratorError",
    "NumberedCanvas"
]
