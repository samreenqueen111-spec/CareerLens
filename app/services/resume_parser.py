"""
Resume Parser Service for CareerLens AI (Stage 2).
Handles robust file validation, secure storage, text extraction from PDF and DOCX,
and rule-based detection of standard resume sections without external LLM dependencies.
"""

import io
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.utils import secure_filename

import pypdf
import docx


class ResumeParserError(Exception):
    """Custom exception class for user-facing resume parsing errors."""
    def __init__(self, message: str, code: str = "PARSING_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ResumeParser:
    """
    Production-grade resume parser supporting PDF and DOCX formats.
    Provides strict file validation, sanitization, text extraction,
    and regex-based section detection.
    """

    ALLOWED_EXTENSIONS = {"pdf", "docx"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    # Standard section definitions with regex patterns for header matching
    SECTION_PATTERNS = {
        "contact_info": {
            "label": "Contact Information",
            "regex": re.compile(
                r"^(?:contact(?:\s+information|\s+details)?|personal\s+info|get\s+in\s+touch)\b",
                re.IGNORECASE
            )
        },
        "summary": {
            "label": "Summary/Profile",
            "regex": re.compile(
                r"^(?:professional\s+summary|summary(?:\s+statement)?|profile|career\s+objective|executive\s+summary|about\s+me|overview)\b",
                re.IGNORECASE
            )
        },
        "skills": {
            "label": "Skills",
            "regex": re.compile(
                r"^(?:skills(?:\s*&amp;|\s*&|\s+and)?\s*(?:abilities|competencies|proficiencies)?|technical\s+skills|core\s+competencies|technologies|tech\s+stack|tools\s*&amp;?\s*technologies|areas\s+of\s+expertise|key\s+skills)\b",
                re.IGNORECASE
            )
        },
        "experience": {
            "label": "Experience",
            "regex": re.compile(
                r"^(?:(?:work|professional|relevant|career)\s+experience|employment\s+history|experience|work\s+history|internships?)\b",
                re.IGNORECASE
            )
        },
        "education": {
            "label": "Education",
            "regex": re.compile(
                r"^(?:education(?:\s+and\s+credentials)?|academic\s+background|academic\s+history|educational\s+qualifications|degrees?|studies)\b",
                re.IGNORECASE
            )
        },
        "projects": {
            "label": "Projects",
            "regex": re.compile(
                r"^(?:(?:personal|academic|key|selected|featured|software)\s+projects|projects(?:\s+portfolio)?|portfolio)\b",
                re.IGNORECASE
            )
        },
        "certifications": {
            "label": "Certifications",
            "regex": re.compile(
                r"^(?:certifications?|licenses?(?:\s+and\s+certifications)?|accreditations?|courses?(?:\s*&amp;|\s*&)?\s*certifications?|professional\s+certifications?)\b",
                re.IGNORECASE
            )
        },
        "achievements": {
            "label": "Achievements",
            "regex": re.compile(
                r"^(?:(?:key\s+)?achievements|honors?(?:\s*&amp;|\s*&)?\s*awards?|awards?(?:\s*&amp;|\s*&)?\s*honors?|accomplishments|publications?|fellowships?)\b",
                re.IGNORECASE
            )
        }
    }

    # Auxiliary Contact Data Extractors
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b")
    URL_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:linkedin\.com\/in\/[A-Za-z0-9_-]+|github\.com\/[A-Za-z0-9_-]+|[A-Za-z0-9_-]+\.(?:dev|io|me|org|com))", re.IGNORECASE)

    @classmethod
    def validate_file(cls, filename: str, file_size_bytes: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate file format and size limits.
        Returns: (is_valid, extension, error_message)
        """
        if not filename or "." not in filename:
            return False, None, "No file selected or file name has no valid extension."

        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, ext, f"Unsupported file format (.{ext}). Please upload a PDF (.pdf) or Word document (.docx)."

        if file_size_bytes == 0:
            return False, ext, "The uploaded file is empty (0 bytes). Please upload a valid resume."

        if file_size_bytes > cls.MAX_FILE_SIZE:
            size_mb = file_size_bytes / (1024 * 1024)
            return False, ext, f"File exceeds maximum allowed size of 5.0 MB (Uploaded: {size_mb:.1f} MB)."

        return True, ext, None

    @classmethod
    def save_secure_upload(cls, file_storage, upload_dir: Path) -> Path:
        """
        Safely store uploaded file in non-public uploads directory with randomized name.
        Prevents directory traversal and file overwrites.
        """
        os.makedirs(upload_dir, exist_ok=True)
        raw_name = secure_filename(file_storage.filename or "resume")
        unique_prefix = uuid.uuid4().hex[:12]
        safe_name = f"{unique_prefix}_{raw_name}"
        save_path = upload_dir / safe_name
        file_storage.save(save_path)
        return save_path

    @classmethod
    def extract_text_from_pdf(cls, file_input) -> str:
        """
        Extract clean text from a PDF file stream or path using pypdf.
        Handles encryption checks, page iterations, and malformed streams.
        """
        try:
            reader = pypdf.PdfReader(file_input)
            
            if reader.is_encrypted:
                raise ResumeParserError(
                    "The uploaded PDF is password protected. Please remove password encryption and retry.",
                    code="PDF_ENCRYPTED"
                )

            if len(reader.pages) == 0:
                raise ResumeParserError(
                    "The PDF file contains no readable pages.",
                    code="EMPTY_DOCUMENT"
                )

            extracted_pages: List[str] = []
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        extracted_pages.append(page_text.strip())
                except Exception as page_err:
                    # Continue extracting other pages if one page encounters non-fatal font decode issues
                    continue

            full_text = "\n\n".join(extracted_pages).strip()

            if not full_text:
                raise ResumeParserError(
                    "No extractable text found in PDF. The document may be a scanned image or empty. Please upload a machine-readable text PDF.",
                    code="NO_TEXT_FOUND"
                )

            return full_text

        except ResumeParserError:
            raise
        except pypdf.errors.PdfReadError as pdf_err:
            raise ResumeParserError(
                f"Invalid or corrupted PDF file: {str(pdf_err)}",
                code="INVALID_PDF"
            )
        except Exception as e:
            raise ResumeParserError(
                f"Failed to extract text from PDF: {str(e)}",
                code="PARSING_FAILED"
            )

    @classmethod
    def extract_text_from_docx(cls, file_input) -> str:
        """
        Extract clean text from a DOCX document using python-docx.
        Extracts both regular paragraphs and table cells.
        """
        try:
            doc = docx.Document(file_input)
            text_blocks: List[str] = []

            # 1. Extract paragraphs
            for para in doc.paragraphs:
                cleaned = para.text.strip()
                if cleaned:
                    text_blocks.append(cleaned)

            # 2. Extract tables (resumes often place skills or education inside tables)
            for table in doc.tables:
                for row in table.rows:
                    row_texts = []
                    for cell in row.cells:
                        c_text = cell.text.strip()
                        if c_text and c_text not in row_texts:
                            row_texts.append(c_text)
                    if row_texts:
                        text_blocks.append(" | ".join(row_texts))

            full_text = "\n\n".join(text_blocks).strip()

            if not full_text:
                raise ResumeParserError(
                    "The DOCX document contains no readable text. Please check the document contents.",
                    code="NO_TEXT_FOUND"
                )

            return full_text

        except ResumeParserError:
            raise
        except Exception as docx_err:
            err_msg = str(docx_err)
            if "Package not found" in err_msg or "file is not a zip file" in err_msg.lower():
                raise ResumeParserError(
                    "Invalid DOCX file. The uploaded document is not a valid Microsoft Word archive.",
                    code="INVALID_DOCX"
                )
            raise ResumeParserError(
                f"Failed to extract text from DOCX: {err_msg}",
                code="PARSING_FAILED"
            )

    @classmethod
    def detect_sections(cls, raw_text: str) -> Dict[str, Any]:
        """
        Identify common resume sections using regex-based heading detection.
        Returns:
            {
                'detected_sections': List[str],      # Human-friendly labels
                'detected_keys': List[str],          # Machine keys
                'missing_sections': List[str],
                'sections_count': int,
                'total_expected': int,               # 8
                'section_contents': Dict[str, str],  # Extracted text for each section
                'contact_details': Dict[str, Any]    # Emails, phones, links
            }
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        # Track detected headers and line indices
        header_matches: List[Tuple[int, str, str]] = [] # (line_index, section_key, label)

        for idx, line in enumerate(lines):
            # Heading lines are typically short (< 60 chars)
            clean_line = re.sub(r"[:\-_#=*]+$", "", line).strip()
            if len(clean_line) > 55 or len(clean_line) < 3:
                continue

            for key, meta in cls.SECTION_PATTERNS.items():
                if meta["regex"].match(clean_line):
                    # Check we don't duplicate the same section consecutively
                    if not header_matches or header_matches[-1][1] != key:
                        header_matches.append((idx, key, meta["label"]))
                    break

        # Segment text between headers
        section_contents: Dict[str, str] = {}
        for i, (start_idx, key, label) in enumerate(header_matches):
            end_idx = header_matches[i + 1][0] if i + 1 < len(header_matches) else len(lines)
            content_lines = lines[start_idx + 1:end_idx]
            section_contents[label] = "\n".join(content_lines).strip()

        # Extract contact anchors (email, phone, URLs)
        emails = list(set(cls.EMAIL_REGEX.findall(raw_text)))
        phones = list(set(cls.PHONE_REGEX.findall(raw_text)))
        # Filter phone numbers that are too short to be real phone numbers
        phones = [p for p in phones if len(re.sub(r"\D", "", p)) >= 10]
        urls = list(set(cls.URL_REGEX.findall(raw_text)))

        # If emails or phones are found, ensure Contact Information is marked detected
        contact_detected = "Contact Information" in section_contents or len(emails) > 0 or len(phones) > 0
        
        detected_labels = list(section_contents.keys())
        if contact_detected and "Contact Information" not in detected_labels:
            detected_labels.insert(0, "Contact Information")
            contact_snippet = []
            if emails: contact_snippet.append(f"Email: {', '.join(emails)}")
            if phones: contact_snippet.append(f"Phone: {', '.join(phones)}")
            if urls: contact_snippet.append(f"Links: {', '.join(urls)}")
            section_contents["Contact Information"] = "\n".join(contact_snippet)

        all_target_labels = [meta["label"] for meta in cls.SECTION_PATTERNS.values()]
        missing_labels = [label for label in all_target_labels if label not in detected_labels]

        return {
            "detected_sections": detected_labels,
            "missing_sections": missing_labels,
            "sections_count": len(detected_labels),
            "total_expected": len(all_target_labels),
            "section_contents": section_contents,
            "contact_details": {
                "emails": emails,
                "phones": phones,
                "links": urls
            }
        }

    @classmethod
    def parse_document(cls, file_stream_or_path, filename: str, file_size_bytes: int = 0) -> Dict[str, Any]:
        """
        Complete parsing orchestrator:
        1. Validates format and size
        2. Extracts raw text stream
        3. Normalizes and computes word/char counts
        4. Detects standard resume sections
        5. Returns structured report
        """
        is_valid, ext, err_msg = cls.validate_file(filename, file_size_bytes)
        if not is_valid:
            raise ResumeParserError(err_msg, code="VALIDATION_FAILED")

        # Extract text based on file format
        if ext == "pdf":
            raw_text = cls.extract_text_from_pdf(file_stream_or_path)
            file_type_label = "PDF Document"
        elif ext == "docx":
            raw_text = cls.extract_text_from_docx(file_stream_or_path)
            file_type_label = "Microsoft Word (DOCX)"
        else:
            raise ResumeParserError(f"Unsupported extension: {ext}", code="UNSUPPORTED_FORMAT")

        # Normalization and counting
        words = raw_text.split()
        word_count = len(words)
        char_count = len(raw_text)
        lines = [l for l in raw_text.splitlines() if l.strip()]
        line_count = len(lines)

        # Detect common sections
        sections_data = cls.detect_sections(raw_text)

        # Preview snippet (first 600 characters cleanly truncated)
        preview_text = raw_text[:600] + ("..." if len(raw_text) > 600 else "")

        return {
            "success": True,
            "filename": filename,
            "file_type": file_type_label,
            "extension": ext,
            "file_size_bytes": file_size_bytes,
            "file_size_kb": round(file_size_bytes / 1024, 1) if file_size_bytes else None,
            "char_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "preview_text": preview_text,
            "full_text": raw_text,
            "sections": sections_data["detected_sections"],
            "missing_sections": sections_data["missing_sections"],
            "sections_count": sections_data["sections_count"],
            "total_expected_sections": sections_data["total_expected"],
            "section_contents": sections_data["section_contents"],
            "contact_details": sections_data["contact_details"],
            "message": f"Successfully parsed {file_type_label} '{filename}' ({word_count:,} words, {sections_data['sections_count']} sections identified)."
        }
