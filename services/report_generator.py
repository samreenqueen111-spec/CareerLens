"""
Report Generator Service for CareerLens AI (Stage 9).
Generates publication-quality, professional PDF candidate evaluation reports
using ReportLab with precise typography, structured scorecard grids,
dynamic running headers/footers, and page numbering.
"""

import io
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for dynamic total page count calculation
    and professional running headers and footers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#64748b"))

        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(40, 752, "CareerLens AI • Professional Candidate Evaluation Report")
            self.drawRightString(letter[0] - 40, 752, "Confidential Candidate Analysis")
            self.setStrokeColor(HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(40, 744, letter[0] - 40, 744)

        # Running Footer (all pages)
        self.setStrokeColor(HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 42, letter[0] - 40, 42)

        self.drawString(
            40,
            30,
            "CareerLens AI Platform • Evaluation private to account holder • Not for public distribution"
        )
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 30, page_str)
        self.restoreState()


class ReportGeneratorError(Exception):
    """Exception raised when PDF report compilation fails."""
    def __init__(self, message: str, code: str = "REPORT_GEN_FAILED"):
        super().__init__(message)
        self.message = message
        self.code = code


class ReportGenerator:
    """
    Generates high-fidelity PDF evaluation dossiers for completed CareerLens AI analyses.
    Includes all 14 required sections:
    1. Candidate/Resume summary
    2. Target Job Title & Company
    3. Overall Match Score
    4. Skills Match Score
    5. Keyword Match Score
    6. Education Match
    7. Experience Match
    8. ATS Readiness Score
    9. Matched Skills
    10. Missing Required Skills
    11. Missing Preferred Skills
    12. Resume Strengths
    13. Improvement Suggestions
    14. Personalized Career Roadmap
    """

    @classmethod
    def generate_pdf(cls, analysis_data: Dict[str, Any]) -> bytes:
        """
        Compile analysis data into a structured multi-page PDF document.
        Returns the raw PDF file bytes in memory.
        """
        if not analysis_data or not isinstance(analysis_data, dict):
            raise ReportGeneratorError("Valid analysis data dictionary is required to generate report.")

        buffer = io.BytesIO()

        try:
            # 40pt horizontal margins, 48pt top/bottom margins
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=48,
                bottomMargin=48
            )

            story = []
            styles = cls._build_stylesheet()

            # 1 & 2. Cover / Header Banner & Job Target
            cls._build_header_banner(story, analysis_data, styles)

            # Candidate & Document Summary
            cls._build_candidate_summary(story, analysis_data, styles)

            # 3 to 8. Executive Compatibility Scorecard
            cls._build_scorecard(story, analysis_data, styles)

            # 9. Matched Skills
            cls._build_matched_skills(story, analysis_data, styles)

            # 10. Missing Required Skills
            cls._build_missing_required_skills(story, analysis_data, styles)

            # 11. Missing Preferred Skills
            cls._build_missing_preferred_skills(story, analysis_data, styles)

            # 12. Resume Strengths
            cls._build_resume_strengths(story, analysis_data, styles)

            # 13. Improvement Suggestions
            cls._build_improvement_suggestions(story, analysis_data, styles)

            # 14. Personalized Career Roadmap
            cls._build_career_roadmap(story, analysis_data, styles)

            # Confidentiality & Data Privacy Notice
            cls._build_privacy_footer(story, styles)

            # Build document with two-pass canvas
            doc.build(story, canvasmaker=NumberedCanvas)

            pdf_bytes = buffer.getvalue()
            return pdf_bytes

        except Exception as e:
            if isinstance(e, ReportGeneratorError):
                raise
            raise ReportGeneratorError(f"Failed to compile PDF report: {str(e)}") from e
        finally:
            buffer.close()

    @staticmethod
    def _build_stylesheet():
        """Define unified typographic hierarchy and color tokens."""
        base = getSampleStyleSheet()

        return {
            "BrandTitle": ParagraphStyle(
                "BrandTitle",
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=HexColor("#1e3a8a")
            ),
            "BrandSubtitle": ParagraphStyle(
                "BrandSubtitle",
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=HexColor("#64748b")
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader",
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=17,
                textColor=HexColor("#0f172a"),
                spaceBefore=10,
                spaceAfter=6
            ),
            "SubsectionHeader": ParagraphStyle(
                "SubsectionHeader",
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=14,
                textColor=HexColor("#1e293b"),
                spaceBefore=6,
                spaceAfter=3
            ),
            "Body": ParagraphStyle(
                "Body",
                fontName="Helvetica",
                fontSize=8.5,
                leading=12,
                textColor=HexColor("#334155")
            ),
            "BodyBold": ParagraphStyle(
                "BodyBold",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=12,
                textColor=HexColor("#0f172a")
            ),
            "ScoreBig": ParagraphStyle(
                "ScoreBig",
                fontName="Helvetica-Bold",
                fontSize=24,
                leading=28,
                alignment=1,  # Center
                textColor=HexColor("#1e3a8a")
            ),
            "ScoreLabel": ParagraphStyle(
                "ScoreLabel",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                alignment=1,
                textColor=HexColor("#475569")
            ),
            "TagStyle": ParagraphStyle(
                "TagStyle",
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=10,
                textColor=HexColor("#1e3a8a")
            ),
            "CalloutTitle": ParagraphStyle(
                "CalloutTitle",
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=13,
                textColor=HexColor("#0369a1")
            ),
            "Disclaimer": ParagraphStyle(
                "Disclaimer",
                fontName="Helvetica-Oblique",
                fontSize=7.5,
                leading=10,
                textColor=HexColor("#94a3b8")
            )
        }

    @classmethod
    def _build_header_banner(cls, story: list, data: dict, styles: dict):
        """Render CareerLens AI branded header with analysis target metadata."""
        job_title = data.get("job_title") or "Target Role"
        company = data.get("company") or "Target Organization"
        analysis_id = data.get("id") or "analysis-report"
        date_str = data.get("analyzed_at") or datetime.now().strftime("%B %d, %Y • %I:%M %p")

        header_table = Table(
            [
                [
                    Paragraph("<b>CAREERLENS</b> <font color='#2563eb'>AI</font>", styles["BrandTitle"]),
                    Paragraph(f"<b>Report ID:</b> {analysis_id}<br/><b>Date:</b> {date_str}", styles["BrandSubtitle"])
                ],
                [
                    Paragraph("Intelligent Resume-to-Job Qualification & Alignment Audit", styles["BrandSubtitle"]),
                    Paragraph("<b>Confidential Candidate Evaluation</b>", styles["BrandSubtitle"])
                ]
            ],
            colWidths=[340, 192]
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#2563eb"), spaceAfter=10))

        # Target Role Callout Card
        target_info = [
            [
                Paragraph("<b>Target Position:</b>", styles["BodyBold"]),
                Paragraph(job_title, styles["BodyBold"]),
                Paragraph("<b>Target Company:</b>", styles["BodyBold"]),
                Paragraph(company, styles["Body"])
            ]
        ]
        target_table = Table(target_info, colWidths=[90, 200, 100, 142])
        target_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#eff6ff")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#bfdbfe")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(target_table)
        story.append(Spacer(1, 10))

    @classmethod
    def _build_candidate_summary(cls, story: list, data: dict, styles: dict):
        """Section 1: Candidate and parsed resume summary."""
        parsed = data.get("parsed_resume", {})
        filename = data.get("resume_filename", "Uploaded_Resume.pdf")
        word_count = parsed.get("word_count", 0) if isinstance(parsed, dict) else 0
        char_count = parsed.get("char_count", 0) if isinstance(parsed, dict) else 0
        contact = parsed.get("contact_details", {}) if isinstance(parsed, dict) else {}
        name = contact.get("name") or "Candidate Profile"
        email = contact.get("email") or "Not provided"
        phone = contact.get("phone") or "Not provided"

        # Candidate bio / summary section snippet
        summary_text = ""
        section_contents = parsed.get("section_contents", {}) if isinstance(parsed, dict) else {}
        if isinstance(section_contents, dict):
            summary_text = section_contents.get("summary") or section_contents.get("profile") or ""

        if not summary_text:
            sections = parsed.get("sections", {}) if isinstance(parsed, dict) else {}
            if isinstance(sections, dict):
                summary_text = sections.get("summary") or sections.get("profile") or ""

        if not summary_text:
            preview = parsed.get("preview_text", "") if isinstance(parsed, dict) else ""
            summary_text = preview[:240] + ("..." if len(preview) > 240 else "")
        if not summary_text:
            summary_text = "Standard resume document parsed and verified for applicant tracking alignment."

        story.append(Paragraph("1. Candidate & Document Overview", styles["SectionHeader"]))

        overview_data = [
            [
                Paragraph(f"<b>Candidate:</b> {name}", styles["Body"]),
                Paragraph(f"<b>Email:</b> {email}", styles["Body"]),
                Paragraph(f"<b>Phone:</b> {phone}", styles["Body"])
            ],
            [
                Paragraph(f"<b>Resume File:</b> {filename}", styles["Body"]),
                Paragraph(f"<b>Word Count:</b> {word_count:,} words", styles["Body"]),
                Paragraph(f"<b>Char Count:</b> {char_count:,} characters", styles["Body"])
            ]
        ]
        overview_table = Table(overview_data, colWidths=[180, 180, 172])
        overview_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(overview_table)
        story.append(Spacer(1, 6))

        # Profile quote box
        quote_table = Table([[
            Paragraph(f"<b>Profile Excerpt:</b> <i>\"{summary_text.strip()}\"</i>", styles["Body"])
        ]], colWidths=[532])
        quote_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(quote_table)
        story.append(Spacer(1, 12))

    @classmethod
    def _build_scorecard(cls, story: list, data: dict, styles: dict):
        """Sections 3 to 8: Multi-dimensional match scores & ATS score."""
        scores = data.get("scores", {})
        overall = scores.get("overall_match", 0)
        skills = scores.get("skills_match", 0)
        keyword = scores.get("keyword_coverage", scores.get("keyword_match", 0))
        education = scores.get("education_relevance", scores.get("education_match", 0))
        experience = scores.get("experience_relevance", scores.get("experience_match", 0))
        ats = scores.get("ats_score", scores.get("ats_compatibility", 0))

        def get_score_color(val: int, is_ats: bool = False) -> str:
            high_thresh = 80 if is_ats else 75
            mid_thresh = 65 if is_ats else 50
            if val >= high_thresh:
                return "#059669"  # Green
            elif val >= mid_thresh:
                return "#d97706"  # Amber
            return "#dc2626"      # Red

        def get_score_badge(val: int, metric_type: str) -> str:
            if metric_type == "overall":
                return "High Match" if val >= 75 else ("Moderate" if val >= 50 else "Needs Work")
            elif metric_type == "skills":
                return "Aligned" if val >= 75 else ("Moderate" if val >= 50 else "Gaps Found")
            elif metric_type == "keywords":
                return "Strong" if val >= 75 else ("Moderate" if val >= 50 else "Review")
            elif metric_type == "education":
                return "Qualified" if val >= 75 else ("Acceptable" if val >= 50 else "Discipline Gap")
            elif metric_type == "experience":
                return "Aligned" if val >= 75 else ("Partial" if val >= 50 else "Needs Growth")
            elif metric_type == "ats":
                return "ATS Ready" if val >= 80 else ("Review Tips" if val >= 65 else "Needs Fix")
            return "Evaluated"

        c_overall = get_score_color(overall)
        c_skills = get_score_color(skills)
        c_keyword = get_score_color(keyword)
        c_education = get_score_color(education)
        c_experience = get_score_color(experience)
        c_ats = get_score_color(ats, is_ats=True)

        story.append(Paragraph("2. Executive Compatibility Scorecard", styles["SectionHeader"]))

        # 6-Card Metric Grid with Color Accents & Status Badges
        score_cards = [
            [
                Paragraph(f"<font color='{c_overall}'>{overall}%</font>", styles["ScoreBig"]),
                Paragraph(f"<font color='{c_skills}'>{skills}%</font>", styles["ScoreBig"]),
                Paragraph(f"<font color='{c_keyword}'>{keyword}%</font>", styles["ScoreBig"]),
                Paragraph(f"<font color='{c_education}'>{education}%</font>", styles["ScoreBig"]),
                Paragraph(f"<font color='{c_experience}'>{experience}%</font>", styles["ScoreBig"]),
                Paragraph(f"<font color='{c_ats}'>{ats}%</font>", styles["ScoreBig"])
            ],
            [
                Paragraph(f"<b>3. Overall Match</b><br/><font color='{c_overall}'><b>[{get_score_badge(overall, 'overall')}]</b></font>", styles["ScoreLabel"]),
                Paragraph(f"<b>4. Skills Match</b><br/><font color='{c_skills}'><b>[{get_score_badge(skills, 'skills')}]</b></font>", styles["ScoreLabel"]),
                Paragraph(f"<b>5. Keyword Match</b><br/><font color='{c_keyword}'><b>[{get_score_badge(keyword, 'keywords')}]</b></font>", styles["ScoreLabel"]),
                Paragraph(f"<b>6. Education</b><br/><font color='{c_education}'><b>[{get_score_badge(education, 'education')}]</b></font>", styles["ScoreLabel"]),
                Paragraph(f"<b>7. Experience</b><br/><font color='{c_experience}'><b>[{get_score_badge(experience, 'experience')}]</b></font>", styles["ScoreLabel"]),
                Paragraph(f"<b>8. ATS Readiness</b><br/><font color='{c_ats}'><b>[{get_score_badge(ats, 'ats')}]</b></font>", styles["ScoreLabel"])
            ]
        ]
        score_table = Table(score_cards, colWidths=[88, 88, 88, 88, 88, 100])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 6))

        # Formula footnote
        formula_text = (
            f"<b>Scoring Formula:</b> Overall Match ({overall}%) is computed from 40% Technical Skills ({skills}%), "
            f"25% Experience Relevance ({experience}%), 20% Keyword Coverage ({keyword}%), and 15% Education ({education}%). "
            f"Applicant Tracking System (ATS) Readiness is evaluated independently at {ats}%."
        )
        story.append(Paragraph(formula_text, styles["Disclaimer"]))
        story.append(Spacer(1, 12))

    @classmethod
    def _build_matched_skills(cls, story: list, data: dict, styles: dict):
        """Section 9: Matched Skills detected in both resume and JD."""
        matched = data.get("matched_skills", [])
        story.append(Paragraph("3. Matched Skills (Verified Competencies)", styles["SectionHeader"]))

        if matched:
            skill_names = []
            for s in matched:
                if isinstance(s, dict):
                    skill_names.append(s.get("name") or s.get("skill") or "")
                elif isinstance(s, str):
                    skill_names.append(s)

            skill_names = [s for s in skill_names if s]
            # Group into rows of 4
            chunks = [skill_names[i:i + 4] for i in range(0, len(skill_names), 4)]
            table_rows = []
            for row in chunks:
                cells = [Paragraph(f"• <b>{item}</b>", styles["Body"]) for item in row]
                while len(cells) < 4:
                    cells.append(Paragraph("", styles["Body"]))
                table_rows.append(cells)

            skill_table = Table(table_rows, colWidths=[133, 133, 133, 133])
            skill_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f0fdf4")),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#86efac")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(skill_table)
        else:
            story.append(Paragraph("<i>No direct skill overlap detected between resume and job requirements.</i>", styles["Body"]))

        story.append(Spacer(1, 12))

    @classmethod
    def _build_missing_required_skills(cls, story: list, data: dict, styles: dict):
        """Section 10: Missing Required Skills (Critical Hard Requirements)."""
        missing_req = data.get("missing_required_skills", [])
        story.append(Paragraph("4. Missing Required Skills (High Priority Gaps)", styles["SectionHeader"]))

        if missing_req:
            rows = [
                [
                    Paragraph("<b>Required Skill</b>", styles["BodyBold"]),
                    Paragraph("<b>Priority</b>", styles["BodyBold"]),
                    Paragraph("<b>Why It Matters</b>", styles["BodyBold"]),
                    Paragraph("<b>Recommended Action</b>", styles["BodyBold"])
                ]
            ]
            for item in missing_req[:6]:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("skill") or "Required Skill"
                    priority = item.get("priority") or "High"
                    why = item.get("why_it_matters") or item.get("reason") or "Core technical qualification specified in job requirements."
                    direction = item.get("learning_direction") or item.get("suggested_direction") or "Build practical project demonstrating core APIs."
                else:
                    name = str(item)
                    priority = "High"
                    why = "Mandatory hard competency outlined in job description."
                    direction = "Review official documentation and implement sample project."

                rows.append([
                    Paragraph(f"<b>{name}</b>", styles["BodyBold"]),
                    Paragraph("<font color='#dc2626'><b>HIGH</b></font>", styles["Body"]),
                    Paragraph(why[:140], styles["Body"]),
                    Paragraph(direction[:140], styles["Body"])
                ])

            req_table = Table(rows, colWidths=[100, 60, 192, 180])
            req_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#fee2e2")),
                ("BACKGROUND", (0, 1), (-1, -1), HexColor("#fef2f2")),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#fca5a5")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#fecaca")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(req_table)
        else:
            story.append(Paragraph("<b>Excellent:</b> Candidate resume demonstrates all core required technical skills.", styles["Body"]))

        story.append(Spacer(1, 12))

    @classmethod
    def _build_missing_preferred_skills(cls, story: list, data: dict, styles: dict):
        """Section 11: Missing Preferred Skills (Bonus Competencies)."""
        missing_pref = data.get("missing_preferred_skills", [])
        story.append(Paragraph("5. Missing Preferred Skills (Nice-to-Have Competencies)", styles["SectionHeader"]))

        if missing_pref:
            rows = [
                [
                    Paragraph("<b>Preferred Skill</b>", styles["BodyBold"]),
                    Paragraph("<b>Priority</b>", styles["BodyBold"]),
                    Paragraph("<b>Career Readiness Impact</b>", styles["BodyBold"])
                ]
            ]
            for item in missing_pref[:6]:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("skill") or "Preferred Skill"
                    priority = item.get("priority") or "Medium"
                    impact = item.get("why_it_matters") or item.get("reason") or "Secondary tooling providing competitive differentiation."
                else:
                    name = str(item)
                    priority = "Medium"
                    impact = "Helpful secondary technology for candidate edge."

                rows.append([
                    Paragraph(f"• <b>{name}</b>", styles["BodyBold"]),
                    Paragraph(f"<font color='#d97706'><b>{priority.upper()}</b></font>", styles["Body"]),
                    Paragraph(impact[:180], styles["Body"])
                ])

            pref_table = Table(rows, colWidths=[130, 80, 322])
            pref_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#fef3c7")),
                ("BACKGROUND", (0, 1), (-1, -1), HexColor("#fffbeb")),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#fde68a")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#fef08a")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(pref_table)
        else:
            story.append(Paragraph("<i>No missing preferred skills flagged.</i>", styles["Body"]))

        story.append(Spacer(1, 12))

    @classmethod
    def _build_resume_strengths(cls, story: list, data: dict, styles: dict):
        """Section 12: Resume Strengths identified by the matching and ATS engine."""
        story.append(Paragraph("6. Resume Strengths & Competitive Assets", styles["SectionHeader"]))

        strengths = []
        # Draw from match_explanation or positive ATS checks
        match_exp = data.get("match_explanation")
        if match_exp:
            strengths.append(match_exp)

        ats_checks = data.get("ats_checklist", [])
        for check in ats_checks:
            if isinstance(check, dict) and check.get("status") == "pass":
                title = check.get("title") or ""
                details = check.get("details") or ""
                strengths.append(f"<b>{title}:</b> {details}")

        if not strengths:
            scores = data.get("scores", {})
            if scores.get("skills_match", 0) >= 70:
                strengths.append("<b>Strong Skill Alignment:</b> Demonstrates solid core technical fundamentals for the target position.")
            if scores.get("ats_score", 0) >= 80:
                strengths.append("<b>High Machine Readability:</b> Clean layout and structured sections pass automated parsing filters cleanly.")
            strengths.append("<b>Structured Documentation:</b> Standard resume sections allow hiring managers to quickly parse key qualifications.")

        table_rows = []
        for s in strengths[:4]:
            table_rows.append([
                Paragraph("<font color='#059669'><b>•</b></font>", styles["BodyBold"]),
                Paragraph(s, styles["Body"])
            ])

        str_table = Table(table_rows, colWidths=[20, 512])
        str_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(str_table)
        story.append(Spacer(1, 12))

    @classmethod
    def _build_improvement_suggestions(cls, story: list, data: dict, styles: dict):
        """Section 13: Actionable Improvement Suggestions."""
        story.append(Paragraph("7. Actionable Resume Improvement Recommendations", styles["SectionHeader"]))

        suggestions = data.get("improvement_suggestions", [])
        if not suggestions:
            # Fallback recommendations if list is empty
            suggestions = [
                "Quantify bullet points with measurable impact (e.g. latency reduced by X%, throughput increased by Y%).",
                "Integrate exact keywords from the target job description into your latest work experience entries.",
                "Ensure technical skills overview mirrors the specific frameworks mentioned in job requirements."
            ]

        table_rows = []
        for i, sug in enumerate(suggestions[:5], 1):
            if isinstance(sug, dict):
                title = sug.get("title") or sug.get("category") or ""
                desc = sug.get("description") or sug.get("text") or sug.get("details") or ""
                if title and desc:
                    text_content = f"<b>{title}:</b> {desc}"
                else:
                    text_content = desc or title or str(sug)
            else:
                text_content = str(sug)

            table_rows.append([
                Paragraph(f"<b>{i}.</b>", styles["BodyBold"]),
                Paragraph(text_content, styles["Body"])
            ])

        sug_table = Table(table_rows, colWidths=[20, 512])
        sug_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#f1f5f9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(sug_table)
        story.append(Spacer(1, 12))

    @classmethod
    def _build_career_roadmap(cls, story: list, data: dict, styles: dict):
        """Section 14: Personalized Career Learning Roadmap."""
        roadmap = data.get("personalized_roadmap") or data.get("learning_roadmap") or {}
        story.append(Paragraph("8. Personalized Career Learning Roadmap", styles["SectionHeader"]))

        # Top Recommended Next Step Callout
        top_step = (
            roadmap.get("recommended_next_step") or
            roadmap.get("top_recommended_next_step")
        ) if isinstance(roadmap, dict) else None
        if top_step:
            skill = top_step.get("skill_name") or "Primary Skill"
            level = top_step.get("recommended_level") or top_step.get("recommended_learning_level") or "Intermediate"
            time_est = top_step.get("estimated_effort") or top_step.get("estimated_time_commitment") or "10-15 hours"
            first_action = top_step.get("immediate_action") or top_step.get("immediate_first_action") or "Complete hands-on quickstart project."

            callout_data = [
                [
                    Paragraph(f"<b>Top Recommended Next Step: {skill}</b> ({level} Level • {time_est})", styles["CalloutTitle"])
                ],
                [
                    Paragraph(f"<b>Immediate Action:</b> {first_action}", styles["Body"])
                ]
            ]
            callout_table = Table(callout_data, colWidths=[532])
            callout_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f0f9ff")),
                ("BOX", (0, 0), (-1, -1), 1, HexColor("#0284c7")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(callout_table)
            story.append(Spacer(1, 8))

        # Phases
        phases = roadmap.get("phases", []) if isinstance(roadmap, dict) else []
        if phases:
            step_counter = 1
            for p in phases[:3]:
                num = p.get("phase_number") or ""
                title = p.get("phase_name") or p.get("phase_title") or f"Phase {num}"
                skills_list = p.get("skills") or []
                
                skill_entries = []
                for s in skills_list:
                    if isinstance(s, dict):
                        s_name = s.get("skill_name") or s.get("name") or "Skill"
                        s_prio = s.get("priority") or "Recommended"
                        s_lvl = s.get("recommended_level") or "Foundational"
                        s_effort = s.get("estimated_effort") or ""
                        seq_num = s.get("suggested_sequence") or step_counter
                        step_counter += 1
                        
                        entry_text = f"<b>Step {seq_num}: {s_name}</b>"
                        meta_parts = [part for part in [s_prio, s_lvl, s_effort] if part]
                        if meta_parts:
                            entry_text += f" <font color='#64748b'>({ ' • '.join(meta_parts) })</font>"
                        
                        steps = s.get("learning_steps") or []
                        if steps:
                            step_bullets = "<br/>".join([f"&nbsp;&nbsp;{i+1}. {st}" for i, st in enumerate(steps[:2])])
                            entry_text += f"<br/>{step_bullets}"
                        skill_entries.append(entry_text)
                    else:
                        s_name = str(s)
                        if s_name:
                            skill_entries.append(f"<b>Step {step_counter}: {s_name}</b>")
                            step_counter += 1

                skills_content = "<br/>".join(skill_entries) if skill_entries else "Core foundational competencies"

                p_table = Table([
                    [
                        Paragraph(f"<b>{title}</b>", styles["BodyBold"]),
                        Paragraph(skills_content, styles["Body"])
                    ]
                ], colWidths=[150, 382])
                p_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (0, -1), HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(p_table)
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("<i>All core job competencies are satisfied. Focus on senior interview portfolio stories.</i>", styles["Body"]))

        story.append(Spacer(1, 14))

    @classmethod
    def _build_privacy_footer(cls, story: list, styles: dict):
        """Privacy guarantee and disclaimer note."""
        notice_table = Table([[
            Paragraph(
                "<b>CONFIDENTIALITY NOTICE:</b> This candidate evaluation report was generated automatically by CareerLens AI "
                "for the authorized user. No passwords, credentials, or personal secrets are stored in this document. "
                "Completing learning roadmaps prepares candidates for technical screening but does not guarantee employment.",
                styles["Disclaimer"]
            )
        ]], colWidths=[532])
        notice_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(notice_table)
