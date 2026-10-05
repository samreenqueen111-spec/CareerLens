"""
Job Description Analyzer Service for CareerLens (Stage 3).
Performs pure-Python text extraction to extract and categorize:
- Required technical skills
- Preferred / nice-to-have technical skills
- Soft skills
- Education requirements
- Experience requirements
- Important job-specific keywords
Without external LLMs or embedding models.
"""

import re
from typing import Dict, Any, List, Set, Tuple, Optional
from collections import Counter


class JobAnalyzerError(Exception):
    """Custom exception for Job Description Analyzer errors."""
    def __init__(self, message: str, code: str = "INVALID_JOB_DESCRIPTION"):
        super().__init__(message)
        self.message = message
        self.code = code


class JobAnalyzer:
    """
    Production-grade text processing engine for analyzing Job Descriptions.
    Extracts structured requirements using rule-based linguistics, section
    segmentation, and domain taxonomy mapping.
    """

    MIN_CHAR_COUNT = 30
    MIN_WORD_COUNT = 8

    # --------------------------------------------------------------------------
    # Technical Skills Taxonomy: Canonical Name -> Matching Regexes / Patterns
    # --------------------------------------------------------------------------
    TECHNICAL_SKILLS_MAP = {
        # Programming Languages
        "Python": [r"\bpython(?:3)?\b"],
        "JavaScript": [r"\bjavascript\b", r"\bjs\b(?!\.)", r"\bes[6-9]\b"],
        "TypeScript": [r"\btypescript\b", r"\bts\b(?!\.)"],
        "Java": [r"\bjava\b(?!script)"],
        "C++": [r"\bc\+\+\b"],
        "C#": [r"\bc#\b", r"\bc-sharp\b"],
        "Go": [r"\bgolang\b", r"\bgo\s+language\b", r"\bgo\b(?=\s*(?:developer|engineer|backend|microservices|concurrency))"],
        "Rust": [r"\brust\b(?:\s+lang|\s+programming)?"],
        "PHP": [r"\bphp(?:\d)?\b"],
        "Ruby": [r"\bruby\b(?!(\s+on\s+rails))"],
        "Swift": [r"\bswift\b(?:\s+programming|\s+developer)?"],
        "Kotlin": [r"\bkotlin\b"],
        "Scala": [r"\bscala\b"],
        "SQL": [r"\bsql\b"],
        "HTML5 / CSS3": [r"\bhtml5?\b", r"\bcss3?\b"],
        "Bash / Shell": [r"\bbash\b", r"\bshell\s+scripting\b", r"\bzsh\b"],

        # Frameworks & Web Libraries
        "React": [r"\breact(?:\.js)?\b"],
        "React Native": [r"\breact\s+native\b"],
        "Next.js": [r"\bnext(?:\.js)?\b"],
        "Angular": [r"\bangular(?:\.js)?\b"],
        "Vue.js": [r"\bvue(?:\.js)?\b"],
        "Node.js": [r"\bnode(?:\.js)?\b"],
        "Express.js": [r"\bexpress(?:\.js)?\b"],
        "Flask": [r"\bflask\b"],
        "FastAPI": [r"\bfastapi\b"],
        "Django": [r"\bdjango\b"],
        "Spring Boot": [r"\bspring\s*boot\b", r"\bspring\s+framework\b"],
        "ASP.NET": [r"\basp\.net(?:\s+core)?\b", r"\b\.net\s+core\b"],
        "Ruby on Rails": [r"\bruby\s+on\s+rails\b", r"\brails\b"],
        "Tailwind CSS": [r"\btailwind(?:\s*css)?\b"],
        "Bootstrap": [r"\bbootstrap\b"],
        "GraphQL": [r"\bgraphql\b", r"\bapollo\b"],
        "REST APIs": [r"\brestful?\b(?:\s+apis?|\s+web\s+services)?", r"\brest\s+apis?\b"],

        # Databases & In-Memory Stores
        "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
        "MySQL": [r"\bmysql\b"],
        "MongoDB": [r"\bmongo(?:db)?\b"],
        "Redis": [r"\bredis\b"],
        "SQLite": [r"\bsqlite\b"],
        "Elasticsearch": [r"\belasticsearch\b", r"\belk\s+stack\b"],
        "Cassandra": [r"\bcassandra\b"],
        "DynamoDB": [r"\bdynamodb\b"],
        "Oracle DB": [r"\boracle(?:\s+database|\s+db)?\b"],

        # DevOps, Cloud & Containers
        "Docker": [r"\bdocker\b", r"\bcontainerization\b", r"\bcontainers?\b"],
        "Kubernetes (K8s)": [r"\bkubernetes\b", r"\bk8s\b"],
        "AWS": [r"\baws\b", r"\bamazon\s+web\s+services\b", r"\b(?:ec2|s3|lambda|eks|rds)\b"],
        "Azure": [r"\bazure\b"],
        "Google Cloud (GCP)": [r"\bgoogle\s+cloud\b", r"\bgcp\b"],
        "CI/CD": [r"\bci\s*\/\s*cd\b", r"\bcontinuous\s+integration\b"],
        "Git": [r"\bgit\b(?!\s*hub|\s*lab)", r"\bgit\s+version\s+control\b"],
        "GitHub / GitLab": [r"\bgithub\b", r"\bgitlab\b"],
        "Terraform": [r"\bterraform\b", r"\biac\b", r"\binfrastructure\s+as\s+code\b"],
        "Ansible": [r"\bansible\b"],
        "Jenkins": [r"\bjenkins\b"],
        "Linux / Unix": [r"\blinux\b", r"\bunix\b"],
        "Nginx": [r"\bnginx\b"],

        # Architecture & Messaging
        "Microservices": [r"\bmicroservices?\b", r"\bmicro-services?\b"],
        "Kafka": [r"\bapache\s+kafka\b", r"\bkafka\b"],
        "RabbitMQ": [r"\brabbitmq\b"],
        "WebSockets": [r"\bwebsockets?\b"],
        "gRPC": [r"\bgrpc\b"],
        "OAuth / JWT": [r"\boauth(?:2(?:\.0)?)?\b", r"\bjwt\b", r"\bjson\s+web\s+tokens?\b"]
    }

    # --------------------------------------------------------------------------
    # Soft Skills Taxonomy
    # --------------------------------------------------------------------------
    SOFT_SKILLS_MAP = {
        "Communication": [
            r"\bwritten\s+(?:and|&)\s+verbal\s+communication\b",
            r"\bstrong\s+communication\s+skills?\b",
            r"\bcommunication\s+skills?\b",
            r"\bpresentation\s+skills?\b"
        ],
        "Teamwork & Collaboration": [
            r"\bteam\s+player\b",
            r"\bcollaborat(?:ion|ive|e)\b",
            r"\bcross-functional\s+(?:teams?|collaboration)\b",
            r"\bteamwork\b"
        ],
        "Problem Solving": [
            r"\bproblem[\s-]solving\b",
            r"\banalytical\s+skills?\b",
            r"\bcritical\s+thinking\b",
            r"\btroubleshooting\b"
        ],
        "Leadership & Mentorship": [
            r"\bmentorship\b",
            r"\bmentor(?:ing)?\b",
            r"\bleadership\b",
            r"\bcode\s+reviews?\b",
            r"\btechnical\s+leadership\b"
        ],
        "Agile / Scrum Process": [
            r"\bagile\b",
            r"\bscrum\b",
            r"\bsprint\s+planning\b",
            r"\bkanban\b"
        ],
        "Adaptability & Ownership": [
            r"\bself[\s-]starter\b",
            r"\bself[\s-]motivated\b",
            r"\bownership\b",
            r"\bfast[\s-]paced\s+environment\b",
            r"\badaptab(?:le|ility)\b"
        ],
        "Attention to Detail": [
            r"\battention\s+to\s+detail\b",
            r"\bdetail[\s-]oriented\b"
        ]
    }

    # --------------------------------------------------------------------------
    # Section Heading Cues for Splitting Required vs Preferred
    # --------------------------------------------------------------------------
    PREFERRED_SECTION_CUES = re.compile(
        r"^(?:preferred(?:\s+qualifications|\s+requirements|\s+skills)?|"
        r"nice\s+to\s+have|bonus(?:\s+points)?|pluses|good\s+to\s+have|"
        r"desirable(?:\s+skills)?|what\s+gives\s+you\s+an\s+edge)\b",
        re.IGNORECASE
    )

    REQUIRED_SECTION_CUES = re.compile(
        r"^(?:requirements|minimum\s+qualifications|basic\s+qualifications|"
        r"what\s+you(?:\'ll)?\s+need|must\s+haves?|qualifications|role\s+requirements|"
        r"what\s+we\s+are\s+looking\s+for|what\s+you\s+bring)\b",
        re.IGNORECASE
    )

    # Inline sentence/clause cues
    PREFERRED_INLINE_PATTERNS = re.compile(
        r"\b(?:nice\s+to\s+have|bonus|preferred|plus|optional|familiarity\s+with|exposure\s+to|advantageous|a\s+plus)\b",
        re.IGNORECASE
    )

    # --------------------------------------------------------------------------
    # Education Patterns
    # --------------------------------------------------------------------------
    DEGREE_PATTERNS = [
        (
            "Bachelor's Degree",
            re.compile(
                r"\b(?:bachelor(?:\'s)?(?:\s+degree)?|b\.?s\.?|b\.?e\.?|b\.?tech\.?|undergraduate)\b(?:\s+(?:in|of)\s+[A-Za-z\s,/\-]+)?",
                re.IGNORECASE
            )
        ),
        (
            "Master's Degree",
            re.compile(
                r"\b(?:master(?:\'s)?(?:\s+degree)?|m\.?s\.?|m\.?tech\.?|postgraduate)\b(?:\s+(?:in|of)\s+[A-Za-z\s,/\-]+)?",
                re.IGNORECASE
            )
        ),
        (
            "Doctorate / Ph.D.",
            re.compile(r"\b(?:ph\.?d\.?|doctorate)\b(?:\s+(?:in|of)\s+[A-Za-z\s,/\-]+)?", re.IGNORECASE)
        ),
        (
            "Equivalent Practical Experience",
            re.compile(r"\b(?:equivalent\s+(?:practical\s+)?experience|relevant\s+work\s+experience\s+in\s+lieu\s+of\s+degree)\b", re.IGNORECASE)
        )
    ]

    FIELD_OF_STUDY_PATTERNS = re.compile(
        r"\b(?:computer\s+science|software\s+engineering|information\s+technology|"
        r"electrical\s+engineering|computer\s+engineering|data\s+science|"
        r"mathematics|statistics|quantitative\s+field|stem\s+field)\b",
        re.IGNORECASE
    )

    # --------------------------------------------------------------------------
    # Experience Patterns
    # --------------------------------------------------------------------------
    EXPERIENCE_PATTERNS = [
        # E.g. "4+ years of production experience", "3-5 years experience", "minimum 2 years"
        re.compile(
            r"(\b(?:(?:minimum|at\s+least)\s+)?(\d+(?:\s*[-–to]\s*\d+)?|\d+\+?)\s*(?:years?|yrs?)(?:\s+of)?(?:\s+[a-z\s,-]{0,35})?\s+experience\b)",
            re.IGNORECASE
        ),
        # E.g. "internship experience", "fresher", "entry level", "new grad"
        re.compile(
            r"\b(entry[\s-]level|fresher|new\s+grad(?:uate)?|internship(?:\s+experience)?|0-1\s+years?|no\s+prior\s+experience\s+required)\b",
            re.IGNORECASE
        )
    ]

    # Stop words for domain keywords extraction
    STOP_WORDS = {
        "the", "and", "or", "to", "in", "of", "a", "an", "for", "with", "is", "are", "as",
        "at", "by", "from", "on", "that", "this", "be", "have", "has", "had", "will",
        "our", "we", "you", "your", "they", "their", "team", "role", "looking", "seeking",
        "join", "work", "working", "experience", "skills", "ability", "responsibilities",
        "requirements", "about", "candidate", "candidates", "strong", "understanding",
        "knowledge", "proficient", "preferred", "must", "plus", "bonus", "years",
        "help", "build", "create", "support", "using", "like", "including", "across",
        "both", "well", "such", "new", "into", "high", "good", "other", "all", "each",
        "related", "equivalent", "environment", "field", "degree"
    }

    @classmethod
    def validate_text(cls, jd_text: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate incoming job description text before processing.
        Returns: (is_valid, error_message)
        """
        if not jd_text or not isinstance(jd_text, str):
            return False, "Job description is empty. Please enter or paste the target job description."

        cleaned = jd_text.strip()
        if len(cleaned) < cls.MIN_CHAR_COUNT:
            return (
                False,
                f"Job description is too short ({len(cleaned)} characters). Minimum requirement is {cls.MIN_CHAR_COUNT} characters."
            )

        words = cleaned.split()
        if len(words) < cls.MIN_WORD_COUNT:
            return (
                False,
                f"Job description contains only {len(words)} words. Minimum requirement is {cls.MIN_WORD_COUNT} words for meaningful analysis."
            )

        # Check that it contains actual alphabetic letters (not just symbols/numbers)
        letters_only = re.sub(r"[^A-Za-z]", "", cleaned)
        if len(letters_only) < 20:
            return False, "Job description text contains insufficient readable language content."

        return True, None

    @classmethod
    def segment_sections(cls, lines: List[str]) -> Dict[str, List[str]]:
        """
        Segment the job description into 'required', 'preferred', and 'general' buckets
        based on line headings.
        """
        sections: Dict[str, List[str]] = {
            "required": [],
            "preferred": [],
            "general": []
        }

        current_mode = "general"

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check if this line is a section header
            clean_head = re.sub(r"[:\-_*#]+$", "", line_str).strip()
            if len(clean_head) < 45:
                if cls.PREFERRED_SECTION_CUES.match(clean_head):
                    current_mode = "preferred"
                    continue
                elif cls.REQUIRED_SECTION_CUES.match(clean_head):
                    current_mode = "required"
                    continue
                elif re.match(r"^(?:about(?:\s+the\s+role|\s+us)?|responsibilities|what\s+you\s+will\s+do|overview)\b", clean_head, re.IGNORECASE):
                    current_mode = "general"
                    continue

            sections[current_mode].append(line_str)

        return sections

    @classmethod
    def extract_skills(cls, jd_text: str) -> Dict[str, List[str]]:
        """
        Identify technical and soft skills, separating required from preferred.
        """
        lines = [l.strip() for l in jd_text.splitlines() if l.strip()]
        segments = cls.segment_sections(lines)

        req_text = " ".join(segments["required"])
        pref_text = " ".join(segments["preferred"])
        gen_text = " ".join(segments["general"])
        full_text_lower = jd_text.lower()

        required_tech: Set[str] = set()
        preferred_tech: Set[str] = set()
        soft_skills: Set[str] = set()

        # 1. Technical Skills Scan
        for canonical, patterns in cls.TECHNICAL_SKILLS_MAP.items():
            compiled_list = [re.compile(p, re.IGNORECASE) for p in patterns]

            # Check if mentioned in preferred section
            is_in_pref = any(c.search(pref_text) for c in compiled_list)

            # Check if mentioned in required section or general
            is_in_req = any(c.search(req_text) for c in compiled_list)
            is_in_gen = any(c.search(gen_text) for c in compiled_list)

            if is_in_pref and not is_in_req:
                preferred_tech.add(canonical)
            elif is_in_req:
                required_tech.add(canonical)
            elif is_in_gen:
                # Check line-level sentence context for inline preferred cues
                is_preferred_inline = False
                for line in segments["general"]:
                    if any(c.search(line) for c in compiled_list):
                        if cls.PREFERRED_INLINE_PATTERNS.search(line):
                            is_preferred_inline = True
                            break

                if is_preferred_inline:
                    preferred_tech.add(canonical)
                else:
                    required_tech.add(canonical)

        # 2. Soft Skills Scan
        for canonical, patterns in cls.SOFT_SKILLS_MAP.items():
            for p in patterns:
                if re.search(p, full_text_lower):
                    soft_skills.add(canonical)
                    break

        return {
            "required_skills": sorted(list(required_tech)),
            "preferred_skills": sorted(list(preferred_tech)),
            "soft_skills": sorted(list(soft_skills))
        }

    @classmethod
    def extract_education(cls, jd_text: str) -> Dict[str, Any]:
        """
        Identify degree requirements and fields of study.
        """
        degrees_found: List[str] = []
        for deg_name, pattern in cls.DEGREE_PATTERNS:
            if pattern.search(jd_text):
                degrees_found.append(deg_name)

        fields_found: List[str] = []
        for match in cls.FIELD_OF_STUDY_PATTERNS.finditer(jd_text):
            val = match.group(0).title()
            if val not in fields_found:
                fields_found.append(val)

        # Formulate clean summary statement
        if degrees_found:
            deg_summary = degrees_found[0]
            if fields_found:
                deg_summary = f"{deg_summary} in {', '.join(fields_found)}"
        else:
            deg_summary = "Not explicitly specified (Degree or equivalent practical experience)"

        return {
            "summary": deg_summary,
            "degrees": degrees_found,
            "fields_of_study": fields_found,
            "is_specified": len(degrees_found) > 0 or len(fields_found) > 0
        }

    @classmethod
    def extract_experience(cls, jd_text: str) -> Dict[str, Any]:
        """
        Extract years of experience, level, and specific matched sentences.
        """
        matches: List[str] = []
        min_years: Optional[int] = None
        max_years: Optional[int] = None

        for pattern in cls.EXPERIENCE_PATTERNS:
            for m in pattern.finditer(jd_text):
                matched_phrase = m.group(0).strip()
                if matched_phrase not in matches:
                    matches.append(matched_phrase)

        # Extract numeric years if present
        for phrase in matches:
            num_match = re.search(r"(\d+)(?:\s*[-–to]\s*(\d+))?", phrase)
            if num_match:
                try:
                    first = int(num_match.group(1))
                    min_years = first if min_years is None else min(min_years, first)
                    if num_match.group(2):
                        second = int(num_match.group(2))
                        max_years = second if max_years is None else max(max_years, second)
                except ValueError:
                    pass

        # Determine level label
        level = "Mid / Senior Level"
        if "internship" in jd_text.lower() or "fresher" in jd_text.lower() or (min_years is not None and min_years <= 1):
            level = "Entry Level / Internship"
        elif min_years is not None and min_years >= 5:
            level = "Senior / Staff Level"
        elif min_years is not None and min_years >= 2:
            level = "Mid Level"

        summary = matches[0] if matches else "Experience level not explicitly quantified"
        # Clean up punctuation and whitespace
        summary = re.sub(r"\s+", " ", summary).strip().capitalize()

        return {
            "summary": summary,
            "level": level,
            "min_years": min_years,
            "max_years": max_years,
            "matched_phrases": matches[:3],
            "is_specified": len(matches) > 0
        }

    @classmethod
    def extract_keywords(cls, jd_text: str, top_n: int = 15) -> List[Dict[str, Any]]:
        """
        Extract key domain keywords and frequencies, excluding stopwords.
        """
        # Clean words
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]{1,24}\b", jd_text)
        
        filtered = [
            w.capitalize() for w in words
            if w.lower() not in cls.STOP_WORDS and len(w) > 2
        ]

        freq = Counter(filtered)
        top_items = freq.most_common(top_n)

        return [{"keyword": k, "frequency": c, "count": c} for k, c in top_items]

    @classmethod
    def analyze_job_description(cls, jd_text: str, job_title: str = "") -> Dict[str, Any]:
        """
        Primary analysis coordinator:
        Validates text, extracts skills, experience, education, and keywords,
        and returns clean structured result.
        """
        is_valid, err_msg = cls.validate_text(jd_text)
        if not is_valid:
            raise JobAnalyzerError(err_msg, code="VALIDATION_FAILED")

        cleaned_text = jd_text.strip()
        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)

        # 1. Skills
        skills_data = cls.extract_skills(cleaned_text)

        # 2. Education
        education_data = cls.extract_education(cleaned_text)

        # 3. Experience
        experience_data = cls.extract_experience(cleaned_text)

        # 4. Keywords
        keywords_data = cls.extract_keywords(cleaned_text, top_n=12)

        return {
            "success": True,
            "job_title": job_title.strip() if job_title else "Target Role",
            "word_count": word_count,
            "char_count": char_count,
            "required_skills": skills_data["required_skills"],
            "preferred_skills": skills_data["preferred_skills"],
            "soft_skills": skills_data["soft_skills"],
            "total_skills_count": len(skills_data["required_skills"]) + len(skills_data["preferred_skills"]) + len(skills_data["soft_skills"]),
            "education": education_data,
            "education_requirements": education_data,
            "experience": experience_data,
            "experience_requirements": experience_data,
            "keywords": keywords_data,
            "important_keywords": keywords_data,
            "message": f"Successfully analyzed job description ({word_count:,} words, {len(skills_data['required_skills'])} required skills, {len(skills_data['preferred_skills'])} preferred skills detected)."
        }
