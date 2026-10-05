"""
Sample analysis data provider for CareerLens (Stage 1).
Provides high-fidelity, realistic structured data for dashboard preview
and history simulation until Stage 2 NLP and AI models are integrated.
"""

from datetime import datetime, timedelta

def get_sample_analysis(job_title="Senior Full Stack Engineer", company="Starlight Technologies"):
    """Returns a rich, production-like analysis report structure."""
    return {
        "id": "analysis-sample-001",
        "job_title": job_title or "Senior Full Stack Engineer",
        "company": company or "Starlight Technologies",
        "analyzed_at": datetime.now().strftime("%b %d, %Y - %I:%M %p"),
        "resume_filename": "Alex_Morgan_Resume_2026.pdf",
        "resume_size_kb": 142,
        "is_preview": True,
        
        # Core Scores (0 - 100)
        "scores": {
            "overall_match": 78,
            "skills_match": 84,
            "experience_relevance": 72,
            "keyword_coverage": 76,
            "ats_compatibility": 88
        },
        "score_verdict": {
            "label": "Strong Candidate Match",
            "summary": "Your profile demonstrates strong alignment with backend and full-stack fundamentals, with minor gaps in container orchestration and declarative APIs.",
            "color_class": "badge-success"
        },
        
        # ATS Check Details
        "ats_checklist": [
            {
                "id": "file_format",
                "title": "Machine-Readable File Format",
                "status": "pass",
                "details": "Document text layer verified. Clean text stream detected without image-only rasterization."
            },
            {
                "id": "section_headers",
                "title": "Standard Section Headings",
                "status": "pass",
                "details": "Recognized 5 standard headers: Summary, Experience, Education, Skills, and Projects."
            },
            {
                "id": "contact_info",
                "title": "Essential Contact Anchors",
                "status": "pass",
                "details": "Verified email, phone, location, and GitHub/LinkedIn URLs in header block."
            },
            {
                "id": "density",
                "title": "Keyword Density & Readability",
                "status": "warning",
                "details": "Recommended density is 2.5-4%. Found 1.9% target keyword frequency in experience section."
            },
            {
                "id": "visual_elements",
                "title": "Tables, Columns & Complex Graphics",
                "status": "pass",
                "details": "No multi-column nesting, icons, or text boxes that disrupt traditional ATS scanners."
            }
        ],
        
        # Matched Skills Breakdown
        "matched_skills": [
            {"name": "Python", "category": "Languages", "proficiency": "Advanced", "relevance": "Core Requirement"},
            {"name": "JavaScript / TypeScript", "category": "Languages", "proficiency": "Advanced", "relevance": "Core Requirement"},
            {"name": "SQL & PostgreSQL", "category": "Databases", "proficiency": "Intermediate", "relevance": "Core Requirement"},
            {"name": "React.js", "category": "Frameworks", "proficiency": "Advanced", "relevance": "Core Requirement"},
            {"name": "Flask / FastAPI", "category": "Frameworks", "proficiency": "Intermediate", "relevance": "Preferred"},
            {"name": "RESTful API Design", "category": "Architecture", "proficiency": "Advanced", "relevance": "Core Requirement"},
            {"name": "Docker", "category": "DevOps", "proficiency": "Intermediate", "relevance": "Preferred"},
            {"name": "Git & CI/CD Workflows", "category": "DevOps", "proficiency": "Advanced", "relevance": "Core Requirement"},
            {"name": "Agile / Scrum Methodologies", "category": "Process", "proficiency": "Intermediate", "relevance": "Collaboration"}
        ],
        
        # Missing Skills with Priority
        "missing_skills": [
            {
                "name": "Kubernetes (K8s)",
                "category": "Cloud & DevOps",
                "priority": "critical",
                "frequency_in_jd": 4,
                "impact": "High - Mentioned under core production deployment responsibilities."
            },
            {
                "name": "Redis Caching",
                "category": "Databases",
                "priority": "recommended",
                "frequency_in_jd": 3,
                "impact": "Medium - Key requirement for high-throughput session state & queue architecture."
            },
            {
                "name": "GraphQL",
                "category": "API Architecture",
                "priority": "recommended",
                "frequency_in_jd": 2,
                "impact": "Medium - Listed as preferred API modernization skill."
            },
            {
                "name": "Terraform / IaC",
                "category": "Infrastructure",
                "priority": "optional",
                "frequency_in_jd": 1,
                "impact": "Low - Bonus qualification for automated cloud provisioning."
            }
        ],
        
        # Actionable Resume Improvement Suggestions
        "improvement_suggestions": [
            {
                "id": "sug-1",
                "category": "Impact & Quantification",
                "type": "high",
                "title": "Quantify Backend Engineering Achievements",
                "description": "Your current bullet points emphasize responsibilities rather than outcomes. Rephrase key points to highlight metrics (e.g., 'Refactored user authentication endpoints, reducing median API latency by 38% and supporting 15,000 daily active users')."
            },
            {
                "id": "sug-2",
                "category": "Keyword Optimization",
                "type": "high",
                "title": "Incorporate Production Containerization Context",
                "description": "The job description emphasizes containerized microservices. Expand your Docker experience bullet to mention multi-stage container builds, local testing orchestration, and environment parity."
            },
            {
                "id": "sug-3",
                "category": "ATS Structure",
                "type": "medium",
                "title": "Standardize Technical Skills Classification",
                "description": "Group your skills explicitly into 'Languages', 'Frameworks & Libraries', 'Databases', and 'Cloud/DevOps' rather than a comma-separated paragraph to increase ATS parsing accuracy."
            },
            {
                "id": "sug-4",
                "category": "Summary Alignment",
                "type": "medium",
                "title": "Tailor Professional Summary to Senior Level Scope",
                "description": "Incorporate cross-functional leadership, architectural decision-making, and code review mentorship into your opening 3-line summary to align with the 'Senior' qualification level."
            }
        ],
        
        # Structured Learning Roadmap
        "learning_roadmap": [
            {
                "phase": 1,
                "phase_title": "Core Missing Competency: Container Orchestration",
                "target_skill": "Kubernetes (K8s)",
                "duration_weeks": "Weeks 1–2",
                "estimated_hours": 12,
                "milestones": [
                    "Master Pods, ReplicaSets, Deployments, and Services in Minikube / Kind",
                    "Configure ConfigMaps, Secrets, and Ingress controllers for multi-tier apps",
                    "Understand rolling updates, readiness probes, and liveness health checks"
                ],
                "recommended_resource": "Official Kubernetes Documentation & interactive tutorials"
            },
            {
                "phase": 2,
                "phase_title": "High-Throughput State: In-Memory Caching",
                "target_skill": "Redis & Caching Patterns",
                "duration_weeks": "Weeks 3–4",
                "estimated_hours": 8,
                "milestones": [
                    "Implement cache-aside pattern for heavy database queries in Python/Node",
                    "Manage cache invalidation strategies and TTL expiration",
                    "Configure Redis as a task queue broker with Celery or BullMQ"
                ],
                "recommended_resource": "Redis University - RU101: Introduction to Redis Data Structures"
            },
            {
                "phase": 3,
                "phase_title": "Flexible Client Queries: Modern API Paradigms",
                "target_skill": "GraphQL & Apollo Server",
                "duration_weeks": "Weeks 5–6",
                "estimated_hours": 10,
                "milestones": [
                    "Design schema definition language (SDL) with query and mutation types",
                    "Solve N+1 query performance traps using DataLoader batching",
                    "Integrate Apollo Client in React frontend with normalized cache"
                ],
                "recommended_resource": "GraphQL.org Tutorials & Apollo Odyssey"
            }
        ],

        # Stage 6: Personalized Career Roadmap
        "personalized_roadmap": {
            "success": True,
            "target_job_title": job_title or "Senior Full Stack Software Engineer",
            "total_recommended_skills": 3,
            "why_this_roadmap": "This personalized roadmap was dynamically synthesized by analyzing 'Senior Full Stack Software Engineer' requirements against your uploaded resume. It isolates 3 actionable gap areas: 1 critical requirement (Kubernetes), 1 core readiness tool (Redis), and 1 optional enhancement (GraphQL). Competencies already verified in your resume (Python, React, TypeScript, SQL, Docker) were intentionally excluded so you invest 100% of your interview preparation time where it moves the needle most. Disclaimer: Completing this roadmap improves role alignment and interview readiness; it is not an employment guarantee.",
            "recommended_next_step": {
                "skill_name": "Kubernetes",
                "priority": "High",
                "current_status": "Related skill found",
                "recommended_level": "Intermediate",
                "headline": "Start Here: Bridge Docker to Kubernetes (K8s) Cluster Orchestration",
                "why": "High-impact requirement for Senior Full Stack Engineer. Because you already understand containerization in Docker, bridging to Kubernetes orchestration yields the fastest, highest-value qualification win.",
                "immediate_action": "Set up a local Minikube cluster and convert your docker-compose service definitions into declarative Kubernetes Deployment and Service YAML manifests.",
                "estimated_effort": "2–3 weeks (12–15 hours)"
            },
            "phases": [
                {
                    "phase_number": 1,
                    "phase_name": "Phase 1: High Priority (Critical Requirements)",
                    "description": "Address essential skills that are important for the target job and currently missing or weak.",
                    "badge_class": "badge-danger",
                    "skill_count": 1,
                    "skills": [
                        {
                            "skill_name": "Kubernetes",
                            "priority": "High",
                            "relevance": "Required",
                            "category": "DevOps & Cloud",
                            "reason": "Essential requirement for Senior Full Stack Engineer. Your Docker background provides a strong foundation for container orchestration.",
                            "current_status": "Related skill found",
                            "recommended_level": "Intermediate",
                            "suggested_sequence": 1,
                            "estimated_effort": "2–3 weeks (12–15 hours)",
                            "prerequisite_bridge": {
                                "has_bridge": True,
                                "candidate_skill": "Docker",
                                "transferable_concepts": "Container image builds, runtime isolation, and multi-container environment configs.",
                                "delta_to_bridge": "Pod lifecycles, ReplicaSets, declarative Services, and Ingress routing."
                            },
                            "learning_steps": [
                                "Master Pods, ReplicaSets, Deployments, and Services in Minikube / Kind.",
                                "Configure ConfigMaps, Secrets, and Ingress controllers for multi-tier apps.",
                                "Understand rolling updates, readiness probes, and liveness health checks."
                            ],
                            "official_reference": "Kubernetes Official Tutorials (kubernetes.io/docs/tutorials)"
                        }
                    ]
                },
                {
                    "phase_number": 2,
                    "phase_name": "Phase 2: Medium Priority (Core Job Readiness)",
                    "description": "Useful competencies that significantly improve job readiness and round out your engineering profile.",
                    "badge_class": "badge-warning",
                    "skill_count": 1,
                    "skills": [
                        {
                            "skill_name": "Redis",
                            "priority": "Medium",
                            "relevance": "Preferred",
                            "category": "Databases",
                            "reason": "Preferred caching and queueing technology to build ultra-low-latency backend microservices.",
                            "current_status": "Missing",
                            "recommended_level": "Beginner",
                            "suggested_sequence": 2,
                            "estimated_effort": "1–2 weeks (8–10 hours)",
                            "prerequisite_bridge": {"has_bridge": False},
                            "learning_steps": [
                                "Understand in-memory data structures: Strings, Hashes, Lists, Sets, and Sorted Sets.",
                                "Run Redis locally and execute basic key-value operations with TTL expiration.",
                                "Implement a cache-aside pattern in a web service to cache expensive database queries."
                            ],
                            "official_reference": "Redis Official Documentation & University (redis.io/docs)"
                        }
                    ]
                },
                {
                    "phase_number": 3,
                    "phase_name": "Phase 3: Optional / Nice-to-Have (Competitive Edge)",
                    "description": "Preferred skills and auxiliary tooling that distinguish your application without being mandatory.",
                    "badge_class": "badge-neutral",
                    "skill_count": 1,
                    "skills": [
                        {
                            "skill_name": "GraphQL",
                            "priority": "Low",
                            "relevance": "Preferred",
                            "category": "Web Services & APIs",
                            "reason": "Flexible API query language that distinguishes frontend-backend data contracts.",
                            "current_status": "Missing",
                            "recommended_level": "Beginner",
                            "suggested_sequence": 3,
                            "estimated_effort": "1–2 weeks (8–10 hours)",
                            "prerequisite_bridge": {"has_bridge": False},
                            "learning_steps": [
                                "Understand schemas, types, queries, and mutations compared to REST.",
                                "Build a simple GraphQL server using Apollo Server or Strawberry with basic resolvers.",
                                "Solve the N+1 query problem using DataLoader batching."
                            ],
                            "official_reference": "GraphQL Official Documentation (graphql.org/learn)"
                        }
                    ]
                }
            ],
            "disclaimer": "This roadmap is provided for interview preparation and skills development. Completing these milestones improves qualification alignment, but hiring decisions remain at the employer's sole discretion."
        }
    }


