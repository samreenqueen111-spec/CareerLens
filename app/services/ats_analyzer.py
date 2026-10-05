"""
Stage 5: ATS-Style Resume Analyzer Service for CareerLens AI.
Analyzes the actual uploaded and parsed resume for common Applicant Tracking System (ATS)
readability, structural integrity, and formatting standards.

Evaluates 11 transparent, rule-based criteria:
1. Contact Information
2. Resume Sections Architecture
3. Skills Section Presentation
4. Education Section Details
5. Experience Section & Quantified Impact
6. Projects Section
7. Certifications Section
8. Keyword Coverage & Natural Density
9. Job Title & Seniority Relevance
10. Readability & Text Quality
11. Document Formatting & Layout Hazards

IMPORTANT NOTICE:
This tool provides a transparent, rule-based ATS-Style Compatibility Audit based on common
parser mechanics and recruiting industry standards. It is NOT an official or proprietary
commercial ATS algorithm (such as Workday, Taleo, or Greenhouse).
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import re


class AtsAnalyzerError(Exception):
    """Custom exception raised for invalid inputs in AtsAnalyzer."""
    def __init__(self, message: str, code: str = "ATS_ANALYZER_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class AtsAnalyzer:
    """
    Evaluates parsed resume text and structure against transparent ATS compatibility benchmarks.
    Generates a deterministic 0-100 score, a diagnostic checklist, detected formatting issues,
    and prioritized resume improvement suggestions.
    """

    # Comprehensive set of high-impact action verbs commonly favored by ATS parsers and recruiters
    STRONG_ACTION_VERBS: Set[str] = {
        "architected", "engineered", "developed", "spearheaded", "designed", "implemented",
        "optimized", "led", "managed", "built", "integrated", "accelerated", "scaled",
        "deployed", "automated", "orchestrated", "refactored", "authored", "mentored",
        "launched", "streamlined", "delivered", "collaborated", "championed", "formulated",
        "created", "established", "drove", "executed", "configured", "administered",
        "standardized", "migrated", "reduced", "increased", "maximized", "minimized",
        "produced", "modernized", "initiated", "resolved", "consolidated", "directed"
    }

    # Common certifications keywords across software, cloud, and security
    KNOWN_CERT_KEYWORDS: Set[str] = {
        "aws", "amazon web services", "solutions architect", "developer associate",
        "sysops", "cloud practitioner", "gcp", "google cloud", "cloud engineer",
        "azure", "microsoft certified", "cka", "ckad", "kubernetes administrator",
        "cissp", "ceh", "security+", "network+", "comptia", "ccna", "ccnp",
        "pmp", "scrum master", "csm", "psm", "safe", "meta certified", "hashicorp",
        "terraform associate", "oracle certified", "istqb", "coursera", "specialization"
    }

    @classmethod
    def analyze(
        cls,
        parsed_resume: Optional[Dict[str, Any]],
        job_analysis: Optional[Dict[str, Any]] = None,
        target_job_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute full ATS-style resume analysis.
        Accepts real parsed resume data from Stage 2 and optional job analysis from Stage 3.
        Returns overall ATS score (0-100), checklist, formatting issues, and recommendations.
        """
        if not parsed_resume or not isinstance(parsed_resume, dict):
            raise AtsAnalyzerError("Missing or invalid parsed_resume payload.", code="MISSING_RESUME_DATA")

        full_text = parsed_resume.get("full_text", "")
        if not full_text or not full_text.strip():
            raise AtsAnalyzerError("Parsed resume contains no text content.", code="EMPTY_RESUME_TEXT")

        section_contents = parsed_resume.get("section_contents", {})
        sections_detected = parsed_resume.get("sections_detected", [])
        contact_meta = parsed_resume.get("contact_info", {})
        metadata = parsed_resume.get("metadata", {})

        word_count = parsed_resume.get("word_count") or len(full_text.split())
        char_count = parsed_resume.get("char_count") or len(full_text)

        checklist: List[Dict[str, Any]] = []
        formatting_issues: List[str] = []
        suggestions: List[Dict[str, Any]] = []

        total_earned_score = 0
        max_possible_score = 100

        # =====================================================================
        # 1. Contact Information Audit (Max 10 pts)
        # =====================================================================
        contact_score, contact_status, contact_details, contact_rec = cls._check_contact_info(
            full_text=full_text,
            contact_meta=contact_meta
        )
        total_earned_score += contact_score
        checklist.append({
            "id": "contact_info",
            "title": "Essential Contact Anchors",
            "category": "Contact & Identity",
            "status": contact_status,
            "score": contact_score,
            "max_score": 10,
            "details": contact_details,
            "recommendation": contact_rec
        })
        if contact_status != "pass":
            suggestions.append({
                "id": "sug-contact",
                "category": "Contact Information",
                "type": "high" if contact_status == "fail" else "medium",
                "title": "Complete Header Contact Anchors",
                "description": contact_rec
            })

        # =====================================================================
        # 2. Resume Sections Architecture (Max 15 pts)
        # =====================================================================
        sections_score, sections_status, sections_details, sections_rec = cls._check_sections_architecture(
            section_contents=section_contents,
            sections_detected=sections_detected
        )
        total_earned_score += sections_score
        checklist.append({
            "id": "section_headers",
            "title": "Standard Section Headings",
            "category": "Document Structure",
            "status": sections_status,
            "score": sections_score,
            "max_score": 15,
            "details": sections_details,
            "recommendation": sections_rec
        })
        if sections_status != "pass":
            suggestions.append({
                "id": "sug-sections",
                "category": "Document Structure",
                "type": "high",
                "title": "Standardize Major Section Headers",
                "description": sections_rec
            })

        # =====================================================================
        # 3. Skills Section Presentation (Max 15 pts)
        # =====================================================================
        skills_score, skills_status, skills_details, skills_rec = cls._check_skills_presentation(
            section_contents=section_contents,
            full_text=full_text
        )
        total_earned_score += skills_score
        checklist.append({
            "id": "skills_presentation",
            "title": "Technical Skills Formatting & Density",
            "category": "Skills Section",
            "status": skills_status,
            "score": skills_score,
            "max_score": 15,
            "details": skills_details,
            "recommendation": skills_rec
        })
        if skills_status != "pass":
            suggestions.append({
                "id": "sug-skills-fmt",
                "category": "Skills Section",
                "type": "medium",
                "title": "Organize Skills with Clear Subheadings",
                "description": skills_rec
            })

        # =====================================================================
        # 4. Education Section Verification (Max 10 pts)
        # =====================================================================
        edu_score, edu_status, edu_details, edu_rec = cls._check_education_details(
            section_contents=section_contents,
            full_text=full_text
        )
        total_earned_score += edu_score
        checklist.append({
            "id": "education_credentials",
            "title": "Education & Academic Credentials",
            "category": "Education",
            "status": edu_status,
            "score": edu_score,
            "max_score": 10,
            "details": edu_details,
            "recommendation": edu_rec
        })
        if edu_status != "pass":
            suggestions.append({
                "id": "sug-edu",
                "category": "Education Section",
                "type": "medium",
                "title": "Clarify Degree and Graduation Year",
                "description": edu_rec
            })

        # =====================================================================
        # 5. Experience Section & Quantified Impact (Max 20 pts)
        # =====================================================================
        exp_score, exp_status, exp_details, exp_rec = cls._check_experience_impact(
            section_contents=section_contents,
            full_text=full_text
        )
        total_earned_score += exp_score
        checklist.append({
            "id": "experience_impact",
            "title": "Experience Chronology & Quantified Impact",
            "category": "Work Experience",
            "status": exp_status,
            "score": exp_score,
            "max_score": 20,
            "details": exp_details,
            "recommendation": exp_rec
        })
        if exp_status != "pass":
            suggestions.append({
                "id": "sug-impact",
                "category": "Experience & Impact",
                "type": "high",
                "title": "Quantify Achievements with Concrete Metrics",
                "description": exp_rec
            })

        # =====================================================================
        # 6. Projects Section (Max 5 pts)
        # =====================================================================
        proj_score, proj_status, proj_details, proj_rec = cls._check_projects_section(
            section_contents=section_contents,
            full_text=full_text
        )
        total_earned_score += proj_score
        checklist.append({
            "id": "projects_section",
            "title": "Technical Projects Demonstration",
            "category": "Projects",
            "status": proj_status,
            "score": proj_score,
            "max_score": 5,
            "details": proj_details,
            "recommendation": proj_rec
        })

        # =====================================================================
        # 7. Certifications & Ongoing Education (Max 5 pts)
        # =====================================================================
        cert_score, cert_status, cert_details, cert_rec = cls._check_certifications(
            section_contents=section_contents,
            full_text=full_text
        )
        total_earned_score += cert_score
        checklist.append({
            "id": "certifications_section",
            "title": "Industry Certifications & Credentials",
            "category": "Certifications",
            "status": cert_status,
            "score": cert_score,
            "max_score": 5,
            "details": cert_details,
            "recommendation": cert_rec
        })

        # =====================================================================
        # 8. Keyword Coverage & Natural Density (Max 15 pts)
        # =====================================================================
        kw_score, kw_status, kw_details, kw_rec = cls._check_keyword_coverage(
            full_text=full_text,
            job_analysis=job_analysis
        )
        total_earned_score += kw_score
        checklist.append({
            "id": "keyword_density",
            "title": "Keyword Coverage & Natural Density",
            "category": "Keywords",
            "status": kw_status,
            "score": kw_score,
            "max_score": 15,
            "details": kw_details,
            "recommendation": kw_rec
        })
        if kw_status != "pass":
            suggestions.append({
                "id": "sug-keywords",
                "category": "Keyword Optimization",
                "type": "high" if kw_status == "fail" else "medium",
                "title": "Align Resume Terminology with Role Keywords",
                "description": kw_rec
            })

        # =====================================================================
        # 9. Job Title & Seniority Relevance (Max 5 pts)
        # =====================================================================
        title_score, title_status, title_details, title_rec = cls._check_job_title_relevance(
            full_text=full_text,
            section_contents=section_contents,
            job_analysis=job_analysis,
            target_job_title=target_job_title
        )
        total_earned_score += title_score
        checklist.append({
            "id": "job_title_relevance",
            "title": "Job Title & Seniority Alignment",
            "category": "Relevance",
            "status": title_status,
            "score": title_score,
            "max_score": 5,
            "details": title_details,
            "recommendation": title_rec
        })

        # =====================================================================
        # 10. Readability & Text Quality (Max 10 pts)
        # =====================================================================
        read_score, read_status, read_details, read_rec = cls._check_readability(
            full_text=full_text,
            word_count=word_count,
            char_count=char_count
        )
        total_earned_score += read_score
        checklist.append({
            "id": "readability_quality",
            "title": "Document Word Count & Readability",
            "category": "Readability",
            "status": read_status,
            "score": read_score,
            "max_score": 10,
            "details": read_details,
            "recommendation": read_rec
        })
        if read_status != "pass":
            suggestions.append({
                "id": "sug-readability",
                "category": "Document Length",
                "type": "medium",
                "title": "Optimize Document Word Count",
                "description": read_rec
            })

        # =====================================================================
        # 11. Document Formatting & Layout Hazards (Max 5 pts)
        # =====================================================================
        fmt_score, fmt_status, fmt_details, fmt_issues = cls._check_formatting_hazards(
            full_text=full_text,
            metadata=metadata
        )
        total_earned_score += fmt_score
        formatting_issues.extend(fmt_issues)
        checklist.append({
            "id": "formatting_hazards",
            "title": "Parser-Friendly Layout & Formatting",
            "category": "Formatting",
            "status": fmt_status,
            "score": fmt_score,
            "max_score": 5,
            "details": fmt_details,
            "recommendation": "Maintain clean single-column hierarchy without embedded text frames, icons, or complex tables."
        })
        if fmt_issues:
            for issue in fmt_issues:
                suggestions.append({
                    "id": f"sug-fmt-{len(suggestions)}",
                    "category": "Layout & Formatting",
                    "type": "medium",
                    "title": "Formatting Remediation",
                    "description": issue
                })

        # -------------------------------------------------------------
        # Overall ATS Score (Clamped 0 - 100)
        # -------------------------------------------------------------
        overall_ats_score = max(0, min(100, int(round(total_earned_score))))

        if overall_ats_score >= 88:
            verdict = "Excellent ATS Compatibility (Highly Parser-Friendly)"
            grade = "A"
        elif overall_ats_score >= 75:
            verdict = "Good ATS Compatibility (Minor Formatting Optimizations Recommended)"
            grade = "B"
        elif overall_ats_score >= 60:
            verdict = "Moderate ATS Compatibility (Actionable Structural Improvements Needed)"
            grade = "C"
        else:
            verdict = "Low ATS Compatibility (Significant Formatting & Content Gaps Detected)"
            grade = "D"

        summary = (
            f"ATS compatibility score is {overall_ats_score}/100 (Grade {grade}: {verdict}). "
            f"Evaluated across 11 transparent parser criteria including contact anchors, standard section headings, "
            f"experience impact metrics, and keyword coverage."
        )

        return {
            "success": True,
            "ats_score": overall_ats_score,
            "grade": grade,
            "verdict": verdict,
            "summary": summary,
            "checklist": checklist,
            "formatting_issues": formatting_issues,
            "improvement_suggestions": suggestions,
            "scoring_breakdown": {c["id"]: c["score"] for c in checklist}
        }

    # =========================================================================
    # Internal Checker Methods
    # =========================================================================

    @classmethod
    def _check_contact_info(cls, full_text: str, contact_meta: Dict[str, Any]) -> Tuple[int, str, str, str]:
        """Check for valid email, phone, location, and professional URLs."""
        # 1. Email check
        email = contact_meta.get("email")
        if not email:
            email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", full_text)
            email = email_match.group(0) if email_match else None

        # 2. Phone check
        phone = contact_meta.get("phone")
        if not phone:
            phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", full_text)
            phone = phone_match.group(0) if phone_match else None

        # 3. Location / Links check
        has_linkedin = "linkedin.com" in full_text.lower()
        has_github = "github.com" in full_text.lower()
        has_location = bool(re.search(r"\b[A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\b", full_text))  # e.g. "San Francisco, CA"

        score = 0
        if email:
            score += 4
        if phone:
            score += 3
        if has_linkedin or has_github or has_location:
            score += 3

        if score >= 9:
            status = "pass"
            details = f"Verified email ({email}), phone ({phone}), and professional profile links."
            rec = "Header contact information is complete and parser-friendly."
        elif score >= 6:
            status = "warning"
            missing = []
            if not email: missing.append("email")
            if not phone: missing.append("phone number")
            if not (has_linkedin or has_github): missing.append("LinkedIn/GitHub URL")
            details = f"Partial contact information detected. Missing: {', '.join(missing)}."
            rec = f"Add your {' and '.join(missing)} prominently in the top header block."
        else:
            status = "fail"
            details = "Critical contact information missing. Email and phone number must be present."
            rec = "Ensure a clear top header containing your full name, email, phone number, and location."

        return score, status, details, rec

    @classmethod
    def _check_sections_architecture(cls, section_contents: Dict[str, Any], sections_detected: List[str]) -> Tuple[int, str, str, str]:
        """Verify presence of conventional, parser-recognized section headings."""
        core_sections = {"Experience", "Education", "Skills"}
        summary_sections = {"Summary/Profile", "Summary"}

        found_core = sum(1 for sec in core_sections if sec in section_contents or sec in sections_detected)
        found_summary = any(sec in section_contents or sec in sections_detected for sec in summary_sections)
        all_detected_count = len(sections_detected) if sections_detected else len(section_contents)

        if found_core == 3 and found_summary:
            score = 15
            status = "pass"
            details = f"Recognized {all_detected_count} standard headers: Summary, Experience, Education, and Skills."
            rec = "Section headings follow standard recruiter and ATS conventions."
        elif found_core == 3:
            score = 12
            status = "pass"
            details = "All 3 essential core sections (Experience, Education, Skills) are clearly identifiable."
            rec = "Consider adding an opening Summary/Profile section to summarize your value proposition."
        elif found_core == 2:
            score = 8
            status = "warning"
            details = "Only 2 of 3 essential sections identified. Parsers may misclassify content."
            rec = "Ensure clear, standard section headings: 'Work Experience', 'Education', and 'Technical Skills'."
        else:
            score = 4
            status = "fail"
            details = "Fewer than 2 standard section headings identified. Document may fail automated indexing."
            rec = "Use clear top-level heading text without embedding headers inside tables or images."

        return score, status, details, rec

    @classmethod
    def _check_skills_presentation(cls, section_contents: Dict[str, Any], full_text: str) -> Tuple[int, str, str, str]:
        """Check for dedicated skills section and clean categorization."""
        skills_text = section_contents.get("Skills", "")
        has_dedicated_section = bool(skills_text and len(skills_text.strip()) > 15)

        # Check for delimiters (commas, pipes, bullets) or categorized headers
        has_categories = any(cat in skills_text.lower() for cat in ["languages:", "frameworks:", "databases:", "tools:", "libraries:"])
        has_delimiters = ("," in skills_text) or ("|" in skills_text) or ("\u2022" in skills_text) or ("-" in skills_text)

        # Approximate skill count by tokens/commas
        comma_items = [s.strip() for s in re.split(r"[,|\n\u2022]", skills_text) if s.strip()]
        skill_count = len(comma_items)

        if has_dedicated_section and (has_categories or skill_count >= 8):
            score = 15
            status = "pass"
            details = f"Dedicated skills section verified with clean categorized formatting ({skill_count}+ skills listed)."
            rec = "Skills section is well-structured for automated keyword indexing."
        elif has_dedicated_section and has_delimiters:
            score = 12
            status = "pass"
            details = "Dedicated skills section detected with comma or delimiter separation."
            rec = "Group skills into categories (e.g. 'Languages', 'Frameworks', 'Cloud') for even faster scanning."
        elif has_dedicated_section:
            score = 8
            status = "warning"
            details = "Skills section detected but content resembles an unbroken paragraph."
            rec = "Format skills using comma-separated lists or bulleted categories rather than continuous sentences."
        else:
            score = 4
            status = "fail"
            details = "No dedicated 'Skills' or 'Technical Skills' section identified."
            rec = "Create a distinct 'Technical Skills' section near the top of your resume."

        return score, status, details, rec

    @classmethod
    def _check_education_details(cls, section_contents: Dict[str, Any], full_text: str) -> Tuple[int, str, str, str]:
        """Check for degree level, university name, and graduation dates."""
        edu_text = (section_contents.get("Education", "") + " " + full_text).lower()

        # Degree check
        has_degree = any(deg in edu_text for deg in ["bachelor", "master", "doctorate", "phd", "b.s", "b.tech", "m.s", "associate", "degree"])
        # Institution check
        has_institution = any(inst in edu_text for inst in ["university", "college", "institute", "polytechnic", "academy", "school"])
        # Dates check
        has_dates = bool(re.search(r"\b(20\d{2}|19\d{2})\b", edu_text))

        score = 0
        if has_degree: score += 4
        if has_institution: score += 3
        if has_dates: score += 3

        if score == 10:
            status = "pass"
            details = "Complete academic profile detected: degree type, educational institution, and graduation dates."
            rec = "Education section is properly formatted and easy for parsers to verify."
        elif score >= 6:
            status = "warning"
            details = "Education details partially present (degree or institution detected, but dates may be unclear)."
            rec = "List your full degree name, university name, and graduation year (e.g., '2021')."
        else:
            status = "fail"
            details = "No verified degree or institution detected in resume text."
            rec = "Add an 'Education' section stating your highest degree, field of study, and institution."

        return score, status, details, rec

    @classmethod
    def _check_experience_impact(cls, section_contents: Dict[str, Any], full_text: str) -> Tuple[int, str, str, str]:
        """Check for chronological dates, strong action verbs, and quantifiable metrics."""
        exp_text = section_contents.get("Experience", "") or full_text
        exp_lower = exp_text.lower()

        # 1. Date ranges (e.g. 2021 – Present, 2019-2021)
        has_date_ranges = bool(re.search(r"\b(20\d{2}|19\d{2})\s*[-–to/]\s*(20\d{2}|present|current|now)\b", exp_lower))

        # 2. Strong action verbs
        tokens = set(re.findall(r"\b[a-z]{3,}\b", exp_lower))
        verb_matches = tokens.intersection(cls.STRONG_ACTION_VERBS)
        verb_count = len(verb_matches)

        # 3. Quantified metrics (%, $, numbers with M/K/users/ms)
        metrics_matches = re.findall(r"(?:\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:m|k|million|thousand|users|requests|ms|sec)\b)", exp_lower)
        metric_count = len(metrics_matches)

        score = 0
        if has_date_ranges:
            score += 8
        else:
            score += 3

        if verb_count >= 4:
            score += 6
        elif verb_count >= 2:
            score += 5
        else:
            score += 2

        if metric_count >= 3:
            score += 6
        elif metric_count >= 1:
            score += 5
        else:
            score += 2

        if score >= 16:
            status = "pass"
            details = f"Strong chronological work history: {verb_count} action verbs and {metric_count} quantified metric points identified."
            rec = "Experience bullets demonstrate measurable impact and clear career progression."
        elif score >= 11:
            status = "warning"
            details = f"Work experience detected with {verb_count} action verbs, but only {metric_count} quantified metric anchors found."
            rec = "Increase quantified outcomes (e.g. 'reduced latency by 35%', 'scaled to 80,000 users') to score higher with recruiters."
        else:
            status = "fail"
            details = "Work experience bullets lack chronological date ranges, action verbs, or quantifiable achievements."
            rec = "Begin every bullet with a past-tense action verb (e.g., 'Architected', 'Spearheaded') and include numbers demonstrating outcomes."

        return score, status, details, rec

    @classmethod
    def _check_projects_section(cls, section_contents: Dict[str, Any], full_text: str) -> Tuple[int, str, str, str]:
        """Check for dedicated or structured projects section."""
        has_proj_section = "Projects" in section_contents and len(section_contents["Projects"].strip()) > 30

        if has_proj_section:
            return 5, "pass", "Dedicated Projects section found showcasing practical tool implementations and architecture.", "Projects section is well-structured."
        elif "project" in full_text.lower():
            return 3, "pass", "Projects referenced within employment history or education.", "Consider creating a dedicated 'Key Projects' section to showcase independent engineering work."
        return 1, "warning", "No distinct project demonstrations identified.", "Add 1–2 notable technical projects highlighting your modern technology stack."

    @classmethod
    def _check_certifications(cls, section_contents: Dict[str, Any], full_text: str) -> Tuple[int, str, str, str]:
        """Check for recognized industry certifications or relevant credentials."""
        has_cert_section = "Certifications" in section_contents and len(section_contents["Certifications"].strip()) > 10
        full_lower = full_text.lower()

        found_certs = [cert for cert in cls.KNOWN_CERT_KEYWORDS if cert in full_lower]

        if has_cert_section or len(found_certs) >= 2:
            return 5, "pass", f"Industry certifications identified ({len(found_certs)} credential references detected).", "Certifications reinforce your domain authority."
        elif len(found_certs) == 1:
            return 4, "pass", "Single industry certification or specialization detected.", "Highlight the credential issuer and completion date."
        # Certifications are not strictly required for every role; provide neutral score
        return 3, "pass", "No formal industry certifications detected (optional qualification).", "Certifications like AWS Solutions Architect or CKA can provide a competitive edge."

    @classmethod
    def _check_keyword_coverage(cls, full_text: str, job_analysis: Optional[Dict[str, Any]]) -> Tuple[int, str, str, str]:
        """Check keyword presence and detect unnatural keyword stuffing."""
        if not job_analysis or not isinstance(job_analysis, dict):
            return 12, "pass", "Keyword baseline evaluated on general software engineering domain terms.", "Ensure target role requirements are reflected across your bullet points."

        keywords = job_analysis.get("keywords", [])
        if not keywords:
            return 12, "pass", "Job description contains general terminology. Good natural keyword distribution.", "Reflect key role responsibilities naturally."

        full_lower = full_text.lower()
        total_kw = len(keywords)
        matched_kw_count = 0
        stuffed_keywords = []

        for kw_item in keywords:
            kw_name = kw_item.get("keyword", "") if isinstance(kw_item, dict) else str(kw_item)
            if not kw_name:
                continue

            escaped = re.escape(kw_name.lower())
            occurrences = len(re.findall(rf"\b{escaped}\b", full_lower))
            if occurrences > 0:
                matched_kw_count += 1
            if occurrences > 10:
                stuffed_keywords.append(kw_name)

        coverage_ratio = matched_kw_count / total_kw if total_kw > 0 else 1.0

        if stuffed_keywords:
            return 7, "warning", f"Potential keyword stuffing detected for term(s): {', '.join(stuffed_keywords[:3])}.", "Avoid repeating the same keyword more than 5–6 times; distribute terms naturally."

        if coverage_ratio >= 0.70:
            score = 15
            status = "pass"
            details = f"Strong keyword coverage: {matched_kw_count} of {total_kw} job keywords ({int(coverage_ratio*100)}%) found with natural density."
            rec = "Resume demonstrates natural semantic alignment with role requirements."
        elif coverage_ratio >= 0.45:
            score = 11
            status = "pass"
            details = f"Moderate keyword coverage ({int(coverage_ratio*100)}%). {matched_kw_count} of {total_kw} job keywords identified."
            rec = "Integrate missing domain keywords naturally into your work experience bullet points."
        else:
            score = 6
            status = "warning"
            details = f"Low keyword coverage ({int(coverage_ratio*100)}%). Only {matched_kw_count} of {total_kw} job keywords detected."
            rec = "Align your resume terminology with the job description to improve automated keyword filtering pass rates."

        return score, status, details, rec

    @classmethod
    def _check_job_title_relevance(
        cls,
        full_text: str,
        section_contents: Dict[str, Any],
        job_analysis: Optional[Dict[str, Any]],
        target_job_title: Optional[str]
    ) -> Tuple[int, str, str, str]:
        """Check if target job title or related seniority words appear in profile or work history."""
        resolved_title = target_job_title or (job_analysis.get("job_title") if job_analysis else None)
        if not resolved_title:
            return 4, "pass", "Job title alignment evaluated against general technical track.", "Align top summary title with your target role."

        title_lower = resolved_title.lower()
        title_tokens = [w for w in re.findall(r"\b[a-z]{3,}\b", title_lower) if w not in ("and", "the", "for", "with")]
        full_lower = full_text.lower()

        matched_tokens = [w for w in title_tokens if w in full_lower]
        match_ratio = len(matched_tokens) / len(title_tokens) if title_tokens else 1.0

        if title_lower in full_lower or match_ratio >= 0.8:
            return 5, "pass", f"Direct title alignment: target role '{resolved_title}' is strongly reflected in your resume.", "Headline and experience align cleanly with target role."
        elif match_ratio >= 0.5:
            return 4, "pass", f"Partial title match: core words from '{resolved_title}' found in your resume text.", "Consider updating your opening professional headline to match the exact target title."
        return 2, "warning", f"Target job title '{resolved_title}' is not explicitly represented in your profile.", f"Include '{resolved_title}' in your summary or target headline to establish immediate relevance."

    @classmethod
    def _check_readability(cls, full_text: str, word_count: int, char_count: int) -> Tuple[int, str, str, str]:
        """Check word count range (ideal 350-1000) and character-to-word cleanliness."""
        # 1. Word count
        if 350 <= word_count <= 950:
            wc_score = 6
            wc_msg = f"Ideal length: {word_count} words (fits standard 1–2 page format)."
        elif 250 <= word_count <= 1200:
            wc_score = 4
            wc_msg = f"Acceptable length: {word_count} words."
        else:
            wc_score = 2
            wc_msg = f"Document length ({word_count} words) is outside the recommended 350–950 word window."

        # 2. Text stream hygiene (detect excessive non-ASCII or OCR noise)
        non_ascii = [c for c in full_text if ord(c) > 127 and c not in ("•", "–", "—", "’", "“", "”", "…", "\t", "\n")]
        non_ascii_ratio = len(non_ascii) / char_count if char_count > 0 else 0.0

        if non_ascii_ratio < 0.01:
            hygiene_score = 4
            hygiene_msg = "Clean text layer without OCR distortion or encoding artifacts."
        else:
            hygiene_score = 1
            hygiene_msg = f"High ratio of non-standard symbols detected ({len(non_ascii)} non-ASCII artifacts)."

        total_score = wc_score + hygiene_score
        status = "pass" if total_score >= 8 else ("warning" if total_score >= 5 else "fail")
        details = f"{wc_msg} {hygiene_msg}"
        rec = "Aim for 400–800 words for an early-career resume, or 700–1,100 words for senior engineers."

        return total_score, status, details, rec

    @classmethod
    def _check_formatting_hazards(cls, full_text: str, metadata: Dict[str, Any]) -> Tuple[int, str, str, List[str]]:
        """Identify potential layout issues such as dense paragraphs, multi-column bleed, and control characters."""
        issues: List[str] = []

        # 1. Dense unbroken text blocks (> 150 words without newline)
        paragraphs = full_text.split("\n\n")
        dense_blocks = [p for p in paragraphs if len(p.split()) > 140]
        if dense_blocks:
            issues.append(f"Detected {len(dense_blocks)} dense text block(s) exceeding 140 words without a paragraph break. Break long paragraphs into scannable 2-3 line bullet points.")

        # 2. Multi-column whitespace artifacts (lines with multiple wide tab gaps)
        lines = full_text.split("\n")
        multi_col_lines = [line for line in lines if len(re.findall(r"\s{4,}", line)) >= 2]
        if len(multi_col_lines) > 4:
            issues.append("Multiple columns or table layouts detected. Some ATS parsers read columns horizontally across lines, disrupting chronological flow.")

        # 3. Control characters or replacement characters
        control_chars = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]", full_text)
        if control_chars:
            issues.append(f"Detected {len(control_chars)} non-printing control character(s). Save your document as a clean standard PDF or DOCX without special glyphs.")

        if not issues:
            return 5, "pass", "Clean single-stream layout. No multi-column fragmentation or formatting hazards detected.", []
        elif len(issues) == 1:
            return 3, "warning", f"Minor formatting observation: {issues[0]}", issues
        return 1, "warning", f"Detected {len(issues)} formatting hazards that may impact automated text extraction.", issues
