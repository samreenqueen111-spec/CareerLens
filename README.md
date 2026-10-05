# CareerLens AI - Candidate Intelligence Platform (Stages 1–9)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/samreenqueen111-spec/CareerLens-AI)
[![Live GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/samreenqueen111-spec/CareerLens-AI)
[![Tests Passing](https://img.shields.io/badge/Tests-80%2F80%20Passing-brightgreen)](https://github.com/samreenqueen111-spec/CareerLens-AI)


CareerLens AI is a production-quality web application designed to help job seekers, students, and professionals understand how well their resume matches a specific job and what they should improve before applying.

Stage 2 introduced **Real Resume Parsing** with `pypdf` and `python-docx`, section detection across 8 standard resume sections, client & server-side validation, safe non-public upload storage, and dynamic text previews.

Stage 3 introduced **Real Job Description Analysis** via pure Python text-processing (`app/services/job_analyzer.py`), separating required skills from preferred skills, detecting soft skills, extracting education and experience requirements, computing keyword frequencies, and rendering structured results.

Stage 4 introduced **Real Resume-to-Job Matching** via a transparent, multi-dimensional scoring engine (`app/services/matcher.py`). It calculates separate, documented scores for Skills Match, Experience Relevance, Keyword Match, and Education Compatibility with canonical skill normalization, related competency credit, and distinct missing required vs. preferred skill categorizations.

Stage 5 introduced **Skill Gap Analysis & ATS-Style Resume Analysis** via two dedicated services (`app/services/skill_gap_analyzer.py` and `app/services/ats_analyzer.py`), providing deep gap diagnosis, weak/shallow match detection, transferable competency bridges, and a transparent 11-point heuristic ATS audit.

Stage 6 introduced the **Personalized Career Learning Roadmap** via a dedicated service (`app/services/roadmap_generator.py`). It synthesizes real gap data into a structured 3-phase progression (Phase 1: High Priority, Phase 2: Medium Priority, Phase 3: Optional) based ONLY on skills actually missing or weak for the target role, featuring a top "Recommended Next Step" callout, beginner-friendly actionable steps, and transparent "Why this roadmap?" rationale without fake courses or guarantees.

Stage 7 introduced persistent **SQLite Storage & Analysis History** via a clean database layer (`database/database.py` and `database/models.py`), auto-persisting completed evaluations, allowing users to view saved reports on `/dashboard?id=...`, managing history with confirmed deletions, and providing an empty state.

Stage 8 introduces **User Authentication + Privacy + Security** (`services/auth_service.py`, `database/models.py`). Features PBKDF2 password hashing, secure session management, strict user-isolated evaluation history, ownership authorization checks, and dedicated candidate privacy policies (`/privacy`).

Stage 9 introduces **Professional Analysis PDF Reports** (`services/report_generator.py`). Implements high-fidelity two-pass PDF report compilation using ReportLab, containing all 14 required evaluation sections, dynamic running headers, page numbering, score cards, gap matrices, career roadmaps, and authenticated owner-only download verification (`/report/<id>/download`).

---

## Cloud Deployment Guide

CareerLens AI is configured for production cloud deployment with **Render**, **Railway**, **Fly.io**, and **Docker**.

### Option A: 1-Click Deploy to Render (Free Tier)
1. Go to [render.com](https://render.com) and log in with your GitHub account (**samreenqueen111-spec**).
2. Click **New +** > **Web Service**.
3. Select your repository: **`samreenqueen111-spec/CareerLens-AI`**.
4. Render will automatically detect the settings from [`render.yaml`](render.yaml) & [`Procfile`](Procfile):
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app`
5. Under **Environment Variables**, set:
   - `SECRET_KEY`: *(Generate a secure random string or use the default generated value)*
   - `FLASK_ENV`: `production`
6. Click **Create Web Service**. Your app will be live at `https://careerlens-ai.onrender.com` in 2 minutes!

### Option B: Deploy with Docker
```bash
# Build the production container image
docker build -t careerlens-ai .

# Run the container
docker run -d -p 5000:5000 -e SECRET_KEY=your_production_secret careerlens-ai
```

### Option C: Deploy to Railway
1. Go to [railway.app](https://railway.app) and click **New Project**.
2. Select **Deploy from GitHub repo** > **`samreenqueen111-spec/CareerLens-AI`**.
3. Railway automatically detects `Procfile` and deploys the app with Gunicorn.

---

## Stage 7 Features: SQLite Database & Analysis History (`database/`)

Stage 7 introduces a clean, persistent storage architecture powered by SQLite and a dedicated data access layer:

1. **Persistent SQLite Storage:**
   - Zero-dependency relational database using Python's standard library `sqlite3`.
   - Default persistent database located at `careerlens.db` in project root (configurable via `DATABASE_PATH` environment variable).
   - Automatically initializes schema, tables, and indices on application boot if they do not exist.
   - Clean connection lifecycle management with request-scoped caching on `flask.g` and automatic teardown (`app.teardown_appcontext(close_db)`), plus standalone execution support.

2. **Clean Database Layer (`database/database.py` & `database/models.py`):**
   - **`database/database.py`**: Manages connection pooling, lifecycle hooks, and safe schema initialization with table and index creation.
   - **`database/models.py`**: Provides the `AnalysisModel` entity with full CRUD methods:
     - `create(...)`: Inserts or updates an analysis record using parameterized SQL.
     - `get_by_id(analysis_id)`: Fetches a single record by primary key with JSON field deserialization.
     - `get_all(limit, offset)`: Retrieves paginated records ordered by descending chronological date (`created_at_iso DESC`).
     - `delete_by_id(analysis_id)`: Deletes an analysis record cleanly with row-count verification.
     - `count()`: Returns the total count of stored analyses.
     - `to_summary_dict()`: Exports summary representations for history cards and API listings.
     - `to_full_dict()`: Re-hydrates the complete evaluation snapshot for the Results Dashboard view.

3. **Complete Analysis Record Schema:**
   - Every completed evaluation persists:
     - **Analysis ID** (`id TEXT PRIMARY KEY`)
     - **Job Title & Company** (`job_title TEXT`, `company TEXT`)
     - **Resume Filename** (`resume_filename TEXT`)
     - **Multi-Dimensional Match Scores**:
       - `overall_score INTEGER`
       - `skills_score INTEGER`
       - `keyword_score INTEGER`
       - `education_score INTEGER`
       - `experience_score INTEGER`
       - `ats_score INTEGER`
     - **Categorized Skills & Gaps**:
       - `matched_skills TEXT` (JSON serialized array)
       - `missing_required_skills TEXT` (JSON serialized array)
       - `missing_preferred_skills TEXT` (JSON serialized array)
       - `weak_matches TEXT` (JSON serialized array)
     - **Career Learning Roadmap** (`roadmap TEXT`, JSON serialized)
     - **Improvement Suggestions & ATS Checklist** (`improvement_suggestions TEXT`, `ats_checklist TEXT`)
     - **Full Analysis Snapshot** (`full_analysis_json TEXT`, JSON serialized)
     - **Timestamps** (`created_at TEXT`, `created_at_iso TEXT`) with descending indexing (`idx_analyses_created_at_iso`).

4. **Security & Parameterized Queries:**
   - **100% Parameterized SQL:** All queries use `?` placeholders; user inputs, job descriptions, and filenames are never concatenated directly into SQL strings, preventing SQL injection vulnerabilities.
   - **No Secrets in Database:** No sensitive API keys, auth secrets, or credentials are saved in SQLite tables.
   - **Sanitized Uploads:** Resumes are processed in-memory or stored safely in designated non-public folders.

5. **Graceful Error Handling & Non-Blocking Analysis:**
   - Database operations are wrapped with try/except fallbacks in `StorageService`.
   - If SQLite storage encounters an I/O or lock error, the analysis pipeline completes successfully, returns the generated results to the user, and maintains an in-memory backup cache so the user's workflow is never interrupted.

6. **Analysis History Interface (`/history`):**
   - Displays all historical analyses ordered from newest to oldest.
   - Card displays: Job title, Company name, Date/Time stamp, Overall Match badge (color-coded High/Moderate/Low), and ATS Readiness score badge.
   - **"View Analysis" Button:** Re-opens the complete saved report in the Results Dashboard (`/dashboard?id=<analysis_id>`), re-rendering all Stage 1–6 charts, skill gap priorities, weak matches, ATS audit items, and personalized roadmap.
   - **"Delete" Button:** Triggers a confirmation modal with role name; upon confirmation, removes the record via `DELETE /api/history/<analysis_id>` with animated UI transition.
   - **Empty State:** When no past evaluations exist, displays the clean, professional empty state message:
     *"No analyses yet. Upload your resume and analyze your first job."* with a quick "Run New Analysis" action button.

---

## Stage 6 Features: Personalized Career Learning Roadmap (`app/services/roadmap_generator.py`)

Stage 6 introduces an algorithmic, highly personalized career roadmap generator that transforms gap diagnostics into an actionable, sequenced learning journey:

1. **Strictly Gap-Driven Recommendations:**
   - Evaluates ONLY skills actually missing or weakly demonstrated for the target job description.
   - **Never recommends skills simply because they are popular:** If a skill is not required or preferred by the JD, it is never arbitrarily injected.
   - **Excludes verified skills:** Competencies already clearly demonstrated in the candidate's resume (e.g. Python, Docker, SQL) are omitted from the roadmap to ensure 100% of study time targets genuine qualification gaps.
   - **Never invents user experience:** All prerequisite bridges strictly rely on verified skills detected in the parsed resume.
   - **No fake course links or promises:** Uses vetted official documentation quickstarts and concrete mini-project milestones; never uses affiliate links or promises that completing the roadmap guarantees employment.

2. **Roadmap Structure — 3 Sequential Phases:**
   - **Phase 1 — High Priority (Critical Requirements):**
     - Focuses on mandatory job requirements that are completely missing or weakly evidenced.
     - Includes related-skill bridges bridging hard requirements (e.g., candidate has SQL, role requires PostgreSQL).
   - **Phase 2 — Medium Priority (Core Job Readiness):**
     - High-value preferred skills that elevate backend, cloud, or system readiness.
     - Bridges for preferred qualifications (e.g., candidate has Docker, role prefers Kubernetes).
   - **Phase 3 — Optional / Nice-to-Have (Competitive Edge):**
     - Secondary tooling, peripheral libraries, and bonus qualifications that provide an extra edge without being strictly mandatory.

3. **Top "Recommended Next Step" Callout:**
   - Highlights the single highest-priority skill to begin working on today.
   - Specifies:
     - **Skill Name & Priority Badge**
     - **Current Status Badge** (*Missing*, *Weak*, or *Related skill found*)
     - **Recommended Learning Level** (*Beginner*, *Intermediate*, or *Advanced*)
     - **Why Start Here:** Concrete explanation of why tackling this specific skill first yields the highest screening ROI.
     - **Immediate First Action:** Beginner-friendly first step (e.g. 10-minute setup and minimal code script).
     - **Estimated Time Commitment:** Realistic hours and weekly timeframe.

4. **Detailed Skill Cards with Beginner-Friendly Steps:**
   - Each recommended skill card clearly displays:
     $$\text{Skill} \longrightarrow \text{Priority} \longrightarrow \text{Why Recommended} \longrightarrow \text{Learning Level}$$
   - Includes:
     - **Current Status:** *Missing* (from scratch), *Weak* (listed in skills overview without experience bullets), or *Related skill found* (adjacent foundation detected).
     - **Suggested Sequence Number:** Logical prerequisite ordering (Step 1, Step 2, Step 3...).
     - **Adjacent Competency Bridge:** Explains what transferable concepts the user already knows and the specific technical delta to bridge.
     - **Actionable 3-Step Plan:**
       1. *Core Concepts & Setup:* Foundational architecture and local environment.
       2. *Hands-On Mini Project:* Realistic, verifiable application component.
       3. *Resume & Interview Evidence:* How to articulate the new capability in interview stories.
     - **Vetted Official Reference:** Links/references to official documentation.

5. **"Why this roadmap?" Explanation & Disclaimer:**
   - Dynamically generated rationale explaining how the engine analyzed the candidate's resume against the target role requirements.
   - Transparently details which verified skills were omitted.
   - Explicit disclaimer stating that completing the roadmap prepares candidates for technical interviews but hiring outcomes remain at employer discretion.

---

## Stage 5 Features: Skill Gap Analysis & ATS-Style Resume Analysis

Stage 5 bridges the gap between raw match scores and actionable career progression through two dedicated, specialized services:

### Part 1 — Skill Gap Analysis (`app/services/skill_gap_analyzer.py`)

Using the real results from Stage 4 matching, the Skill Gap Analyzer identifies and diagnoses all candidate qualification gaps without inventing skills or fabricating candidate experience:

1. **Missing Required Skills (High Priority):**
   - Flags non-negotiable hard requirements absent from the candidate's resume.
   - For every missing skill, provides:
     - **Skill Name & Category** (e.g. *Databases*, *DevOps & Cloud*, *Languages*)
     - **Priority:** Always set to `High` for required skills.
     - **Why it matters:** Specific technical explanation of the skill's role in the job.
     - **Suggested Learning Direction:** Hands-on study steps, frameworks, and reference resources.

2. **Missing Preferred Skills (Medium / Low Priority):**
   - Isolates "nice-to-have" skills that can give candidates a competitive edge.
   - Categorized as `Medium` priority for primary technical domains (languages, databases, cloud) or `Low` priority for secondary tooling.
   - Provides concrete learning pathways for career growth.

3. **Weak & Low-Confidence Matches:**
   - **Related Skill Matches:** When a requirement is fulfilled via a parent/related skill (e.g., candidate has *Docker* for a *Kubernetes* requirement, or *SQL* for *PostgreSQL*), it is flagged with the exact related skill match and actionable steps to demonstrate native proficiency.
   - **Shallow Keyword Mentions:** Detects skills mentioned only in a static skills list but missing evidence, metrics, or project context in Work Experience.

4. **Transferable Skills & Competency Bridges:**
   - Maps candidate's verified skills to target JD requirements.
   - Details **Transferable Concepts**, **Delta to Bridge**, **Satisfaction Level** (e.g., *75% Satisfied*), and **Interview Strategy** (how to pitch adjacent experience in technical interviews).
   - **Strict Verification Guarantee:** Strictly relies on verified candidate skills; never claims skills not detected in the resume text.

5. **Personalized 3-Phase Learning Roadmap:**
   - Synthesizes identified gaps into a concrete 3-phase progression:
     - **Phase 1 (Weeks 1–2):** Critical Foundation (highest-impact missing required skill)
     - **Phase 2 (Weeks 3–4):** Architecture & Integration (core backend, cloud, or system design skill)
     - **Phase 3 (Weeks 5–6):** Production Readiness & Advanced Practices (preferred tools, testing, CI/CD)
   - Each phase outlines concrete weekly milestones, estimated hours, and vetted learning resources.

---

### Part 2 — ATS-Style Resume Analysis (`app/services/ats_analyzer.py`)

An automated heuristic audit evaluating uploaded resumes against 11 industry-standard ATS (Applicant Tracking System) indexing characteristics:

> [!NOTE]
> **Transparent Heuristic Audit Notice:** This feature is a deterministic, rule-based compatibility audit based on publicly known recruiter scanning standards and resume parsing best practices. It does NOT claim to replicate proprietary, black-box commercial algorithms (such as Workday, Taleo, or Greenhouse).

1. **11 Transparent Heuristic Evaluation Criteria:**
   - **Essential Contact Anchors (10 pts):** Verified email, phone, location/city, and LinkedIn or GitHub profiles.
   - **Section Architecture (15 pts):** Standard heading conventions (*Summary*, *Work Experience*, *Education*, *Technical Skills*).
   - **Technical Skills Formatting (15 pts):** Dedicated skills section with clean delimiter/categorized formatting ($8+$ skills).
   - **Education & Academic Credentials (10 pts):** Verified degree title, university name, and graduation year.
   - **Experience Chronology & Quantified Impact (20 pts):** Chronological date ranges (`2021 – Present`), strong past-tense action verbs (*Architected*, *Spearheaded*, *Optimized*), and quantified business metrics (`%`, `$`, request volume, user scale).
   - **Technical Projects Demonstration (5 pts):** Dedicated projects section with dates and technology stack mentions.
   - **Certifications & Credentials (5 pts):** Professional certifications (*AWS Certified*, *CKA*, *PMP*).
   - **Keyword Coverage & Density (10 pts):** Matching job keywords and automated detection of artificial keyword stuffing ($>10\times$ repetition).
   - **Job Title Alignment (5 pts):** Relevance of candidate's past job titles or headline to the target role.
   - **Readability & Text Hygiene (5 pts):** Optimal word count ($150-1,200$ words) and clean ASCII extraction without corrupt artifacts.
   - **Formatting Hazards (Pass/Flag):** Scans for multi-column tables, excessive symbols, or layout hazards that risk text misordering in basic parsers.

2. **Deterministic Scoring & Grading:**
   - Returns a transparent **0–100 ATS Score** with Letter Grades:
     - `A` (85–100): Excellent ATS Compatibility
     - `B` (70–84): Good Compatibility with minor gaps
     - `C` (55–69): Fair Compatibility requiring structural revisions
     - `D` (<55): Formatting or structural hazards detected
   - Produces an 11-point diagnostic checklist with `pass`, `warning`, or `fail` status, detailed rationale, and concrete recommendations.

---

## Stage 4 Features: Real Resume-to-Job Matching

1. **Documented Multi-Dimensional Scoring Formula:**
   No random scores or sample fixtures are used when real documents are provided. The **Overall Match Score** uses a documented, weighted composite formula:
   $$\text{Overall Match} = (0.40 \times \text{Skills}) + (0.25 \times \text{Experience}) + (0.20 \times \text{Keywords}) + (0.15 \times \text{Education})$$
   - **Skills Match (40% weight):**
     - Required job skills: 75% sub-weight
     - Preferred job skills: 25% sub-weight
     - Exact match credit: $1.0$ ($100\%$)
     - Related competency credit: $0.65$ ($65\%$)
   - **Experience Match (25% weight):**
     - Compares candidate's tenure (extracted from date ranges like `2021 – Present` or explicit statements like `5+ years`) against the role's required years.
     - Meeting or exceeding requirements yields $100\%$; within 1-2 years yields $75\%-85\%$; junior/entry-level roles yield structured tiered credit.
   - **Keyword Match (20% weight):**
     - Evaluates occurrences of important job-specific domain terms and tools across the candidate's resume.
   - **Education Match (15% weight):**
     - Compares highest degree attained (*Doctorate*, *Master's*, *Bachelor's*, *Associate*) against the job's minimum requirement, with bonus credit for matching STEM / Computer Science disciplines.

2. **Canonical Skill Normalization & Related Skill Family Mapping:**
   - Normalizes naming variations and abbreviations (e.g., `JS` $\rightarrow$ `JavaScript`, `py` $\rightarrow$ `Python`, `ML` $\rightarrow$ `Machine Learning`, `Kubernetes (K8s)` $\rightarrow$ `Kubernetes`, `Postgres` $\rightarrow$ `PostgreSQL`).
   - Distinguishes **Exact Matches** from **Related Matches** (e.g., candidate having `SQL` receives $0.65$ credit toward a `PostgreSQL` requirement without falsely claiming exact proficiency).

3. **Separation of Missing Required vs. Missing Preferred Skills:**
   - **Missing Required Skills:** Flags critical hard gaps that could disqualify an application.
   - **Missing Preferred Skills:** Highlights bonus opportunities without heavily penalizing overall candidate viability.

4. **Keyword Correlation Grid:**
   - Displays **Matched Keywords** with their frequency of appearance in the resume.
   - Displays **Missing Keywords** with frequency counts in the job description to guide targeted resume keyword optimization.

5. **Match Explanation & Score Rationale:**
   - Transparent, human-readable summary detailing why the overall score was awarded, including tenure comparison, exact/related skill counts, and degree verification.

6. **Dedicated Service Architecture:**
   - Implemented in `app/services/matcher.py` (`ResumeJobMatcher` / `Matcher`).
   - Dedicated REST API endpoint: `POST /api/match` accepting raw text or structured resume & JD payloads.
   - Comprehensive edge-case handling for empty text, missing inputs, and roles without detectable skill requirements.

---

## Stage 3 Features: Real Job Description Analysis

1. **Categorized Competency Extraction:**
   - **Required Technical Skills:** Extracts core languages, frameworks, databases, cloud, and tools (e.g., Python, SQL, React, Git, PostgreSQL).
   - **Preferred / Nice-to-Have Skills:** Intelligently separates "nice-to-have" skills from hard requirements using section boundaries (*Preferred Qualifications*, *Nice to Have*, *Bonus*, *Pluses*) and inline phrase cues (*preferred*, *plus*, *bonus*, *familiarity with*, *nice to have*).
   - **Soft Skills & Attributes:** Isolates essential interpersonal and process competencies (*communication*, *teamwork*, *leadership*, *problem solving*, *mentorship*, *agile*, *critical thinking*).

2. **Education & Experience Qualification Extraction:**
   - **Education Requirements:** Detects required degree levels (*Bachelor's*, *Master's*, *PhD*, *B.Tech*, *Associate*) paired with target disciplines (*Computer Science*, *Data Science*, *Software Engineering*, *Information Technology*, *STEM*).
   - **Experience Requirements:** Quantifies minimum and maximum required years (e.g., `3+ years`, `5-7 years`), detects junior/fresher/internship roles, and classifies the seniority level (*Entry Level*, *Mid Level*, *Senior / Staff Level*).

3. **Important Domain Keywords & Frequency Ranking:**
   - Cleans and filters text against common stopwords to surface high-relevance domain keywords and their exact frequencies.

4. **Dedicated Service Architecture:**
   - Implemented in `app/services/job_analyzer.py` (`JobAnalyzer` class).
   - Dedicated REST API endpoint: `POST /api/analyze-jd` accepting JSON or form data.
   - Comprehensive error handling for empty inputs, short descriptions (<30 characters, <8 words), and unreadable content.

5. **User Interface Integration (Without Redesign):**
   - **Interactive Live Extraction:** The Analyzer workspace features an **Extract Skills** button and instant quick-fill sample roles (*Senior Full Stack*, *Frontend Platform*, *DevOps Engineer*) with live feedback.
   - **Visual Skill Tags & Cards:** Renders styled badges:
     - Required Technical Skills (`tag-required` green pills)
     - Preferred / Nice-to-Have Skills (`tag-preferred` amber pills)
     - Soft Skills (`tag-soft` blue pills)
     - Important Keywords with frequency chips (`tag-keyword`)
     - Experience Requirement and Education Requirement summary cards
   - **Results Dashboard Integration:** When an analysis report is submitted, the Results Dashboard renders the **Analyzed Job Description (Stage 3 Engine)** card displaying the actual extracted requirements.

---

## Stage 2 Features: Real Resume Parsing

1. **Accepted Formats:**
   - **PDF (`.pdf`):** Real text extraction using `pypdf.PdfReader` with page-by-page stream extraction, encryption checks, and error recovery.
   - **Microsoft Word (`.docx`):** Real text extraction using `python-docx` traversing both standard paragraphs and layout tables.

2. **Validation & Security:**
   - **Strict Extension Checking:** Rejects unsupported files safely (`.exe`, `.txt`, `.jpg`, etc.).
   - **File Size Restrictions:** Enforces maximum size limit (5 MB) and blocks 0-byte empty files.
   - **Corruption & Decryption Safeguards:** Safely intercepts password-protected PDFs, corrupt PDF streams, invalid ZIP/XML archives, and empty text layers with user-friendly error banners.
   - **Safe Upload Storage:** Uploaded documents are renamed with unique randomized prefixes using `werkzeug.utils.secure_filename` and stored in `uploads/` (isolated from public static assets, never executed, and never exposed via public URLs).

3. **Heuristic Section Detection (No LLM):**
   Reliable Python regular expression rules detect and categorize 8 common resume sections:
   - **Contact Information** (with email, phone, and profile link extraction)
   - **Summary/Profile**
   - **Education**
   - **Skills**
   - **Experience**
   - **Projects**
   - **Certifications**
   - **Achievements**

4. **Real-Time UI Display:**
   - **Immediate Upload Feedback:** Uploading a PDF or DOCX file immediately extracts text and displays:
     - Real file name and file type badge (e.g. `PDF Document` or `Microsoft Word (DOCX)`)
     - Real character count and word count
     - Detected section pills (highlighted with checkmarks)
     - Scrollable, expandable extracted text preview block with a **Copy Text** button
   - **Dashboard Integration:** When an analysis is submitted, the Results Dashboard displays a **Parsed Resume Inspection** card showing the actual extracted text and section breakdown alongside matching metrics.

---

## Main Screens

### 1. Landing Page (`/`)
- Professional CareerLens AI branding with custom SVG brandmark.
- Clear value proposition: *"Know Exactly How Your Resume Matches the Job Before You Apply"*.
- Prominent **"Analyze My Resume"** primary CTA.
- 4 Core Capabilities:
  - **Resume-JD Semantic Matching**
  - **Skill Gap Analysis** (Critical vs Recommended vs Optional)
  - **ATS-Style Verification** (Formatting and readability audit)
  - **Personalized Learning Roadmap** (Structured phased curriculum)
- **How It Works:** 4-step workflow explaining candidate submission, text extraction, semantic correlation, and gap closure.
- Professional SaaS footer with platform links, engineering transparency, and privacy commitments.

### 2. Resume Analyzer Workspace (`/analyzer`)
- Interactive drag-and-drop document upload area supporting `.pdf` and `.docx` (Max 5 MB).
- Real-time client-side and server-side text extraction.
- Selected file preview pill with filename, size, and remove button.
- Live **Extracted Resume Preview** card with character/word counts, detected sections, and copy functionality.
- Target Job Title & Employer inputs.
- Job Description editor with real-time word and character counter.
- **One-click Quick-Fill Sample Roles:** Preloads realistic JDs (*Senior Full Stack*, *Frontend Platform*, *DevOps Engineer*) for testing.
- **Multi-step Loading State:** Realistic pipeline animation showcasing sequential validation, text extraction, semantic keyword matching, ATS scoring, and roadmap formulation.

### 3. Results Dashboard (`/dashboard`)
- Clearly marked **Stage 1 Prototype Preview** informational banner.
- **Parsed Resume Inspection Card (Stage 2):** Real document details, word counts, detected sections, and extracted text preview.
- **Overall Match Score:** High-contrast animated circular gauge with health status verdict.
- **4 Key Dimensional Metrics:**
  - Skills Match (`84%`)
  - Experience Relevance (`72%`)
  - Keyword Coverage (`76%`)
  - ATS Compatibility (`88%`)
- **Matched Skills:** Categorized chips (Languages, Frameworks, Databases, DevOps, Architecture) with proficiency ratings.
- **Missing Skills & Gaps:** Prioritized gap cards (`Critical`, `Recommended`, `Optional`) with JD frequency weighting.
- **Actionable Resume Improvements:** Checklist recommendations with copy-to-clipboard functionality.
- **ATS Compatibility Audit:** Diagnostic checklist verifying single-column structure, standard section headers, contact anchors, and keyword density.
- **Personalized Skill Roadmap:** Phased milestones (Weeks 1–2, 3–4, 5–6) with estimated study hours and vetted learning resources.
- Action toolbar: **Print/Export Report** and **New Analysis**.

### 4. Analysis History Workspace (`/history`)
- Historical analysis log with job title, employer, timestamp, match score badge, and ATS score.
- **Real-Time Search:** Instant filtering by job title or target employer.
- **Score Filtering:** Filter by High Match (≥75%), Moderate (50–74%), or Low (<50%).
- **Interactive Actions:** Direct "View Analysis" link to reopen specific reports.
- **Delete Management:** Confirmation modal with smooth DOM removal, counter updates, and clean empty state handling.

### 5. Architecture & About Page (`/about`)
- Transparent documentation of candidate privacy principles.
- Detailed scoring methodology across the 4 analysis vectors.
- Multi-stage engineering roadmap.

---

## Project Structure

```
careerlens-ai/
├── .env                              # Local environment variables
├── .env.example                      # Example environment variables & future stubs
├── .gitignore                        # Production gitignore for Python, uploads & secrets
├── requirements.txt                  # Python dependencies (Stage 1 & 2 Core)
├── config.py                         # Configuration classes (Dev, Prod, Test)
├── run.py                            # Application entry point
├── README.md                         # Complete documentation
├── samples/                          # Test resume fixtures (PDF & DOCX)
│   ├── generate_sample_resumes.py    # Script to regenerate sample resumes
│   ├── sample_resume.pdf             # Real test PDF resume (337 words, 8 sections)
│   └── sample_resume.docx            # Real test DOCX resume (335 words, 8 sections)
├── tests/
│   └── test_careerlens.py            # Automated integration test suite (18 tests)
└── app/
    ├── __init__.py                   # Flask Application Factory (create_app)
    ├── routes/
    │   ├── __init__.py
    │   ├── main.py                   # Landing page, about, and health check routes
    │   ├── analyzer.py               # Analyzer, dashboard, and history view routes
    │   ├── api.py                    # REST API (/api/parse-resume, /api/analyze, /api/history)
    │   └── errors.py                 # Custom 400, 404, 413, 500 error handlers
    ├── services/
    │   ├── __init__.py
    │   ├── resume_parser.py          # Stage 2 Real Resume Parser (PDF/DOCX & sections)
    │   ├── parser_service.py         # Parser wrapper & service interface
    │   ├── sample_data.py            # High-fidelity mock analysis & history fixtures
    │   ├── analysis_service.py       # Analysis coordinator & Stage 2 AI stub
    │   └── storage_service.py        # In-memory history store & Stage 3 DB interface
    ├── static/
    │   ├── css/
    │   │   ├── variables.css         # Design tokens & dark/light theme definitions
    │   │   ├── base.css              # CSS reset, typography hierarchy, containers
    │   │   ├── components.css        # Buttons, badges, cards, modals, toasts, nav
    │   │   ├── landing.css           # Hero, features, how-it-works, footer styles
    │   │   ├── analyzer.css          # Dropzone, JD editor, loading modal, parsed text preview
    │   │   ├── dashboard.css         # Overall score gauge, skills, roadmap styles
    │   │   └── history.css           # History cards, search filters, empty state
    │   ├── js/
    │   │   ├── theme.js              # Zero-flicker dark/light mode controller
    │   │   ├── main.js               # Mobile nav, toasts, accessible modal controls
    │   │   ├── analyzer.js           # Drag-and-drop, validation, real-time parsing, pipeline
    │   │   ├── dashboard.js          # Radial gauge animator, clipboard copy, print
    │   │   └── history.js            # Live filter, delete confirmation modal, state
    │   └── images/
    │       └── logo.svg              # CareerLens AI brandmark
    └── templates/
        ├── base.html                 # Master layout with anti-flicker theme script
        ├── components/
        │   ├── navbar.html           # Responsive sticky navbar with theme toggle
        │   └── footer.html           # SaaS footer with architectural notices
        ├── pages/
        │   ├── index.html            # Landing page
        │   ├── analyzer.html         # Resume Analyzer interface with parsed text preview
        │   ├── dashboard.html        # Results Dashboard with parsed document inspection
        │   ├── history.html          # Analysis History
        │   └── about.html            # Architecture & Methodology
        └── errors/
            ├── 400.html              # Bad Request error view
            ├── 404.html              # Not Found error view
            ├── 413.html              # File Size Exceeded error view
            └── 500.html              # Internal Server Error view
```

---

## Installation & Quick Start

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### 2. Environment Setup

```bash
# Clone or navigate to the repository directory
cd c:\Users\91789\Documents\antigravity

# Create a virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# Install dependencies (Flask, pypdf, python-docx, reportlab, python-dotenv)
pip install -r requirements.txt
```

### 3. Configure Environment Variables
A ready-to-run `.env` is already included for local development:
```bash
# Optional: copy from example if needed
cp .env.example .env
```

### 4. Run the Application
Launch the Flask development server:
```bash
python run.py
```

The application will start on:
- **Landing Page:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Resume Analyzer:** [http://127.0.0.1:5000/analyzer](http://127.0.0.1:5000/analyzer)
- **Results Dashboard:** [http://127.0.0.1:5000/dashboard](http://127.0.0.1:5000/dashboard)
- **Analysis History:** [http://127.0.0.1:5000/history](http://127.0.0.1:5000/history)
- **Health Check:** [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health)

---

## Testing Real Resume Parsing & Job Description Analysis

CareerLens AI includes two pre-built sample resumes in the `samples/` directory:
- `samples/sample_resume.pdf`
- `samples/sample_resume.docx`

### Manual Browser Testing:
1. Open [http://127.0.0.1:5000/analyzer](http://127.0.0.1:5000/analyzer).
2. **Test Resume Parsing (Stage 2):**
   - Drag and drop either `samples/sample_resume.pdf` or `samples/sample_resume.docx`.
   - The application immediately processes the document:
     - Displays **"Resume parsed successfully! Identified 8 of 8 common sections."**
     - Displays file type badge (`PDF Document` or `Microsoft Word (DOCX)`).
     - Displays real character and word counts (e.g., `337 words • 2,491 chars`).
     - Renders badges for detected sections (*Contact Information*, *Summary*, *Skills*, *Experience*, *Education*, *Projects*, *Certifications*, *Achievements*).
     - Shows the scrollable **Extracted Text Preview** with **Copy Text** and **Expand** buttons.
3. **Test Job Description Analysis (Stage 3):**
   - Click any quick-fill sample button (*Senior Full Stack*, *Frontend Platform*, or *DevOps Engineer*), or paste custom JD text into the editor.
   - Click **Extract Skills** (or trigger on edit).
   - The application analyzes the text in real-time and displays:
     - **Experience Requirement** (e.g., `4+ years of production experience` with seniority classification)
     - **Education Requirement** (e.g., `Bachelor's in Computer Science`)
     - **Required Technical Skills** (green tags, e.g., `Python`, `React`, `TypeScript`, `SQL`, `Git`)
     - **Preferred / Nice-to-Have Skills** (amber tags, e.g., `Docker`, `Kubernetes`, `GraphQL`, `Redis`)
     - **Soft Skills & Attributes** (blue tags, e.g., `Communication`, `Mentorship`, `Agile`)
     - **Important Domain Keywords** with frequency counts
4. **End-to-End Submission:**
   - Click **Run Analysis**. The Results Dashboard opens with both the **Parsed Resume Inspection** card (Stage 2) and the **Analyzed Job Description** card (Stage 3) displaying the actual extracted data.

### Automated Test Suite:
Run the comprehensive 62-test suite covering Stages 1, 2, 3, 4, 5, and 6:
```bash
python -m unittest discover tests
```

**Results:**
```
Ran 72 tests in 6.06s
OK
```

---

## API Specifications

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/roadmap` | **Stage 6 Endpoint:** Accepts raw text or structured payloads, returning a 3-phase career roadmap based ONLY on missing or weak skills, with top "Recommended Next Step", beginner-friendly steps, and rationale |
| `POST` | `/api/skill-gap` | **Stage 5 Endpoint:** Accepts raw text or structured payloads, returning missing required/preferred skills with priorities, why it matters, learning direction, weak matches, transferable competency bridges, and a 3-phase learning roadmap |
| `POST` | `/api/ats-audit` | **Stage 5 Endpoint:** Accepts raw text or parsed resume data, performing an 11-point heuristic ATS compatibility audit with transparent 0–100 scoring, letter grades, formatting hazard detection, and recommendations |
| `POST` | `/api/match` | **Stage 4 Endpoint:** Accepts raw text (`resume_text`, `job_description`) or structured JSON payloads and performs transparent matching across Skills, Experience, Keywords, and Education |
| `POST` | `/api/parse-resume` | **Stage 2 Endpoint:** Accepts resume file (`resume`), extracts text, detects sections, and returns character/word count and text preview |
| `POST` | `/api/analyze-jd` | **Stage 3 Endpoint:** Accepts `job_description` and optional `job_title`, extracts required/preferred technical skills, soft skills, education, experience, and keywords |
| `POST` | `/api/analyze` | Unified end-to-end pipeline: Handles resume upload & JD, executes parsing (Stage 2), JD analysis (Stage 3), matching (Stage 4), skill gap analysis (Stage 5), ATS audit (Stage 5), and personalized career roadmap (Stage 6), automatically persists to SQLite database, and returns complete structured results |
| `GET` | `/api/history` | **Stage 7 Endpoint:** Returns JSON array of all past analyses ordered from SQLite database by descending timestamp |
| `GET` | `/api/history/<id>` | **Stage 7 Endpoint:** Returns details for a single analysis record from SQLite database |
| `DELETE` | `/api/history/<id>` | **Stage 7 Endpoint:** Deletes an analysis record from SQLite database with row confirmation |
| `GET` | `/api/sample-jd/<role>` | Returns sample job description (`fullstack`, `frontend`, `devops`) |
| `GET` | `/health` | Application status, version, and configuration |

---

## Multi-Stage Roadmap

```
+-------------------------------------------------------------+
| STAGE 1: FOUNDATION (COMPLETED)                             |
| - Flask Application Factory & modular blueprints            |
| - Reusable Jinja2 component hierarchy                       |
| - Light / Dark mode system tokens & zero-flicker init       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 2: REAL RESUME PARSING (COMPLETED)                    |
| - PDF Text Extraction via pypdf (encrypted checks, streams) |
| - DOCX Text Extraction via python-docx (paragraphs, tables) |
| - Heuristic Section Detection (8 common resume sections)    |
| - Real-time extracted text preview, word/char counts in UI  |
| - Safe non-public uploads directory with randomized keys    |
| - Comprehensive error handling (empty, corrupt, unsupported)|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 3: REAL JOB DESCRIPTION ANALYSIS (COMPLETED)          |
| - Python text-processing service (JobAnalyzer)              |
| - Required Technical Skills taxonomy extraction             |
| - Preferred vs Required skills separation (sections & cues) |
| - Soft skills & professional competencies categorization    |
| - Education (degrees + disciplines) requirements extraction |
| - Experience (quantified years + seniority) extraction      |
| - Domain keywords & frequency ranking                       |
| - Real-time UI skill tags & dashboard integration           |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 4: REAL RESUME-TO-JOB MATCHING (COMPLETED)            |
| - Transparent weighted scoring (40% Skill, 25% Exp,         |
|   20% KW, 15% Edu) via app/services/matcher.py             |
| - Canonical skill normalization (e.g. JS -> JavaScript)    |
| - Exact vs related skill matching (0.65 credit distinction) |
| - Missing required (critical) vs preferred (bonus) skills   |
| - Keyword correlation analysis (matched vs missing)         |
| - Match explanation & score rationale generation            |
| - Real Stage 4 Results Dashboard & POST /api/match endpoint |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 5: SKILL GAP & ATS-STYLE ANALYSIS (COMPLETED)         |
| - Dedicated SkillGapAnalyzer & AtsAnalyzer services         |
| - Missing required (High) vs preferred (Med/Low) skills     |
| - Why it matters & structured learning directions           |
| - Weak & low-confidence match identification                |
| - Transferable skills & competency bridging logic           |
| - 11-point transparent heuristic ATS compatibility audit   |
| - Deterministic 0-100 ATS scoring & diagnostic checklist    |
| - Actionable resume improvements & 3-phase closure roadmap  |
| - Dedicated POST /api/skill-gap & POST /api/ats-audit APIs  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 6: PERSONALIZED CAREER ROADMAP (COMPLETED)            |
| - Dedicated RoadmapGenerator service (roadmap_generator.py) |
| - Dynamic recommendations ONLY for missing/weak skills      |
| - Omission of verified competencies & no popular skill spam |
| - Top "Recommended Next Step" highest-impact action callout |
| - 3-phase progression (High, Medium, Optional / Nice-to-Have)|
| - Detailed cards: Skill -> Priority -> Why -> Learning Level|
| - Concrete beginner-friendly steps with vetted references   |
| - Transparent "Why this roadmap?" explanation & disclaimer  |
| - Dedicated POST /api/roadmap endpoint & dashboard view     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 7: DATABASE + ANALYSIS HISTORY (COMPLETED)            |
| - Zero-dependency persistent SQLite storage (careerlens.db) |
| - Clean database layer (database/database.py & models.py)   |
| - Parameterized queries safe against SQL injection attacks  |
| - AnalysisModel CRUD with full evaluation snapshot storage  |
| - Non-blocking error resilience with memory store fallback  |
| - Analysis History view (/history) with sorting and metrics |
| - Full report re-opening on Results Dashboard (/dashboard)  |
| - Modal-confirmed deletion (DELETE /api/history/<id>)       |
| - Polished empty state with call-to-action button           |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 8: USER AUTHENTICATION + PRIVACY + SECURITY (COMPLETED)|
| - Secure PBKDF2 password hashing & Flask session management |
| - User accounts & isolated history isolation (UserModel)     |
| - Strictly scoped analyses: user-only view, delete, access   |
| - Environment secret management & safe parameterized queries |
| - Candidate privacy declaration & transparency policy       |
| - Routes: /signup, /login, /logout, /privacy & API endpoints|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 9: PROFESSIONAL ANALYSIS REPORT (COMPLETED)           |
| - High-fidelity ReportLab 5.0.1 PDF compilation engine      |
| - NumberedCanvas two-pass dynamic page numbering (X of Y)   |
| - 14 comprehensive evaluation sections in single report     |
| - Dynamic candidate overview, target job cards & score card |
| - Verified skills & color-coded gap matrices (Req & Pref)   |
| - Resume strengths, tailored improvements & 3-phase roadmap |
| - "Download Report" CTA on Dashboard & owner authorization   |
| - Strict download endpoints: /report/<id>/download          |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| STAGE 10: AI EMBEDDINGS & ADVANCED LLM REASONING (FUTURE)   |
| - SentenceTransformers embeddings & cosine semantic scoring |
| - Context-aware resume tailoring & interview preparation    |
+-------------------------------------------------------------+
```

---

## Verification & Test Suite

Run the complete automated test suite (77 tests spanning Stages 1 through 9):

```bash
python -m unittest discover -s tests -p "test_*.py"
```

All 77 tests pass with 100% success rate across parsing, matching, gap analysis, ATS auditing, roadmapping, SQLite persistence, user authentication, and PDF report compilation.

---

## License

CareerLens AI is licensed under the MIT License.