def get_sample_history():
    """Returns sample analysis history entries."""
    now = datetime.now()
    return [
        {
            "id": "hist-001",
            "job_title": "Senior Full Stack Software Engineer",
            "company": "Starlight Technologies",
            "created_at": (now - timedelta(hours=2)).strftime("%b %d, %Y • %I:%M %p"),
            "date_iso": (now - timedelta(hours=2)).isoformat(),
            "overall_score": 78,
            "skills_score": 84,
            "ats_score": 88,
            "status": "High Match",
            "filename": "Alex_Morgan_Resume_2026.pdf"
        },
        {
            "id": "hist-002",
            "job_title": "Staff Frontend Platform Engineer",
            "company": "Veloce Cloud Systems",
            "created_at": (now - timedelta(days=1, hours=4)).strftime("%b %d, %Y • %I:%M %p"),
            "date_iso": (now - timedelta(days=1, hours=4)).isoformat(),
            "overall_score": 91,
            "skills_score": 94,
            "ats_score": 92,
            "status": "Excellent Match",
            "filename": "Alex_Morgan_Resume_2026.pdf"
        },
        {
            "id": "hist-003",
            "job_title": "DevOps & Cloud Infrastructure Specialist",
            "company": "Nordic Data Grid",
            "created_at": (now - timedelta(days=3, hours=7)).strftime("%b %d, %Y • %I:%M %p"),
            "date_iso": (now - timedelta(days=3, hours=7)).isoformat(),
            "overall_score": 58,
            "skills_score": 52,
            "ats_score": 82,
            "status": "Moderate Gap",
            "filename": "Alex_Morgan_Resume_2026.pdf"
        },
        {
            "id": "hist-004",
            "job_title": "Backend Systems Engineer (Python / Go)",
            "company": "Apex Distributed Labs",
            "created_at": (now - timedelta(days=6)).strftime("%b %d, %Y • %I:%M %p"),
            "date_iso": (now - timedelta(days=6)).isoformat(),
            "overall_score": 83,
            "skills_score": 86,
            "ats_score": 89,
            "status": "High Match",
            "filename": "Alex_Morgan_Resume_2026.pdf"
        }
    ]
