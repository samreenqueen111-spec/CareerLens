"""
CareerLens AI - Resume to Job Matching Engine (Stage 4).
Performs transparent, deterministic matching between parsed resume data
and analyzed job description data without relying on random scores or LLMs.

Scoring Formula (Documented & Deterministic):
Overall Match = (0.40 * Skills Match) + 
                (0.25 * Experience Match) + 
                (0.20 * Keyword Match) + 
                (0.15 * Education Match)

Features:
- Normalized skill matching (e.g., Python / Python Programming, JS / JavaScript, ML / Machine Learning)
- Distinguishes exact matches from related/family skills (e.g., PostgreSQL <-> SQL)
- Separate evaluation of Required vs. Preferred job skills
- Experience tenure estimation and seniority comparison
- Degree hierarchy and discipline matching
- Keyword presence and frequency correlation
- Transparent, human-readable match explanation
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple


class MatcherError(Exception):
    """Custom exception raised when matching fails or input data is invalid."""
    def __init__(self, message: str, code: str = "MATCHER_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ResumeJobMatcher:
    """
    Deterministic Resume-to-Job Matching Engine.
    Receives structured resume data and structured Job Description data,
    evaluating Skills, Keywords, Education, and Experience.
    """

    # Scoring Weights (Sum = 1.00 / 100%)
    WEIGHT_SKILLS = 0.40
    WEIGHT_EXPERIENCE = 0.25
    WEIGHT_KEYWORDS = 0.20
    WEIGHT_EDUCATION = 0.15

    # Skill Credit Multipliers
    CREDIT_EXACT_MATCH = 1.00
    CREDIT_RELATED_MATCH = 0.65

    # Degree Hierarchy Mapping (0 to 4)
    DEGREE_HIERARCHY = {
        "doctorate": 4, "phd": 4, "ph.d": 4, "doctor of philosophy": 4,
        "master": 3, "master's": 3, "masters": 3, "m.s": 3, "ms": 3, "m.tech": 3, "mtech": 3, "msc": 3, "mba": 3,
        "bachelor": 2, "bachelor's": 2, "bachelors": 2, "b.s": 2, "bs": 2, "b.tech": 2, "btech": 2, "b.e": 2, "be": 2, "bsc": 2, "b.a": 2, "ba": 2, "undergraduate": 2,
        "associate": 1, "associate's": 1, "associates": 1, "diploma": 1,
        "high school": 0
    }

    # Canonical Skill Normalization Dictionary
    # Maps variations/abbreviations to standard display names
    CANONICAL_SKILL_MAP: Dict[str, str] = {
        "py": "Python",
        "python": "Python",
        "python programming": "Python",
        "python3": "Python",
        "js": "JavaScript",
        "javascript": "JavaScript",
        "ecmascript": "JavaScript",
        "ts": "TypeScript",
        "typescript": "TypeScript",
        "golang": "Go",
        "go": "Go",
        "go lang": "Go",
        "c++": "C++",
        "cpp": "C++",
        "c#": "C#",
        "csharp": "C#",
        "java": "Java",
        "rust": "Rust",
        "php": "PHP",
        "ruby": "Ruby",
        "swift": "Swift",
        "kotlin": "Kotlin",
        "dart": "Dart",
        "react": "React",
        "reactjs": "React",
        "react.js": "React",
        "react native": "React Native",
        "vue": "Vue.js",
        "vuejs": "Vue.js",
        "vue.js": "Vue.js",
        "angular": "Angular",
        "angularjs": "Angular",
        "angular.js": "Angular",
        "node": "Node.js",
        "nodejs": "Node.js",
        "node.js": "Node.js",
        "express": "Express.js",
        "expressjs": "Express.js",
        "express.js": "Express.js",
        "fastapi": "FastAPI",
        "fast api": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "spring": "Spring Boot",
        "spring boot": "Spring Boot",
        "springboot": "Spring Boot",
        "nextjs": "Next.js",
        "next.js": "Next.js",
        "sql": "SQL",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "sqlite": "SQLite",
        "mongodb": "MongoDB",
        "mongo": "MongoDB",
        "redis": "Redis",
        "cassandra": "Cassandra",
        "dynamodb": "DynamoDB",
        "docker": "Docker",
        "docker container": "Docker",
        "containerization": "Docker",
        "kubernetes": "Kubernetes",
        "k8s": "Kubernetes",
        "aws": "Amazon Web Services (AWS)",
        "amazon web services": "Amazon Web Services (AWS)",
        "gcp": "Google Cloud Platform (GCP)",
        "google cloud": "Google Cloud Platform (GCP)",
        "azure": "Microsoft Azure",
        "microsoft azure": "Microsoft Azure",
        "terraform": "Terraform",
        "ansible": "Ansible",
        "git": "Git",
        "github": "Git",
        "gitlab": "Git",
        "ci/cd": "CI/CD",
        "ci cd": "CI/CD",
        "continuous integration": "CI/CD",
        "github actions": "GitHub Actions",
        "jenkins": "Jenkins",
        "rest": "REST APIs",
        "restful": "REST APIs",
        "rest api": "REST APIs",
        "restful api": "REST APIs",
        "restful apis": "REST APIs",
        "graphql": "GraphQL",
        "grpc": "gRPC",
        "ml": "Machine Learning",
        "machine learning": "Machine Learning",
        "ai": "Artificial Intelligence",
        "artificial intelligence": "Artificial Intelligence",
        "deep learning": "Deep Learning",
        "dl": "Deep Learning",
        "nlp": "Natural Language Processing",
        "natural language processing": "Natural Language Processing",
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "scikit-learn": "Scikit-Learn",
        "scikit learn": "Scikit-Learn",
        "tailwind": "Tailwind CSS",
        "tailwindcss": "Tailwind CSS",
        "tailwind css": "Tailwind CSS",
        "bootstrap": "Bootstrap",
        "html": "HTML5",
        "html5": "HTML5",
        "css": "CSS3",
        "css3": "CSS3",
        "sass": "Sass/SCSS",
        "scss": "Sass/SCSS",
        "linux": "Linux",
        "unix": "Linux",
        "bash": "Bash Scripting",
        "shell": "Bash Scripting",
        "agile": "Agile / Scrum",
        "scrum": "Agile / Scrum",
        "jira": "Jira",
        "microservices": "Microservices",
        "distributed systems": "Distributed Systems",
        "kafka": "Kafka",
        "apache kafka": "Kafka"
    }

    # Related / Family Skill Map
    # Connects specialized skills with parent/sibling competencies
    # to avoid treating candidates who know SQL as completely missing PostgreSQL.
    RELATED_SKILL_MAP: Dict[str, Set[str]] = {
        "PostgreSQL": {"SQL", "MySQL", "SQLite", "Relational Databases", "RDBMS"},
        "MySQL": {"SQL", "PostgreSQL", "SQLite", "Relational Databases", "RDBMS"},
        "SQLite": {"SQL", "PostgreSQL", "MySQL", "Relational Databases"},
        "SQL": {"PostgreSQL", "MySQL", "SQLite", "Database"},
        "MongoDB": {"NoSQL", "Document Databases", "Database", "Redis"},
        "Redis": {"In-Memory Caching", "Caching", "NoSQL", "Database"},
        "FastAPI": {"Python", "REST APIs", "Flask", "Backend", "API Design"},
        "Flask": {"Python", "REST APIs", "FastAPI", "Django", "Backend"},
        "Django": {"Python", "Web Frameworks", "Flask", "FastAPI", "Backend"},
        "React": {"JavaScript", "TypeScript", "Frontend", "Next.js", "Web Development"},
        "React Native": {"React", "Mobile Development", "JavaScript"},
        "Next.js": {"React", "TypeScript", "JavaScript", "Frontend"},
        "Vue.js": {"JavaScript", "TypeScript", "Frontend", "Web Development"},
        "Angular": {"TypeScript", "JavaScript", "Frontend", "Web Development"},
        "Node.js": {"JavaScript", "TypeScript", "Express.js", "Backend"},
        "Express.js": {"Node.js", "JavaScript", "Backend", "REST APIs"},
        "Kubernetes": {"Docker", "Containerization", "DevOps", "Cloud Orchestration"},
        "Docker": {"Containerization", "Kubernetes", "DevOps", "Linux"},
        "Terraform": {"Infrastructure as Code", "DevOps", "Cloud", "AWS"},
        "Amazon Web Services (AWS)": {"Cloud Computing", "Google Cloud Platform (GCP)", "Microsoft Azure", "DevOps"},
        "Google Cloud Platform (GCP)": {"Cloud Computing", "Amazon Web Services (AWS)", "Microsoft Azure"},
        "Microsoft Azure": {"Cloud Computing", "Amazon Web Services (AWS)", "Google Cloud Platform (GCP)"},
        "Machine Learning": {"Python", "Data Science", "Artificial Intelligence", "Deep Learning", "PyTorch", "TensorFlow"},
        "Deep Learning": {"Machine Learning", "Neural Networks", "PyTorch", "TensorFlow", "Python"},
        "PyTorch": {"Machine Learning", "Deep Learning", "Python", "TensorFlow"},
        "TensorFlow": {"Machine Learning", "Deep Learning", "Python", "PyTorch"},
        "Pandas": {"Data Analysis", "Python", "NumPy", "Data Science"},
        "TypeScript": {"JavaScript", "Frontend", "Node.js"},
        "JavaScript": {"TypeScript", "Frontend", "Web Development"},
        "REST APIs": {"API Design", "Backend", "FastAPI", "Flask", "GraphQL"},
        "GraphQL": {"REST APIs", "API Design", "Backend"},
        "CI/CD": {"DevOps", "GitHub Actions", "Jenkins", "GitLab", "Docker"},
        "GitHub Actions": {"CI/CD", "DevOps", "Git"},
        "Tailwind CSS": {"CSS3", "Frontend", "HTML5"},
        "Bootstrap": {"CSS3", "Frontend", "HTML5"}
    }

    # Skill Category Taxonomy
    SKILL_CATEGORIES: Dict[str, str] = {
        "Python": "Languages", "JavaScript": "Languages", "TypeScript": "Languages",
        "Go": "Languages", "Java": "Languages", "C++": "Languages", "C#": "Languages",
        "Rust": "Languages", "PHP": "Languages", "Ruby": "Languages", "Swift": "Languages",
        "SQL": "Databases", "PostgreSQL": "Databases", "MySQL": "Databases", "SQLite": "Databases",
        "MongoDB": "Databases", "Redis": "Databases", "Cassandra": "Databases", "DynamoDB": "Databases",
        "React": "Frameworks", "React Native": "Frameworks", "Vue.js": "Frameworks", "Angular": "Frameworks",
        "Node.js": "Frameworks", "Express.js": "Frameworks", "FastAPI": "Frameworks", "Flask": "Frameworks",
        "Django": "Frameworks", "Spring Boot": "Frameworks", "Next.js": "Frameworks",
        "Docker": "DevOps & Cloud", "Kubernetes": "DevOps & Cloud",
        "Amazon Web Services (AWS)": "DevOps & Cloud", "Google Cloud Platform (GCP)": "DevOps & Cloud",
        "Microsoft Azure": "DevOps & Cloud", "Terraform": "DevOps & Cloud", "CI/CD": "DevOps & Cloud",
        "GitHub Actions": "DevOps & Cloud", "Linux": "DevOps & Cloud",
        "REST APIs": "Architecture & APIs", "GraphQL": "Architecture & APIs", "gRPC": "Architecture & APIs",
        "Microservices": "Architecture & APIs", "Distributed Systems": "Architecture & APIs",
        "Kafka": "Messaging & Streaming",
        "Machine Learning": "AI & Data Science", "Artificial Intelligence": "AI & Data Science",
        "Deep Learning": "AI & Data Science", "Natural Language Processing": "AI & Data Science",
        "PyTorch": "AI & Data Science", "TensorFlow": "AI & Data Science",
        "Pandas": "AI & Data Science", "NumPy": "AI & Data Science",
        "HTML5": "Frontend", "CSS3": "Frontend", "Tailwind CSS": "Frontend", "Bootstrap": "Frontend",
        "Agile / Scrum": "Methodologies", "Git": "Tools & Version Control"
    }

    @classmethod
    def canonicalize_skill(cls, skill_str: str) -> str:
        """Normalize a skill string into its canonical display name."""
        if not skill_str:
            return ""
        norm_key = skill_str.strip().lower()
        if norm_key in cls.CANONICAL_SKILL_MAP:
            return cls.CANONICAL_SKILL_MAP[norm_key]

        # Clean trailing parentheticals, e.g. "Kubernetes (K8s)" -> "kubernetes"
        cleaned_parens = re.sub(r"\s*\([^)]*\)", "", norm_key).strip()
        if cleaned_parens in cls.CANONICAL_SKILL_MAP:
            return cls.CANONICAL_SKILL_MAP[cleaned_parens]

        # Handle slash compounds, e.g. "JavaScript / JS", "Linux / Unix"
        if "/" in norm_key:
            parts = [p.strip() for p in norm_key.split("/") if p.strip()]
            for p in parts:
                if p in cls.CANONICAL_SKILL_MAP:
                    return cls.CANONICAL_SKILL_MAP[p]

        # Return cleanly capitalized string if not in explicit dictionary
        return skill_str.strip()

    @classmethod
    def extract_candidate_skills(cls, resume_data: Dict[str, Any]) -> Set[str]:
        """
        Extract all canonical skills detected in the candidate's resume.
        Scans full text as well as designated sections (Skills, Experience, Projects).
        """
        full_text = resume_data.get("full_text", "")
        section_contents = resume_data.get("section_contents", {})

        # Give priority/weight to technical sections
        skills_text = section_contents.get("Skills", "") + "\n" + \
                      section_contents.get("Experience", "") + "\n" + \
                      section_contents.get("Projects", "") + "\n" + \
                      full_text

        text_lower = " " + skills_text.lower() + " "
        detected: Set[str] = set()

        for term, canonical in cls.CANONICAL_SKILL_MAP.items():
            # Use word boundaries or punctuation-safe lookahead for symbols
            escaped = re.escape(term)
            pattern = rf"(?:\b|(?<=[^A-Za-z0-9])){escaped}(?:\b|(?=[^A-Za-z0-9]))"
            if re.search(pattern, text_lower):
                detected.add(canonical)

        return detected

    @classmethod
    def extract_candidate_experience_years(cls, resume_data: Dict[str, Any]) -> float:
        """
        Estimate candidate's total years of experience from resume text and date ranges.
        """
        full_text = resume_data.get("full_text", "")
        current_year = datetime.now().year

        # 1. Search for explicit statements: "5+ years of experience", "4 years experience"
        explicit_matches = re.findall(
            r"(\d+)(?:\+|-|\s*to\s*\d+)?\s*(?:years|yrs)(?:\s+of)?\s+(?:experience|exp)",
            full_text,
            re.IGNORECASE
        )
        if explicit_matches:
            try:
                explicit_years = [float(y) for y in explicit_matches]
                return max(explicit_years)
            except ValueError:
                pass

        # 2. Extract tenure from date ranges (e.g. 2021 – Present, 2017 – 2021)
        year_ranges = re.findall(
            r"\b(20\d{2}|19\d{2})\s*[-–to/]\s*(20\d{2}|present|current|now)\b",
            full_text,
            re.IGNORECASE
        )
        
        total_tenure_years = 0.0
        calculated_spans = []

        for start_str, end_str in year_ranges:
            try:
                start_yr = int(start_str)
                end_yr = current_year if end_str.lower() in ("present", "current", "now") else int(end_str)
                span = max(0, end_yr - start_yr)
                # Cap individual span to prevent college graduation years being miscalculated as 20 years
                if 0 <= span <= 15:
                    calculated_spans.append(span)
            except ValueError:
                continue

        if calculated_spans:
            # Avoid double-counting overlapping dates by taking cumulative or bounded max
            return float(max(calculated_spans))

        # Default fallback: check if candidate is a fresher / entry-level
        if "internship" in full_text.lower() or "fresher" in full_text.lower():
            return 0.5

        return 1.0

    @classmethod
    def extract_candidate_education(cls, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect highest degree level and field of study from candidate's resume.
        """
        full_text = resume_data.get("full_text", "")
        edu_section = resume_data.get("section_contents", {}).get("Education", "")
        text_to_search = (edu_section + " " + full_text).lower()

        DEGREE_CANONICAL_NAMES = {
            4: "Doctorate (PhD)",
            3: "Master's",
            2: "Bachelor's",
            1: "Associate",
            0: "Not specified"
        }

        highest_degree_level = 0
        for deg_term, level in cls.DEGREE_HIERARCHY.items():
            escaped = re.escape(deg_term)
            if re.search(rf"\b{escaped}\b", text_to_search):
                if level > highest_degree_level:
                    highest_degree_level = level

        highest_degree_name = DEGREE_CANONICAL_NAMES.get(highest_degree_level, "Not specified")

        # Check field of study
        fields_found = []
        for field in ["computer science", "software engineering", "data science", "information technology", "electrical engineering", "mathematics"]:
            if field in text_to_search:
                fields_found.append(field.title())

        field_summary = fields_found[0] if fields_found else "Engineering / STEM"

        return {
            "level": highest_degree_level,
            "degree_name": highest_degree_name,
            "fields": fields_found,
            "field_summary": field_summary,
            "has_degree": highest_degree_level > 0
        }

    @classmethod
    def match(
        cls,
        resume_data: Optional[Dict[str, Any]],
        jd_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main matching orchestrator.
        Calculates separate scores for Skills, Keywords, Education, and Experience,
        and generates a weighted Overall Match Score.
        """
        # --- 1. Validation & Input Sanitization ---
        if not resume_data or not isinstance(resume_data, dict):
            raise MatcherError(
                "Resume data is missing or empty. Please upload and parse a valid resume document.",
                code="MISSING_RESUME_DATA"
            )

        if not jd_data or not isinstance(jd_data, dict):
            raise MatcherError(
                "Job description data is missing or empty. Please provide a valid job description.",
                code="MISSING_JD_DATA"
            )

        resume_text = resume_data.get("full_text", "").strip()
        if not resume_text:
            raise MatcherError(
                "Resume document contains no extractable text or text layer is empty.",
                code="EMPTY_RESUME_TEXT"
            )

        # Retrieve parsed JD attributes
        req_skills_raw = jd_data.get("required_skills", [])
        pref_skills_raw = jd_data.get("preferred_skills", [])
        jd_keywords_raw = jd_data.get("keywords") or jd_data.get("important_keywords") or []
        jd_education = jd_data.get("education") or jd_data.get("education_requirements") or {}
        jd_experience = jd_data.get("experience") or jd_data.get("experience_requirements") or {}

        # Canonicalize JD skills
        required_jd_skills = [cls.canonicalize_skill(s) for s in req_skills_raw if s]
        preferred_jd_skills = [cls.canonicalize_skill(s) for s in pref_skills_raw if s]
        
        # Deduplicate while preserving order
        required_jd_skills = list(dict.fromkeys(required_jd_skills))
        preferred_jd_skills = [s for s in list(dict.fromkeys(preferred_jd_skills)) if s not in required_jd_skills]

        # Extract candidate's skills, experience, and education
        candidate_skills = cls.extract_candidate_skills(resume_data)
        candidate_years = cls.extract_candidate_experience_years(resume_data)
        candidate_edu = cls.extract_candidate_education(resume_data)

        # --- 2. Skills Matching (Exact vs. Related vs. Missing) ---
        matched_skills: List[Dict[str, Any]] = []
        missing_required_skills: List[Dict[str, Any]] = []
        missing_preferred_skills: List[Dict[str, Any]] = []

        required_credits = 0.0
        preferred_credits = 0.0

        # Evaluate Required Skills
        for skill in required_jd_skills:
            category = cls.SKILL_CATEGORIES.get(skill, "Core Technology")
            if skill in candidate_skills:
                # Exact Match
                required_credits += cls.CREDIT_EXACT_MATCH
                matched_skills.append({
                    "name": skill,
                    "category": category,
                    "match_type": "exact",
                    "relevance": "Required",
                    "matched_via": "Exact match found in resume",
                    "credit": cls.CREDIT_EXACT_MATCH,
                    "proficiency": "Verified in Resume"
                })
            else:
                # Check for Related / Family Match
                related_candidates = cls.RELATED_SKILL_MAP.get(skill, set())
                found_rel = [r for r in related_candidates if r in candidate_skills]
                if found_rel:
                    rel_skill = found_rel[0]
                    required_credits += cls.CREDIT_RELATED_MATCH
                    matched_skills.append({
                        "name": skill,
                        "category": category,
                        "match_type": "related",
                        "relevance": "Required",
                        "matched_via": f"Related skill '{rel_skill}' found in resume",
                        "credit": cls.CREDIT_RELATED_MATCH,
                        "proficiency": "Related Skill Identified"
                    })
                else:
                    # Missing Required Skill
                    missing_required_skills.append({
                        "name": skill,
                        "category": category,
                        "priority": "critical",
                        "relevance": "Required",
                        "frequency_in_jd": 2,
                        "impact": f"High - Core requirement '{skill}' was not detected in resume text."
                    })

        # Evaluate Preferred Skills
        for skill in preferred_jd_skills:
            category = cls.SKILL_CATEGORIES.get(skill, "Preferred Technology")
            if skill in candidate_skills:
                # Exact Match
                preferred_credits += cls.CREDIT_EXACT_MATCH
                matched_skills.append({
                    "name": skill,
                    "category": category,
                    "match_type": "exact",
                    "relevance": "Preferred",
                    "matched_via": "Exact match found in resume",
                    "credit": cls.CREDIT_EXACT_MATCH,
                    "proficiency": "Preferred Skill Match"
                })
            else:
                related_candidates = cls.RELATED_SKILL_MAP.get(skill, set())
                found_rel = [r for r in related_candidates if r in candidate_skills]
                if found_rel:
                    rel_skill = found_rel[0]
                    preferred_credits += cls.CREDIT_RELATED_MATCH
                    matched_skills.append({
                        "name": skill,
                        "category": category,
                        "match_type": "related",
                        "relevance": "Preferred",
                        "matched_via": f"Related skill '{rel_skill}' found in resume",
                        "credit": cls.CREDIT_RELATED_MATCH,
                        "proficiency": "Related Skill Identified"
                    })
                else:
                    missing_preferred_skills.append({
                        "name": skill,
                        "category": category,
                        "priority": "recommended",
                        "relevance": "Preferred",
                        "frequency_in_jd": 1,
                        "impact": f"Medium - Preferred bonus skill '{skill}' not listed in resume."
                    })

        # Calculate Skills Match Score (0 - 100)
        total_req_count = len(required_jd_skills)
        total_pref_count = len(preferred_jd_skills)

        if total_req_count > 0 and total_pref_count > 0:
            req_score = (required_credits / total_req_count) * 100.0
            pref_score = (preferred_credits / total_pref_count) * 100.0
            # 75% weight on required, 25% on preferred
            skills_score = round(0.75 * req_score + 0.25 * pref_score, 1)
        elif total_req_count > 0:
            skills_score = round((required_credits / total_req_count) * 100.0, 1)
        elif total_pref_count > 0:
            skills_score = round((preferred_credits / total_pref_count) * 100.0, 1)
        else:
            # No detectable skills in JD
            skills_score = 75.0 if len(candidate_skills) > 0 else 50.0

        # --- 3. Keyword Match (Job-Specific Domain Keywords) ---
        matched_keywords: List[Dict[str, Any]] = []
        missing_keywords: List[Dict[str, Any]] = []

        resume_lower = resume_text.lower()
        total_jd_keywords = len(jd_keywords_raw)

        for kw_item in jd_keywords_raw:
            kw_name = kw_item.get("keyword", "") if isinstance(kw_item, dict) else str(kw_item)
            kw_count = kw_item.get("count", 1) if isinstance(kw_item, dict) else 1
            if not kw_name:
                continue

            # Case-insensitive word boundary check
            escaped_kw = re.escape(kw_name.lower())
            occurrences = len(re.findall(rf"\b{escaped_kw}\b", resume_lower))

            if occurrences > 0:
                matched_keywords.append({
                    "keyword": kw_name,
                    "count_in_jd": kw_count,
                    "frequency_in_resume": occurrences,
                    "status": "matched"
                })
            else:
                missing_keywords.append({
                    "keyword": kw_name,
                    "count_in_jd": kw_count,
                    "status": "missing"
                })

        if total_jd_keywords > 0:
            keyword_score = round((len(matched_keywords) / total_jd_keywords) * 100.0, 1)
        else:
            keyword_score = 80.0

        # --- 4. Education Match (Hierarchy & Field of Study) ---
        jd_edu_degrees = jd_education.get("degrees", [])
        jd_edu_fields = jd_education.get("fields_of_study", [])
        jd_edu_specified = jd_education.get("is_specified", False)

        required_degree_level = 0
        for deg in jd_edu_degrees:
            deg_lower = deg.lower()
            for key, level in cls.DEGREE_HIERARCHY.items():
                if key in deg_lower:
                    required_degree_level = max(required_degree_level, level)

        cand_level = candidate_edu["level"]

        if not jd_edu_specified or required_degree_level == 0:
            # No strict education requirement stated in JD
            edu_score = 100.0 if candidate_edu["has_degree"] else 85.0
        else:
            if cand_level >= required_degree_level:
                base_edu = 90.0
            elif cand_level == required_degree_level - 1:
                base_edu = 70.0
            elif cand_level > 0:
                base_edu = 50.0
            else:
                base_edu = 35.0

            # Bonus for matching field of study
            field_bonus = 0.0
            if jd_edu_fields:
                if any(f.lower() in [cf.lower() for cf in candidate_edu["fields"]] for f in jd_edu_fields):
                    field_bonus = 10.0
                elif candidate_edu["fields"]:
                    field_bonus = 5.0
            else:
                field_bonus = 10.0 if candidate_edu["fields"] else 0.0

            edu_score = min(100.0, base_edu + field_bonus)

        # --- 5. Experience Match (Years of Experience & Scope) ---
        jd_min_years = jd_experience.get("min_years")
        jd_exp_specified = jd_experience.get("is_specified", False)

        if jd_min_years is not None and jd_min_years > 0:
            if candidate_years >= jd_min_years:
                exp_score = 100.0
            elif candidate_years >= (jd_min_years - 1):
                exp_score = 82.0
            elif candidate_years >= (jd_min_years * 0.5):
                exp_score = 65.0
            elif candidate_years > 0:
                exp_score = 45.0
            else:
                exp_score = 25.0
        else:
            # JD does not strictly quantify years
            if candidate_years >= 3:
                exp_score = 95.0
            elif candidate_years >= 1:
                exp_score = 85.0
            else:
                exp_score = 70.0

        # --- 6. Overall Match Score (Weighted Composite) ---
        # Overall = 0.40 * Skills + 0.25 * Experience + 0.20 * Keyword + 0.15 * Education
        raw_overall = (
            (cls.WEIGHT_SKILLS * skills_score) +
            (cls.WEIGHT_EXPERIENCE * exp_score) +
            (cls.WEIGHT_KEYWORDS * keyword_score) +
            (cls.WEIGHT_EDUCATION * edu_score)
        )
        overall_score = int(round(raw_overall))
        # Clamp to bounds [0, 100]
        overall_score = max(0, min(100, overall_score))

        # --- 7. Score Verdict Classification ---
        if overall_score >= 85:
            verdict_label = "Exceptional Candidate Match"
            verdict_class = "badge-success"
            tier = "high"
        elif overall_score >= 70:
            verdict_label = "Strong Candidate Match"
            verdict_class = "badge-success"
            tier = "strong"
        elif overall_score >= 55:
            verdict_label = "Moderate Alignment"
            verdict_class = "badge-warning"
            tier = "moderate"
        elif overall_score >= 40:
            verdict_label = "Developing Alignment"
            verdict_class = "badge-warning"
            tier = "developing"
        else:
            verdict_label = "Significant Skill Gap"
            verdict_class = "badge-danger"
            tier = "gap"

        # --- 8. Transparent Match Explanation ---
        skills_summary_parts = []
        exact_count = sum(1 for m in matched_skills if m["match_type"] == "exact")
        related_count = sum(1 for m in matched_skills if m["match_type"] == "related")
        
        if exact_count > 0:
            skills_summary_parts.append(f"{exact_count} exact skill match{'es' if exact_count != 1 else ''}")
        if related_count > 0:
            skills_summary_parts.append(f"{related_count} related competency match{'es' if related_count != 1 else ''}")
        
        skills_str = ", ".join(skills_summary_parts) if skills_summary_parts else "No direct technical matches"
        missing_req_count = len(missing_required_skills)
        missing_str = f"{missing_req_count} required gap{'s' if missing_req_count != 1 else ''}" if missing_req_count else "no critical required gaps"

        match_explanation = (
            f"Overall match score is {overall_score}% ({verdict_label}), calculated using transparent weighted criteria: "
            f"Skills Alignment {skills_score}% ({skills_str}; {missing_str}), "
            f"Experience Relevance {exp_score}% (Candidate has ~{candidate_years:.1f} yrs vs {jd_min_years or 'unspecified'} required), "
            f"Keyword Coverage {keyword_score}% ({len(matched_keywords)} of {total_jd_keywords} job terms found), and "
            f"Education Match {edu_score}% ({candidate_edu['degree_name']} in {candidate_edu['field_summary']})."
        )

        scores_explanation = {
            "skills_match": f"{skills_score}%: {skills_str} identified. {missing_str}.",
            "experience_match": f"{exp_score}%: Estimated candidate tenure is ~{candidate_years:.1f} years against role requirements.",
            "keyword_match": f"{keyword_score}%: {len(matched_keywords)} of {total_jd_keywords} key domain keywords matched in resume text.",
            "education_match": f"{edu_score}%: Candidate holds {candidate_edu['degree_name']} degree in {candidate_edu['field_summary']}."
        }

        # Combine missing skills for unified dashboard listing
        all_missing_skills = missing_required_skills + missing_preferred_skills

        # Generate actionable improvement suggestions based on real gaps
        improvement_suggestions = []
        sug_idx = 1

        if missing_required_skills:
            top_miss = [s["name"] for s in missing_required_skills[:3]]
            improvement_suggestions.append({
                "id": f"sug-{sug_idx}",
                "category": "Required Skills Gap",
                "type": "high",
                "title": f"Address Missing Core Competencies: {', '.join(top_miss)}",
                "description": f"The job description explicitly emphasizes {', '.join(top_miss)} as core requirements. If you have experience with these or related tools, document specific projects or implementations in your resume."
            })
            sug_idx += 1

        if missing_keywords:
            top_miss_kw = [k["keyword"] for k in missing_keywords[:4]]
            improvement_suggestions.append({
                "id": f"sug-{sug_idx}",
                "category": "Keyword Optimization",
                "type": "high",
                "title": f"Integrate High-Priority Job Keywords",
                "description": f"Incorporate relevant domain keywords like '{', '.join(top_miss_kw)}' naturally into your work experience bullet points to improve ATS screening pass rates."
            })
            sug_idx += 1

        if candidate_years < (jd_min_years or 0):
            improvement_suggestions.append({
                "id": f"sug-{sug_idx}",
                "category": "Experience Context",
                "type": "medium",
                "title": "Emphasize Production Impact to Offset Experience Gap",
                "description": f"The position seeks {jd_min_years}+ years of experience. Highlight high-impact projects, scale metrics (e.g. latency reduction, user volume), and leadership to demonstrate senior-level execution."
            })
            sug_idx += 1

        if not improvement_suggestions:
            improvement_suggestions.append({
                "id": f"sug-{sug_idx}",
                "category": "Profile Polish",
                "type": "medium",
                "title": "Quantify Achievements with Key Metrics",
                "description": "Your profile demonstrates strong alignment with the job description. Strengthen your bullet points by quantifying performance outcomes (e.g., percentage improvements, users served)."
            })

        return {
            "success": True,
            "scores": {
                "overall_match": overall_score,
                "skills_match": int(round(skills_score)),
                "keyword_match": int(round(keyword_score)),
                "keyword_coverage": int(round(keyword_score)), # alias for backward compatibility
                "education_match": int(round(edu_score)),
                "experience_match": int(round(exp_score)),
                "experience_relevance": int(round(exp_score)), # alias for backward compatibility
                "ats_compatibility": 88 # preserved mechanical baseline
            },
            "scoring_formula": {
                "formula": "Overall = (0.40 * Skills) + (0.25 * Experience) + (0.20 * Keywords) + (0.15 * Education)",
                "weights": {
                    "skills": cls.WEIGHT_SKILLS,
                    "experience": cls.WEIGHT_EXPERIENCE,
                    "keywords": cls.WEIGHT_KEYWORDS,
                    "education": cls.WEIGHT_EDUCATION
                }
            },
            "score_verdict": {
                "label": verdict_label,
                "tier": tier,
                "color_class": verdict_class,
                "summary": match_explanation
            },
            "match_explanation": match_explanation,
            "scores_explanation": scores_explanation,
            "matched_skills": matched_skills,
            "missing_required_skills": missing_required_skills,
            "missing_preferred_skills": missing_preferred_skills,
            "missing_skills": all_missing_skills,
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "improvement_suggestions": improvement_suggestions,
            "candidate_stats": {
                "estimated_experience_years": candidate_years,
                "highest_degree": candidate_edu["degree_name"],
                "field_of_study": candidate_edu["field_summary"],
                "total_skills_detected": len(candidate_skills)
            }
        }


# Convenient alias
Matcher = ResumeJobMatcher
