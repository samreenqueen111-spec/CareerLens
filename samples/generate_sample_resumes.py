"""
Script to generate test sample resumes in PDF and DOCX formats.
Used for verifying Stage 2 real resume parsing across all 8 standard sections.
"""

from pathlib import Path
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

SAMPLES_DIR = Path(__file__).resolve().parent

RESUME_DATA = {
    "name": "Alex Morgan",
    "contact": "alex.morgan@example.com | (555) 234-5678 | San Francisco, CA | linkedin.com/in/alexmorgan | github.com/alexmorgan",
    "summary": "Results-driven Senior Full Stack Software Engineer with 5+ years of experience designing, scaling, and maintaining high-performance web platforms. Deep expertise in Python, React, PostgreSQL, and distributed cloud microservices with a track record of improving latency by 35% and mentoring junior engineers.",
    "skills": "Languages: Python, JavaScript, TypeScript, SQL, Go\nFrameworks & Libraries: React, Flask, FastAPI, Node.js, Express, Tailwind CSS\nDatabases & Storage: PostgreSQL, MySQL, Redis, MongoDB\nDevOps & Tools: Docker, Git, GitHub Actions, CI/CD, AWS (S3, EC2), Linux, Nginx",
    "experience": [
        "Senior Software Engineer • CloudScale Labs (2023 – Present)\n- Architected high-throughput REST APIs in Python (FastAPI/Flask) serving 2.5M daily requests with 99.98% uptime.\n- Spearheaded migration of legacy monolithic frontend to React and TypeScript, accelerating page load speeds by 42%.\n- Integrated automated CI/CD testing pipelines with GitHub Actions, cutting release cycles from weekly to daily.",
        "Full Stack Developer • Nexus Interactive (2021 – 2023)\n- Developed interactive customer portal features using React and Node.js for 80,000+ active enterprise users.\n- Optimized PostgreSQL query execution plans and database indexes, reducing median endpoint latency by 28%.\n- Collaborated with UI/UX designers to implement WCAG 2.1 AA accessible design system components."
    ],
    "education": "Bachelor of Science in Computer Science • University of California, Berkeley (2017 – 2021)\nGraduated Cum Laude • Relevant Coursework: Data Structures & Algorithms, Operating Systems, Database Systems, Distributed Computing.",
    "projects": [
        "Distributed Task Queue Engine (2024)\nBuilt an in-memory asynchronous task runner in Python and Redis supporting priority scheduling, exponential retry policies, and real-time dashboard observability.",
        "DevPulse Analytics Platform (2023)\nDeveloped an open-source GitHub workflow telemetry visualization dashboard using React, TypeScript, and FastAPI, starred by over 600 developers."
    ],
    "certifications": "- AWS Certified Solutions Architect – Associate (Amazon Web Services, 2024)\n- Meta Certified Front-End Developer Specialization (Meta / Coursera, 2022)",
    "achievements": "- 1st Place Winner, CalHacks Open Cloud Hackathon (2020) out of 150 competing teams.\n- Dean's Honor List for 6 consecutive semesters at UC Berkeley."
}


def generate_docx(output_path: Path):
    doc = Document()
    doc.add_heading(RESUME_DATA["name"], level=0)
    
    # Contact Information
    doc.add_heading("Contact Information", level=1)
    doc.add_paragraph(RESUME_DATA["contact"])
    
    # Summary
    doc.add_heading("Summary", level=1)
    doc.add_paragraph(RESUME_DATA["summary"])
    
    # Skills
    doc.add_heading("Technical Skills", level=1)
    doc.add_paragraph(RESUME_DATA["skills"])
    
    # Experience
    doc.add_heading("Work Experience", level=1)
    for exp in RESUME_DATA["experience"]:
        doc.add_paragraph(exp)
        
    # Education
    doc.add_heading("Education", level=1)
    doc.add_paragraph(RESUME_DATA["education"])
    
    # Projects
    doc.add_heading("Projects", level=1)
    for proj in RESUME_DATA["projects"]:
        doc.add_paragraph(proj)
        
    # Certifications
    doc.add_heading("Certifications", level=1)
    doc.add_paragraph(RESUME_DATA["certifications"])
    
    # Achievements
    doc.add_heading("Achievements", level=1)
    doc.add_paragraph(RESUME_DATA["achievements"])
    
    doc.save(output_path)
    print(f"Generated DOCX resume: {output_path}")


def generate_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor="#1E293B"
    )
    story.append(Paragraph(RESUME_DATA["name"], title_style))
    story.append(Spacer(1, 4))

    # Contact
    contact_style = ParagraphStyle(
        "ContactStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor="#475569"
    )
    story.append(Paragraph(RESUME_DATA["contact"], contact_style))
    story.append(Spacer(1, 10))

    # Headings and content
    h_style = ParagraphStyle(
        "H1Style",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor="#4338CA",
        spaceBefore=8,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor="#334155"
    )

    # Summary
    story.append(Paragraph("Professional Summary", h_style))
    story.append(Paragraph(RESUME_DATA["summary"], body_style))
    story.append(Spacer(1, 6))

    # Skills
    story.append(Paragraph("Technical Skills", h_style))
    for line in RESUME_DATA["skills"].splitlines():
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 6))

    # Experience
    story.append(Paragraph("Work Experience", h_style))
    for exp in RESUME_DATA["experience"]:
        for line in exp.splitlines():
            story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 4))

    # Education
    story.append(Paragraph("Education", h_style))
    for line in RESUME_DATA["education"].splitlines():
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 6))

    # Projects
    story.append(Paragraph("Key Projects", h_style))
    for proj in RESUME_DATA["projects"]:
        for line in proj.splitlines():
            story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 4))

    # Certifications
    story.append(Paragraph("Certifications", h_style))
    for line in RESUME_DATA["certifications"].splitlines():
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 6))

    # Achievements
    story.append(Paragraph("Achievements & Honors", h_style))
    for line in RESUME_DATA["achievements"].splitlines():
        story.append(Paragraph(line, body_style))

    doc.build(story)
    print(f"Generated PDF resume: {output_path}")


if __name__ == "__main__":
    generate_docx(SAMPLES_DIR / "sample_resume.docx")
    generate_pdf(SAMPLES_DIR / "sample_resume.pdf")
