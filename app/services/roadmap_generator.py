"""
Stage 6: Personalized Career Learning Roadmap Service for CareerLens AI.

Generates a realistic, highly personalized learning roadmap based ONLY on skills
that are actually missing or weak for the target job description.

Roadmap Structure:
- Phase 1 — High Priority: Skills that are important for the target job and currently missing or weak.
- Phase 2 — Medium Priority: Useful skills that improve overall job readiness.
- Phase 3 — Optional / Nice-to-Have: Preferred skills that are not essential.

Key Requirements & Constraints:
- Never recommend a skill simply because it is popular.
- Do not recommend skills already clearly demonstrated in the resume unless the JD requires a higher level.
- Do not invent user experience.
- Do not promise that completing the roadmap guarantees a job.
- Do not use fake course links or fake certifications.
- Keep recommendations understandable for beginners.
"""

from typing import Dict, Any, List, Optional, Set
import re
from app.services.matcher import ResumeJobMatcher
from app.services.skill_gap_analyzer import SkillGapAnalyzer


class RoadmapError(Exception):
    """Custom exception raised for invalid inputs in RoadmapGenerator."""
    def __init__(self, message: str, code: str = "ROADMAP_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class RoadmapGenerator:
    """
    Synthesizes real outputs from resume parsing, JD analysis, matching,
    and skill gap analysis into a prioritized, 3-phase career roadmap.
    """

    # Knowledge Base: Curated beginner-friendly, concrete, actionable learning steps
    CURATED_ROADMAP_DETAILS: Dict[str, Dict[str, Any]] = {
        "Kafka": {
            "category": "Messaging & Event Streaming",
            "beginner_steps": [
                "Understand event streaming fundamentals: topics, partitions, broker clusters, producer/consumer models, and consumer offsets.",
                "Spin up a local single-node Kafka and Zookeeper/KRaft container using Docker Compose and publish test events via the CLI.",
                "Write a Python script using 'kafka-python' or 'confluent-kafka' to produce JSON events and process them with an asynchronous consumer worker."
            ],
            "intermediate_steps": [
                "Implement consumer group scaling, commit strategies (at-least-once vs at-most-once), and dead-letter queues (DLQ) for failed message handling.",
                "Build an event-driven microservice workflow where an order creation event triggers inventory reservations and notifications asynchronously.",
                "Configure Kafka schema registry with Apache Avro to enforce strict message payload contracts across services."
            ],
            "estimated_effort": "2–3 weeks (12–16 hours)",
            "why_recommended": "Core event streaming technology listed as a mandatory requirement for high-throughput, decoupled microservices.",
            "official_reference": "Apache Kafka Official Documentation & Quickstart (kafka.apache.org)"
        },
        "Kubernetes": {
            "category": "DevOps & Cloud",
            "beginner_steps": [
                "Learn container orchestration fundamentals: Pods, Deployments, Services (ClusterIP/NodePort), and Namespaces using Minikube or Kind.",
                "Write declarative YAML manifests to deploy a containerized web application with environment variables and ConfigMaps.",
                "Expose your deployment locally, execute rolling updates, and observe pod recreation during version rollouts."
            ],
            "intermediate_steps": [
                "Configure PersistentVolumeClaims (PVC), Secret management, and Horizontal Pod Autoscalers (HPA) driven by CPU/memory thresholds.",
                "Package your application manifests into a modular, versioned Helm chart with customizable values.yaml configurations.",
                "Deploy an Ingress Controller (NGINX or Traefik) with path-based routing and simulated TLS termination."
            ],
            "estimated_effort": "3–4 weeks (15–20 hours)",
            "why_recommended": "Industry standard for container deployment, service discovery, and automated horizontal scaling.",
            "official_reference": "Kubernetes Official Tutorials (kubernetes.io/docs/tutorials)"
        },
        "Docker": {
            "category": "DevOps & Cloud",
            "beginner_steps": [
                "Understand containerization primitives: images, containers, daemon lifecycle, and how containers isolate dependencies from the host OS.",
                "Write an optimized Dockerfile for your application using lightweight base images (e.g. python:3.11-slim) and .dockerignore.",
                "Use Docker Compose to run a multi-service development stack combining your backend application and a PostgreSQL database."
            ],
            "intermediate_steps": [
                "Implement multi-stage Docker builds to separate compile-time dependencies from the final production runtime image.",
                "Manage persistent data using named Docker volumes and configure isolated bridge networks for inter-container communication.",
                "Inspect security vulnerabilities using 'docker scout' or 'trivy' and resolve insecure package layers."
            ],
            "estimated_effort": "1–2 weeks (8–10 hours)",
            "why_recommended": "Foundational container standard that guarantees development and production environment parity.",
            "official_reference": "Docker Documentation & Getting Started Guide (docs.docker.com)"
        },
        "PostgreSQL": {
            "category": "Databases",
            "beginner_steps": [
                "Install PostgreSQL locally or run via Docker; master relational modeling, primary/foreign key constraints, and standard data types.",
                "Write complex SQL queries involving INNER/LEFT JOINs, GROUP BY aggregations, HAVING filters, and transaction boundaries (BEGIN/COMMIT).",
                "Connect your application via an ORM or driver (e.g. psycopg, SQLAlchemy) with connection pooling and parameterized queries."
            ],
            "intermediate_steps": [
                "Profile query execution using EXPLAIN (ANALYZE, BUFFERS) to detect sequential scans and optimize performance with B-Tree and compound indexes.",
                "Implement database schema migrations using tools like Alembic or Flyway to maintain version-controlled database state.",
                "Explore advanced PostgreSQL capabilities including JSONB indexing, window functions, and transaction isolation levels."
            ],
            "estimated_effort": "2 weeks (10–12 hours)",
            "why_recommended": "Leading enterprise relational database for transactional integrity, complex relational querying, and reliable data persistence.",
            "official_reference": "PostgreSQL Official Documentation (postgresql.org/docs)"
        },
        "MySQL": {
            "category": "Databases",
            "beginner_steps": [
                "Set up MySQL locally; master relational schema creation, table constraints, and basic CRUD operations.",
                "Practice writing multi-table JOINs, subqueries, and aggregation functions on real-world datasets.",
                "Integrate MySQL into a backend web application using parameterized queries to prevent SQL injection."
            ],
            "intermediate_steps": [
                "Analyze query execution plans with EXPLAIN and design optimal composite indexes for WHERE and ORDER BY clauses.",
                "Study InnoDB storage engine architecture, transaction logs (redo/undo), and row-level locking mechanisms.",
                "Implement automated database backups, replica configurations, and connection pool tuning."
            ],
            "estimated_effort": "1–2 weeks (8–10 hours)",
            "why_recommended": "Widely deployed relational database powering web applications, ecommerce systems, and transactional microservices.",
            "official_reference": "MySQL Reference Manual (dev.mysql.com/doc)"
        },
        "MongoDB": {
            "category": "Databases",
            "beginner_steps": [
                "Understand NoSQL document-oriented architecture: collections, BSON documents, dynamic schemas, and embedded vs referenced models.",
                "Set up MongoDB Atlas or a local Docker instance and perform CRUD operations using the Mongo shell and native language driver (PyMongo / Mongoose).",
                "Implement single-field and compound indexes to accelerate frequent document lookups."
            ],
            "intermediate_steps": [
                "Build complex multi-stage data transformations using the MongoDB Aggregation Pipeline ($match, $group, $lookup, $unwind).",
                "Benchmark query performance using .explain('executionStats') and optimize slow document scans.",
                "Implement document schema validation rules using JSON Schema within MongoDB."
            ],
            "estimated_effort": "1–2 weeks (8–12 hours)",
            "why_recommended": "Flexible document database ideal for unstructured data, dynamic catalog models, and rapid schema evolution.",
            "official_reference": "MongoDB University & Official Docs (mongodb.com/docs)"
        },
        "Redis": {
            "category": "Databases",
            "beginner_steps": [
                "Understand in-memory data structures: Strings, Hashes, Lists, Sets, and Sorted Sets.",
                "Run Redis locally and execute basic key-value operations with TTL (time-to-live) expiration policies.",
                "Implement a cache-aside pattern in a web service to cache expensive database queries and verify cache hit/miss behavior."
            ],
            "intermediate_steps": [
                "Implement a sliding-window distributed rate limiter and session storage module using Redis Hashes.",
                "Configure Redis as a reliable message broker or task queue backend using Celery or BullMQ.",
                "Explore atomic transactions (MULTI/EXEC) and Redis Pub/Sub for lightweight broadcast notifications."
            ],
            "estimated_effort": "1 week (6–8 hours)",
            "why_recommended": "Ultra-low latency in-memory data store essential for caching, rate limiting, and session management.",
            "official_reference": "Redis Official Documentation & University (redis.io/docs)"
        },
        "GraphQL": {
            "category": "Web Services & APIs",
            "beginner_steps": [
                "Understand the core GraphQL paradigm: Schemas, Types, Queries, Mutations, and how it solves over-fetching and under-fetching.",
                "Build a simple GraphQL server using Apollo Server, Strawberry, or Graphene defining types and basic resolver functions.",
                "Query your GraphQL endpoint using Apollo Sandbox or GraphiQL, testing field selection and input arguments."
            ],
            "intermediate_steps": [
                "Solve the N+1 database query problem using DataLoader batching and caching techniques.",
                "Implement schema authentication, query complexity limits, and field-level permission checks.",
                "Set up real-time subscriptions using WebSockets for live event notifications."
            ],
            "estimated_effort": "1–2 weeks (8–10 hours)",
            "why_recommended": "Modern API query language that allows clients to request exactly the data they need in a single network round-trip.",
            "official_reference": "GraphQL Official Documentation (graphql.org/learn)"
        },
        "React": {
            "category": "Frameworks",
            "beginner_steps": [
                "Master JSX syntax, declarative rendering, component hierarchies, props, and fundamental hooks (useState, useEffect).",
                "Build an interactive single-page application with form inputs, conditional rendering, and dynamic list mapping.",
                "Manage asynchronous API fetches cleanly with dedicated loading spinners and error state boundaries."
            ],
            "intermediate_steps": [
                "Implement centralized client state management using modern tools like Zustand, Redux Toolkit, or React Context.",
                "Master performance optimization hooks (useMemo, useCallback) and identify unnecessary re-renders with React DevTools.",
                "Structure reusable UI component libraries with accessible keyboard navigation and ARIA attributes."
            ],
            "estimated_effort": "2–3 weeks (12–16 hours)",
            "why_recommended": "Dominant frontend UI library for building scalable, responsive web applications and component-driven user interfaces.",
            "official_reference": "React Official Documentation (react.dev)"
        },
        "TypeScript": {
            "category": "Languages",
            "beginner_steps": [
                "Understand static typing benefits: primitive types, type inference, interfaces, and type aliases.",
                "Set up a tsconfig.json project with strict mode enabled and convert a small JavaScript module to clean TypeScript.",
                "Define explicit types for function parameters, return values, and asynchronous Promise responses without using 'any'."
            ],
            "intermediate_steps": [
                "Master advanced type system features: union and intersection types, generics, keyof operators, and type guards.",
                "Utilize built-in utility types (Partial, Pick, Omit, Record) to create flexible, DRY data contracts.",
                "Configure strict linting and automated type-checking in your CI pipeline using 'tsc --noEmit'."
            ],
            "estimated_effort": "1–2 weeks (8–10 hours)",
            "why_recommended": "Ensures compile-time type safety, eliminates common runtime bugs, and facilitates large-scale refactoring in enterprise codebases.",
            "official_reference": "TypeScript Handbook (typescriptlang.org/docs)"
        },
        "FastAPI": {
            "category": "Frameworks",
            "beginner_steps": [
                "Understand FastAPI's async architecture, automatic OpenAPI/Swagger documentation, and Python type hint integration.",
                "Build a RESTful API with path parameters, query parameters, and Pydantic request/response validation schemas.",
                "Write automated test cases using pytest and Starlette's TestClient to verify API responses."
            ],
            "intermediate_steps": [
                "Implement dependency injection for database sessions, JWT authentication, and configuration management.",
                "Configure asynchronous background tasks and custom middleware for request logging and timing.",
                "Containerize and deploy the FastAPI application with Uvicorn and Gunicorn worker processes."
            ],
            "estimated_effort": "1–2 weeks (8–10 hours)",
            "why_recommended": "High-performance Python web framework ideal for building async microservices with built-in data validation and documentation.",
            "official_reference": "FastAPI Official Documentation (fastapi.tiangolo.com)"
        },
        "Amazon Web Services (AWS)": {
            "category": "DevOps & Cloud",
            "beginner_steps": [
                "Understand cloud computing fundamentals and core AWS services: EC2 (compute), S3 (object storage), IAM (identity & access), and VPC (networking).",
                "Create a secure IAM user following the principle of least privilege and configure the AWS CLI on your local machine.",
                "Deploy a containerized application to AWS ECS (Fargate) or AWS App Runner behind a load balancer."
            ],
            "intermediate_steps": [
                "Configure an Amazon RDS PostgreSQL database inside private VPC subnets with automated snapshots and multi-AZ failover.",
                "Implement serverless microservices using AWS Lambda and API Gateway triggered by S3 or SQS events.",
                "Provision reproducible cloud infrastructure using Infrastructure as Code (Terraform or AWS CloudFormation)."
            ],
            "estimated_effort": "3–4 weeks (15–20 hours)",
            "why_recommended": "Market-leading cloud platform required for architecting, deploying, and managing scalable distributed applications.",
            "official_reference": "AWS Skill Builder & Official Documentation (aws.amazon.com/getting-started)"
        },
        "CI/CD": {
            "category": "DevOps & Cloud",
            "beginner_steps": [
                "Understand Continuous Integration and Continuous Deployment principles: automated testing, linting, build pipelines, and release stages.",
                "Create a GitHub Actions or GitLab CI workflow YAML file that triggers on every pull request to run unit tests and linters.",
                "Configure workflow status badges and enforce branch protection rules preventing merges on failed pipeline runs."
            ],
            "intermediate_steps": [
                "Automate multi-stage Docker image builds, tag generation, and container image publishing to a container registry.",
                "Configure automated deployment to staging and production environments using environment secrets and approval gates.",
                "Implement rollback strategies and automated smoke testing post-deployment."
            ],
            "estimated_effort": "1 week (6–8 hours)",
            "why_recommended": "Automates testing and deployment workflows, preventing code regressions and accelerating delivery cycles.",
            "official_reference": "GitHub Actions Documentation (docs.github.com/en/actions)"
        }
    }

    @classmethod
    def _determine_learning_level(
        cls,
        skill_name: str,
        current_status: str,
        candidate_skills: Set[str],
        job_analysis: Dict[str, Any]
    ) -> str:
        """
        Determines the recommended learning level for a skill:
        - Beginner: Missing from scratch with no related technical foundation.
        - Intermediate: Candidate already has a verified related skill (transferable conceptual foundation),
          or the match is weak (has superficial familiarity, needs practical project depth).
        - Advanced: Senior-level roles where candidate already has intermediate foundation and needs
          production scaling, high-concurrency, or architectural mastery.
        """
        is_senior_role = False
        exp_req = job_analysis.get("experience", {}) or {}
        min_years = exp_req.get("min_years") or 0
        job_title = (job_analysis.get("job_title") or "").lower()
        if min_years >= 5 or any(term in job_title for term in ["senior", "lead", "staff", "principal", "architect"]):
            is_senior_role = True

        if current_status == "Related skill found":
            return "Intermediate"
        elif current_status == "Weak":
            return "Advanced" if is_senior_role else "Intermediate"
        else:
            # Completely missing
            # If candidate has 5+ related technical skills in the same family, recommend Intermediate; otherwise Beginner
            category = ResumeJobMatcher.SKILL_CATEGORIES.get(skill_name, "")
            family_matches = sum(1 for s in candidate_skills if ResumeJobMatcher.SKILL_CATEGORIES.get(s) == category)
            if family_matches >= 2 and is_senior_role:
                return "Intermediate"
            return "Beginner"

    @classmethod
    def _synthesize_steps(
        cls,
        skill_name: str,
        category: str,
        level: str,
        status: str,
        related_skill: Optional[str] = None
    ) -> List[str]:
        """
        Provides beginner-friendly, concrete, 3-step action steps.
        Uses curated knowledge base where available, or synthesizes structured steps based on category and level.
        """
        curated = cls.CURATED_ROADMAP_DETAILS.get(skill_name)
        if curated:
            if level == "Beginner" and "beginner_steps" in curated:
                return curated["beginner_steps"]
            elif level in ("Intermediate", "Advanced") and "intermediate_steps" in curated:
                return curated["intermediate_steps"]

        # Context-aware synthesizer for uncataloged skills
        cat_lower = category.lower()
        if related_skill:
            step_1 = f"Leverage your existing foundation in '{related_skill}' to study how '{skill_name}' approaches core architecture, syntax, and workflow design."
            step_2 = f"Build a practical mini-project translating a component from '{related_skill}' to '{skill_name}' to master the delta."
            step_3 = f"Document performance comparisons and configuration nuances between '{related_skill}' and '{skill_name}' to showcase during technical interviews."
            return [step_1, step_2, step_3]

        if "database" in cat_lower or "data" in cat_lower:
            step_1 = f"Learn {skill_name} data modeling fundamentals, primary indexing strategies, and basic query execution."
            step_2 = f"Run a local instance and build a CRUD service integrating {skill_name} with your preferred programming language."
            step_3 = f"Implement query profiling, connection pooling, and benchmark response latency under simulated load."
        elif "devops" in cat_lower or "cloud" in cat_lower:
            step_1 = f"Understand core architecture and operational primitives of {skill_name} via official quickstart guides."
            step_2 = f"Configure a reproducible local sandbox or automated pipeline incorporating {skill_name} into a web service."
            step_3 = f"Implement observability, security least-privilege policies, and failover routines."
        elif "language" in cat_lower:
            step_1 = f"Master core syntax, data structures, and idiomatic conventions of {skill_name} using official documentation."
            step_2 = f"Write a functional utility or command-line tool with comprehensive unit test coverage."
            step_3 = f"Build a small backend or data processing service adhering to clean architecture principles."
        else:
            step_1 = f"Review official documentation and core principles of {skill_name}; establish a working local development environment."
            step_2 = f"Develop a targeted proof-of-concept project demonstrating configuration, standard workflows, and error handling."
            step_3 = f"Integrate automated unit tests and summarize your implementation in a portfolio repository bullet point."

        return [step_1, step_2, step_3]

    @classmethod
    def _build_next_step(cls, top_skill: Optional[Dict[str, Any]], target_job_title: str) -> Dict[str, Any]:
        """
        Creates the 'Recommended Next Step' callout card highlighting the single
        highest-priority skill to begin working on immediately.
        """
        if not top_skill:
            return {
                "skill_name": "System Architecture & Mock Interviews",
                "priority": "High",
                "current_status": "All Requirements Met",
                "recommended_level": "Advanced",
                "headline": f"Ready for {target_job_title}: Polish System Design & Behavioral Interview Stories",
                "why": "Your resume already covers the required technical competencies for this role. Maximize your chances by rehearsing system architecture trade-offs and STAR-method behavioral examples.",
                "immediate_action": "Conduct a 45-minute mock technical interview focusing on architectural scaling and end-to-end reliability for your recent projects.",
                "estimated_effort": "1 week (5–7 hours)"
            }

        name = top_skill["skill_name"]
        status = top_skill["current_status"]
        level = top_skill["recommended_level"]
        steps = top_skill.get("learning_steps", [])
        first_step = steps[0] if steps else f"Review official {name} documentation and set up a local practice environment."

        if status == "Related skill found":
            why = f"High-impact requirement for {target_job_title}. Because you already understand related concepts, bridging to '{name}' gives you the quickest qualification win."
        elif status == "Weak":
            why = f"'{name}' is listed in your skills overview but lacks evidence in work experience. Adding a measurable achievement bullet transforms this from a question mark to a strength."
        else:
            why = f"Essential requirement listed for {target_job_title} with zero verified evidence on your resume. Addressing this foundational gap first yields the highest return on recruiter screening."

        return {
            "skill_name": name,
            "priority": top_skill["priority"],
            "current_status": status,
            "recommended_level": level,
            "headline": f"Start Here: Master {name} Fundamentals",
            "why": why,
            "immediate_action": first_step,
            "estimated_effort": top_skill.get("estimated_effort", "1–2 weeks (8–10 hours)")
        }

    @classmethod
    def _generate_why_this_roadmap(
        cls,
        target_job_title: str,
        total_gaps: int,
        high_count: int,
        med_count: int,
        low_count: int,
        matched_skills: List[str]
    ) -> str:
        """
        Dynamically explains how the roadmap was produced from user's resume and JD,
        emphasizing that verified skills were omitted and disclaiming job guarantees.
        """
        sample_matched = ", ".join(matched_skills[:4]) if matched_skills else "none detected"
        more_text = f" and {len(matched_skills) - 4} others" if len(matched_skills) > 4 else ""

        if total_gaps == 0:
            return (
                f"This roadmap evaluated your resume against the '{target_job_title}' requirements and found that your "
                f"verified qualifications match all specified technical criteria. Rather than prescribing artificial coursework, "
                f"your plan focuses on interview storytelling, deep architecture trade-offs, and portfolio presentation. "
                f"Disclaimer: Technical alignment significantly boosts interview conversion, but hiring decisions depend on overall candidate evaluation."
            )

        return (
            f"This personalized roadmap was dynamically synthesized by analyzing '{target_job_title}' requirements "
            f"against your uploaded resume. It isolates {total_gaps} actionable gap areas: {high_count} critical "
            f"requirements, {med_count} core readiness tools, and {low_count} optional enhancements. "
            f"Competencies already verified in your resume ({sample_matched}{more_text}) were intentionally excluded "
            f"so you invest 100% of your interview preparation time where it moves the needle most. "
            f"Disclaimer: Completing this roadmap improves role alignment and interview readiness; it is not an employment guarantee."
        )

    @classmethod
    def generate(
        cls,
        parsed_resume: Dict[str, Any],
        job_analysis: Dict[str, Any],
        match_result: Optional[Dict[str, Any]] = None,
        skill_gap_analysis: Optional[Dict[str, Any]] = None,
        ats_analysis: Optional[Dict[str, Any]] = None,
        target_job_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for Stage 6: Personalized Career Learning Roadmap.
        Accepts real results from parsing, JD analysis, matching, gap analysis, and ATS audit.
        Returns a structured, 3-phase roadmap based ONLY on actually missing or weak skills.
        """
        if parsed_resume is None or not isinstance(parsed_resume, dict):
            raise RoadmapError("Missing or invalid parsed_resume payload.", code="MISSING_PARSED_RESUME")
        if job_analysis is None or not isinstance(job_analysis, dict):
            raise RoadmapError("Missing or invalid job_analysis payload.", code="MISSING_JD_ANALYSIS")

        resolved_title = target_job_title or job_analysis.get("job_title") or "Target Role"

        # Compute dependencies if not pre-provided
        if match_result is None or not isinstance(match_result, dict):
            match_result = ResumeJobMatcher.match(parsed_resume, job_analysis)

        if skill_gap_analysis is None or not isinstance(skill_gap_analysis, dict):
            skill_gap_analysis = SkillGapAnalyzer.analyze(match_result, job_analysis, parsed_resume)

        # Candidate verified skills
        candidate_stats = match_result.get("candidate_stats", {})
        candidate_skills: Set[str] = set(candidate_stats.get("candidate_skills", []))
        if not candidate_skills:
            candidate_skills = ResumeJobMatcher.extract_candidate_skills(parsed_resume)

        matched_skills_list = [m.get("name", "") for m in match_result.get("matched_skills", []) if m.get("name")]

        # Map transferable bridges for quick lookup
        transferable_bridges: Dict[str, Dict[str, Any]] = {}
        for bridge in skill_gap_analysis.get("partially_satisfied_requirements", []):
            target = bridge.get("target_skill")
            if target:
                transferable_bridges[target] = bridge

        # Map weak matches for quick lookup
        weak_matches_map: Dict[str, Dict[str, Any]] = {}
        for weak in skill_gap_analysis.get("weak_matches", []):
            name = weak.get("name")
            if name:
                weak_matches_map[name] = weak

        # Accumulator for all recommended skills (deduplicated by skill_name)
        recommended_skills: Dict[str, Dict[str, Any]] = {}

        # ---------------------------------------------------------------------
        # 1. Process Missing Required Skills (High Priority)
        # ---------------------------------------------------------------------
        for item in skill_gap_analysis.get("missing_required_skills", []):
            skill_name = item.get("name")
            if not skill_name:
                continue

            category = item.get("category") or ResumeJobMatcher.SKILL_CATEGORIES.get(skill_name, "Technical Competency")
            bridge = transferable_bridges.get(skill_name)
            weak = weak_matches_map.get(skill_name)

            if bridge:
                status = "Related skill found"
                cand_skill = bridge.get("candidate_skill", "related technology")
                reason = f"Essential requirement for {resolved_title}. You possess related experience in '{cand_skill}', which provides a conceptual bridge."
                prereq_bridge = {
                    "has_bridge": True,
                    "candidate_skill": cand_skill,
                    "transferable_concepts": bridge.get("transferable_concepts", ""),
                    "delta_to_bridge": bridge.get("delta_to_bridge", "")
                }
            elif weak:
                status = "Weak"
                cand_skill = None
                reason = f"Essential requirement for {resolved_title}. Listed on your resume but lacks practical evidence or measurable impact."
                prereq_bridge = {"has_bridge": False}
            else:
                status = "Missing"
                cand_skill = None
                reason = f"Core non-negotiable requirement for {resolved_title} with zero evidence detected on your resume."
                prereq_bridge = {"has_bridge": False}

            level = cls._determine_learning_level(skill_name, status, candidate_skills, job_analysis)
            steps = cls._synthesize_steps(skill_name, category, level, status, cand_skill)
            curated = cls.CURATED_ROADMAP_DETAILS.get(skill_name, {})
            effort = curated.get("estimated_effort", "2 weeks (10–12 hours)")
            official_ref = curated.get("official_reference")

            recommended_skills[skill_name] = {
                "skill_name": skill_name,
                "priority": "High",
                "relevance": "Required",
                "category": category,
                "reason": reason,
                "current_status": status,
                "recommended_level": level,
                "learning_steps": steps,
                "estimated_effort": effort,
                "prerequisite_bridge": prereq_bridge,
                "official_reference": official_ref
            }

        # ---------------------------------------------------------------------
        # 2. Process Weak Required Matches not yet added
        # ---------------------------------------------------------------------
        for name, weak in weak_matches_map.items():
            if name in recommended_skills:
                continue

            relevance = weak.get("relevance", "Required")
            priority = "High" if relevance == "Required" else "Medium"
            category = ResumeJobMatcher.SKILL_CATEGORIES.get(name, "Technical Competency")
            status = "Related skill found" if weak.get("match_type") == "related_skill" else "Weak"
            bridge = transferable_bridges.get(name)
            cand_skill = bridge.get("candidate_skill") if bridge else weak.get("matched_via")

            reason = weak.get("why_weak") or f"Identified as weak for {resolved_title}; needs practical reinforcement."
            level = cls._determine_learning_level(name, status, candidate_skills, job_analysis)
            steps = cls._synthesize_steps(name, category, level, status, cand_skill)
            curated = cls.CURATED_ROADMAP_DETAILS.get(name, {})
            effort = curated.get("estimated_effort", "1–2 weeks (8–10 hours)")
            official_ref = curated.get("official_reference")

            prereq_bridge = {
                "has_bridge": bool(bridge or cand_skill),
                "candidate_skill": cand_skill,
                "transferable_concepts": bridge.get("transferable_concepts", "") if bridge else "",
                "delta_to_bridge": bridge.get("delta_to_bridge", "") if bridge else ""
            }

            recommended_skills[name] = {
                "skill_name": name,
                "priority": priority,
                "relevance": relevance,
                "category": category,
                "reason": reason,
                "current_status": status,
                "recommended_level": level,
                "learning_steps": steps,
                "estimated_effort": effort,
                "prerequisite_bridge": prereq_bridge,
                "official_reference": official_ref
            }

        # ---------------------------------------------------------------------
        # 3. Process Missing Preferred Skills (Medium / Low Priority)
        # ---------------------------------------------------------------------
        for item in skill_gap_analysis.get("missing_preferred_skills", []):
            skill_name = item.get("name")
            if not skill_name or skill_name in recommended_skills:
                continue

            category = item.get("category") or ResumeJobMatcher.SKILL_CATEGORIES.get(skill_name, "Technical Competency")
            bridge = transferable_bridges.get(skill_name)
            priority = item.get("priority", "Medium")

            if bridge:
                status = "Related skill found"
                cand_skill = bridge.get("candidate_skill", "related technology")
                reason = f"Preferred qualification for {resolved_title}. Your experience in '{cand_skill}' can be leveraged for a quick transition."
                prereq_bridge = {
                    "has_bridge": True,
                    "candidate_skill": cand_skill,
                    "transferable_concepts": bridge.get("transferable_concepts", ""),
                    "delta_to_bridge": bridge.get("delta_to_bridge", "")
                }
            else:
                status = "Missing"
                cand_skill = None
                reason = f"Preferred / nice-to-have qualification for {resolved_title} that strengthens your job readiness."
                prereq_bridge = {"has_bridge": False}

            level = cls._determine_learning_level(skill_name, status, candidate_skills, job_analysis)
            steps = cls._synthesize_steps(skill_name, category, level, status, cand_skill)
            curated = cls.CURATED_ROADMAP_DETAILS.get(skill_name, {})
            effort = curated.get("estimated_effort", "1–2 weeks (6–8 hours)")
            official_ref = curated.get("official_reference")

            recommended_skills[skill_name] = {
                "skill_name": skill_name,
                "priority": priority,
                "relevance": "Preferred",
                "category": category,
                "reason": reason,
                "current_status": status,
                "recommended_level": level,
                "learning_steps": steps,
                "estimated_effort": effort,
                "prerequisite_bridge": prereq_bridge,
                "official_reference": official_ref
            }

        # ---------------------------------------------------------------------
        # 4. Filter Guard: Strictly NEVER recommend skills already verified in resume
        # ---------------------------------------------------------------------
        # An exact match with solid evidence should NEVER appear in the roadmap
        final_skills_list: List[Dict[str, Any]] = []
        for name, item in recommended_skills.items():
            # If the user has this skill verified exactly and it's NOT flagged as weak or related, omit it
            if name in candidate_skills and item["current_status"] not in ("Weak", "Related skill found"):
                continue
            final_skills_list.append(item)

        # ---------------------------------------------------------------------
        # 5. Suggested Learning Sequence & Phase Organization
        # ---------------------------------------------------------------------
        # Sorting order:
        # Priority: High -> Medium -> Low
        # Status within priority: Missing required -> Related bridge -> Weak
        priority_rank = {"High": 0, "Medium": 1, "Low": 2}
        status_rank = {"Missing": 0, "Related skill found": 1, "Weak": 2}

        final_skills_list.sort(key=lambda s: (
            priority_rank.get(s["priority"], 3),
            status_rank.get(s["current_status"], 3),
            s["skill_name"]
        ))

        # Assign suggested sequence numbers (1, 2, 3...)
        for idx, skill in enumerate(final_skills_list, start=1):
            skill["suggested_sequence"] = idx

        # Partition into 3 distinct phases
        phase_1_skills = [s for s in final_skills_list if s["priority"] == "High"]
        phase_2_skills = [s for s in final_skills_list if s["priority"] == "Medium"]
        phase_3_skills = [s for s in final_skills_list if s["priority"] == "Low"]

        phases = [
            {
                "phase_number": 1,
                "phase_name": "Phase 1: High Priority (Critical Requirements)",
                "description": "Address essential skills that are important for the target job and currently missing or weak.",
                "badge_class": "badge-danger",
                "skill_count": len(phase_1_skills),
                "skills": phase_1_skills
            },
            {
                "phase_number": 2,
                "phase_name": "Phase 2: Medium Priority (Core Job Readiness)",
                "description": "Useful competencies that significantly improve job readiness and round out your engineering profile.",
                "badge_class": "badge-warning",
                "skill_count": len(phase_2_skills),
                "skills": phase_2_skills
            },
            {
                "phase_number": 3,
                "phase_name": "Phase 3: Optional / Nice-to-Have (Competitive Edge)",
                "description": "Preferred skills and auxiliary tooling that distinguish your application without being mandatory.",
                "badge_class": "badge-neutral",
                "skill_count": len(phase_3_skills),
                "skills": phase_3_skills
            }
        ]

        # Top Recommended Next Step
        top_skill = final_skills_list[0] if final_skills_list else None
        recommended_next_step = cls._build_next_step(top_skill, resolved_title)

        # "Why this roadmap?" explanation
        why_this_roadmap = cls._generate_why_this_roadmap(
            target_job_title=resolved_title,
            total_gaps=len(final_skills_list),
            high_count=len(phase_1_skills),
            med_count=len(phase_2_skills),
            low_count=len(phase_3_skills),
            matched_skills=matched_skills_list
        )

        return {
            "success": True,
            "target_job_title": resolved_title,
            "total_recommended_skills": len(final_skills_list),
            "recommended_next_step": recommended_next_step,
            "why_this_roadmap": why_this_roadmap,
            "phases": phases,
            "all_recommended_skills": final_skills_list,
            "disclaimer": "This roadmap is provided for interview preparation and skills development. Completing these milestones improves qualification alignment, but hiring decisions remain at the employer's sole discretion."
        }
