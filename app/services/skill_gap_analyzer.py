"""
Stage 5: Skill Gap Analyzer Service for CareerLens AI.
Analyzes real Resume-to-Job matching results to identify:
1. Missing Required Skills (High Priority with impact and learning directions)
2. Missing Preferred Skills (Medium/Low Priority with impact and learning directions)
3. Weak / Low-Confidence Matches (Related skill matches & shallow keyword mentions)
4. Related Skills Partially Satisfying Requirements (Transferable concepts & deltas to bridge)
5. Structured Phased Personalized Skill Gap Closure Roadmap

Constraint: Strictly relies on verified candidate skills and JD requirements.
Never invents skills or claims candidate possesses skills that are not present.
"""

from typing import Dict, Any, List, Optional, Set
import re
from app.services.matcher import ResumeJobMatcher


class SkillGapError(Exception):
    """Custom exception raised for invalid inputs in SkillGapAnalyzer."""
    def __init__(self, message: str, code: str = "SKILL_GAP_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class SkillGapAnalyzer:
    """
    Analyzes skill gaps between parsed candidate resumes and analyzed job descriptions.
    Produces prioritized missing skills, weak match diagnostics, transferable competency bridges,
    and a structured personalized learning roadmap.
    """

    # Curated Knowledge Base: Contextual Impact and Concrete Learning Directions
    CURATED_SKILL_PROFILES: Dict[str, Dict[str, Any]] = {
        "Python": {
            "why_it_matters": "Core language for backend microservices, data processing pipelines, automation scripts, and server-side APIs.",
            "learning_direction": "Deepen proficiency in type annotations (PEP 484), asynchronous programming (asyncio), pytest test coverage, and API frameworks (FastAPI/Flask).",
            "milestones": [
                "Implement asynchronous API endpoints with type hints and Pydantic validation",
                "Write comprehensive unit and integration tests using pytest and mock fixtures",
                "Profile execution bottlenecks and optimize memory usage with generators"
            ],
            "resource": "Official Python Documentation & 'Fluent Python' by Luciano Ramalho"
        },
        "JavaScript": {
            "why_it_matters": "Foundational language for full-stack and web engineering, powers interactive user interfaces and asynchronous event-driven runtimes.",
            "learning_direction": "Master modern ECMAScript (ES2022+), asynchronous promises/async-await, event loop mechanics, closures, and modular architecture.",
            "milestones": [
                "Build an event-driven DOM application utilizing ES module imports and async fetches",
                "Deepen knowledge of scope, prototypical inheritance, and microtask queue execution",
                "Implement functional array pipelines with clean immutability patterns"
            ],
            "resource": "MDN Web Docs - JavaScript Guide & 'You Don't Know JS' by Kyle Simpson"
        },
        "TypeScript": {
            "why_it_matters": "Provides compile-time type safety, robust refactoring tools, and scalable interface contracts across large enterprise codebases.",
            "learning_direction": "Master advanced TypeScript constructs including generics, union/intersection types, conditional types, mapped types, and strict tsconfig setups.",
            "milestones": [
                "Refactor vanilla JavaScript modules to strict TypeScript with zero 'any' types",
                "Design reusable generic interfaces and utility types for API payload serialization",
                "Configure automated CI linting with ESLint typescript-parser and tsc --noEmit"
            ],
            "resource": "TypeScript Handbook (typescriptlang.org) & Total TypeScript by Matt Pocock"
        },
        "React": {
            "why_it_matters": "Dominant frontend library for constructing reusable component trees, stateful client applications, and responsive single-page web apps.",
            "learning_direction": "Master React 18+ hooks (useEffect, useMemo, useCallback, useId), Context API / Zustand state management, and SSR patterns.",
            "milestones": [
                "Develop an accessible interactive dashboard using custom hooks and memoized components",
                "Implement centralized state management with Zustand or Redux Toolkit",
                "Optimize client render performance using React DevTools Profiler"
            ],
            "resource": "React.dev Official Documentation & Scrimba Interactive React Course"
        },
        "Next.js": {
            "why_it_matters": "Modern React framework providing Server-Side Rendering (SSR), Static Site Generation (SSG), incremental regeneration, and API routing.",
            "learning_direction": "Master the Next.js App Router, Server Components vs Client Components, server actions, route handlers, and edge caching.",
            "milestones": [
                "Build a full-stack Next.js 14+ application leveraging the App Router and Server Actions",
                "Implement dynamic metadata and OpenGraph tags for search engine optimization",
                "Configure edge caching and Incremental Static Regeneration (ISR) for high performance"
            ],
            "resource": "Next.js Official Learn Platform (nextjs.org/learn)"
        },
        "PostgreSQL": {
            "why_it_matters": "Enterprise-grade relational database required for ACID transactions, complex relational modeling, and high-reliability data persistence.",
            "learning_direction": "Master relational schema normalization, B-Tree and GIN/GiST indexing, EXPLAIN ANALYZE query planning, JSONB storage, and connection pooling.",
            "milestones": [
                "Design normalized 3NF relational schemas with strict foreign key constraints and indexes",
                "Analyze slow database queries using EXPLAIN ANALYZE and optimize execution cost",
                "Implement transactional rollbacks and connection pooling with PgBouncer"
            ],
            "resource": "PostgreSQL Tutorial (postgresqltutorial.com) & 'Designing Data-Intensive Applications' by Martin Kleppmann"
        },
        "MySQL": {
            "why_it_matters": "Widely deployed relational database powering web applications, transactional services, and content management systems.",
            "learning_direction": "Study InnoDB storage engine mechanics, index optimization, query profiling, replication topologies, and transaction isolation levels.",
            "milestones": [
                "Create optimized compound indexes based on query WHERE and ORDER BY clauses",
                "Configure automated backup dumps and point-in-time recovery testing",
                "Measure query throughput under concurrency using MySQL Workbench or sys schema"
            ],
            "resource": "MySQL 8.0 Reference Manual & High Performance MySQL by Silvia Botros"
        },
        "MongoDB": {
            "why_it_matters": "Popular NoSQL document store ideal for flexible semi-structured JSON documents, rapid schema evolution, and horizontal scaling.",
            "learning_direction": "Learn MongoDB aggregation pipelines, compound multikey indexes, document schema validation rules, and sharding strategies.",
            "milestones": [
                "Construct multi-stage aggregation pipelines with $match, $group, $lookup, and $project",
                "Benchmark query performance with .explain('executionStats') to verify index usage",
                "Implement schema validation rules with JSON Schema in Mongoose or PyMongo"
            ],
            "resource": "MongoDB University (learn.mongodb.com) M121 & M201 Courses"
        },
        "Redis": {
            "why_it_matters": "Ultra-low latency in-memory data store essential for caching, session stores, rate limiters, pub/sub messaging, and distributed locks.",
            "learning_direction": "Implement cache-aside strategies, TTL expiration policies, atomic Redis data structures (Hashes, Sorted Sets), and pub/sub pipelines.",
            "milestones": [
                "Implement a distributed rate limiter and session storage module using Redis hashes",
                "Design cache invalidation routines and handle cache stampede mitigation",
                "Integrate Redis as a reliable task queue broker with Celery or BullMQ"
            ],
            "resource": "Redis University - RU101: Introduction to Redis Data Structures"
        },
        "Docker": {
            "why_it_matters": "Containerization standard for packaging applications with dependencies, eliminating 'works on my machine' parity issues in CI/CD.",
            "learning_direction": "Master multi-stage Dockerfiles, image layer caching, security scanning, volume mounts, and multi-container Docker Compose networks.",
            "milestones": [
                "Write optimized multi-stage Dockerfiles minimizing production image size below 100MB",
                "Configure a multi-service local development stack using Docker Compose (App + DB + Redis)",
                "Run vulnerability scans using Docker Scout or Trivy to eliminate CVE risks"
            ],
            "resource": "Docker Official Docs & 'Docker Deep Dive' by Nigel Poulton"
        },
        "Kubernetes": {
            "why_it_matters": "Industry standard for container orchestration, automating deployment, scaling, failover, and service discovery across cloud clusters.",
            "learning_direction": "Learn core resources (Pods, Deployments, Services, ConfigMaps, Secrets, Ingress), Helm chart packaging, and rolling update strategies.",
            "milestones": [
                "Deploy a multi-tier microservice application to a local Minikube or Kind cluster",
                "Package deployment manifests into a customizable, versioned Helm chart",
                "Configure horizontal pod autoscaling (HPA) and zero-downtime rolling updates"
            ],
            "resource": "Kubernetes.io Interactive Tutorials & 'Kubernetes in Action' by Marko Lukša"
        },
        "Amazon Web Services (AWS)": {
            "why_it_matters": "Leading cloud infrastructure provider powering global computation, storage, networking, serverless execution, and managed databases.",
            "learning_direction": "Focus on core infrastructure services (EC2, S3, RDS, IAM, Lambda, VPC, CloudWatch) and Infrastructure as Code with Terraform.",
            "milestones": [
                "Architect a secure VPC with public/private subnets, NAT gateways, and least-privilege IAM roles",
                "Deploy a containerized application to AWS ECS (Fargate) behind an Application Load Balancer",
                "Provision cloud infrastructure reproducibly using Terraform or AWS CDK"
            ],
            "resource": "AWS Skill Builder & AWS Certified Solutions Architect Associate Study Guide"
        },
        "Google Cloud Platform (GCP)": {
            "why_it_matters": "Major cloud platform recognized for managed Kubernetes (GKE), BigQuery analytics, and serverless Cloud Run deployments.",
            "learning_direction": "Master Cloud Run container deployment, Google Kubernetes Engine (GKE), IAM policies, and BigQuery data processing.",
            "milestones": [
                "Deploy a containerized REST service to Cloud Run with automatic scaling",
                "Configure GKE cluster autoscaling and integrate Cloud Monitoring metrics",
                "Set up IAM service accounts with fine-grained role-based permissions"
            ],
            "resource": "Google Cloud Skills Boost & Cloud Architecture Center"
        },
        "Microsoft Azure": {
            "why_it_matters": "Dominant enterprise cloud ecosystem providing Azure App Services, Azure Kubernetes Service (AKS), and Azure DevOps integrations.",
            "learning_direction": "Study Azure Resource Manager (ARM), App Service deployment, Azure SQL, and Azure Active Directory (Entra ID) authentication.",
            "milestones": [
                "Deploy a web app to Azure App Service with continuous deployment slots",
                "Configure managed identity authentication for Azure SQL connections",
                "Set up Azure Monitor alerts and Application Insights application telemetry"
            ],
            "resource": "Microsoft Learn - Azure Fundamentals & Azure Developer Pathways"
        },
        "GraphQL": {
            "why_it_matters": "Declarative API query language allowing clients to request exactly what they need, preventing over-fetching and under-fetching.",
            "learning_direction": "Learn GraphQL Schema Definition Language (SDL), resolvers, DataLoader batching to eliminate N+1 queries, and client caching.",
            "milestones": [
                "Design a GraphQL schema with queries, mutations, custom scalar types, and inputs",
                "Implement batching with DataLoader to eliminate N+1 database roundtrips",
                "Integrate Apollo Client in a frontend application with normalized cache policies"
            ],
            "resource": "GraphQL.org Official Documentation & Apollo Odyssey Interactive Tutorials"
        },
        "REST APIs": {
            "why_it_matters": "Universal architectural pattern for web service communication, resource modeling, and service integration.",
            "learning_direction": "Master RESTful conventions, HTTP status codes, idempotency, pagination, rate limiting, and OpenAPI/Swagger documentation.",
            "milestones": [
                "Architect a RESTful service following strict resource naming and status code standards",
                "Implement cursor-based pagination, field filtering, and rate limiting headers",
                "Generate interactive Swagger/OpenAPI documentation and client SDKs"
            ],
            "resource": "RESTful Web API Design by Arnaud Lauret & OpenAPI 3.1 Specification"
        },
        "CI/CD": {
            "why_it_matters": "Automates verification, testing, security scanning, and deployments, enabling reliable and frequent production releases.",
            "learning_direction": "Master GitHub Actions, GitLab CI, or Jenkins pipelines with automated linting, unit testing, container build steps, and deployment stages.",
            "milestones": [
                "Build a multi-job GitHub Actions workflow triggered on pull requests and branch merges",
                "Implement automated Docker image build and push stages with layer caching",
                "Configure branch protection rules requiring passing CI checks and approvals"
            ],
            "resource": "GitHub Actions Documentation & 'Continuous Delivery' by Jez Humble"
        },
        "Terraform": {
            "why_it_matters": "De facto standard for Infrastructure as Code (IaC), provisioning multi-cloud resources declaratively with version control.",
            "learning_direction": "Master HCL syntax, provider configurations, remote state storage with locking, reusable modules, and terraform plan workflows.",
            "milestones": [
                "Write modular Terraform configurations provisioning cloud compute, storage, and networking",
                "Configure S3 backend state storage with DynamoDB state locking",
                "Integrate automated Terraform plan checks into CI/CD pull request workflows"
            ],
            "resource": "HashiCorp Learn Terraform Tutorials & 'Terraform: Up and Running' by Yevgeniy Brikman"
        },
        "Machine Learning": {
            "why_it_matters": "Powers predictive algorithms, intelligent recommendations, natural language capabilities, and automated classification.",
            "learning_direction": "Master data preprocessing, feature engineering, regression/classification models, evaluation metrics (ROC-AUC, F1), and model inference.",
            "milestones": [
                "Clean and preprocess tabular datasets using Pandas and Scikit-Learn pipelines",
                "Train and tune cross-validated classification models with hyperparameter search",
                "Deploy a trained model as a REST inference endpoint using FastAPI"
            ],
            "resource": "Coursera Machine Learning Specialization by Andrew Ng & Scikit-Learn Docs"
        },
        "Deep Learning": {
            "why_it_matters": "Enables complex neural network architectures for computer vision, natural language processing, and generative AI models.",
            "learning_direction": "Learn backpropagation mechanics, activation functions, loss optimization (Adam), Convolutional / Transformer architectures in PyTorch.",
            "milestones": [
                "Construct and train a multi-layer neural network from scratch using PyTorch nn.Module",
                "Fine-tune a pretrained vision or transformer model using transfer learning",
                "Track training convergence, loss curves, and validation metrics using TensorBoard"
            ],
            "resource": "DeepLearning.AI Specializations & 'Deep Learning with Python' by François Chollet"
        },
        "Agile / Scrum": {
            "why_it_matters": "Standard iterative development framework facilitating cross-functional collaboration, sprint planning, backlog grooming, and rapid feedback.",
            "learning_direction": "Study Scrum ceremonies (Daily Standups, Sprint Planning, Retrospectives), story point estimation, Jira tracking, and continuous improvement.",
            "milestones": [
                "Participate in sprint backlog grooming and breaking user stories into acceptance criteria",
                "Document technical debt and define clear Definition of Done standards",
                "Lead or contribute to sprint retrospective action items to resolve velocity impediments"
            ],
            "resource": "Scrum Guide by Ken Schwaber & Jeff Sutherland (scrumguides.org)"
        },
        "Git": {
            "why_it_matters": "Universal version control system required for collaborative software engineering, branch isolation, and historical code auditability.",
            "learning_direction": "Master interactive rebase, cherry-pick, branch management, merge conflict resolution, commit squashing, and Git hooks.",
            "milestones": [
                "Resolve complex three-way merge conflicts cleanly while maintaining commit history",
                "Organize clean feature branches using interactive rebase and semantic commit messages",
                "Configure pre-commit hooks to automate local linting and secret scanning"
            ],
            "resource": "Pro Git Book (git-scm.com/book) by Scott Chacon and Ben Straub"
        }
    }

    # Curated Knowledge Base: Specific Competency Transferability
    # Maps (TargetSkill, CandidateSkill) -> Detailed Transferability Analysis
    TRANSFERABILITY_DETAILS: Dict[tuple, Dict[str, Any]] = {
        ("PostgreSQL", "SQL"): {
            "transferable_concepts": "Relational data modeling, table constraints, ANSI SQL syntax, JOIN operations, transactions, and indexing principles.",
            "delta_to_bridge": "PostgreSQL-specific types (JSONB, UUID), EXPLAIN ANALYZE execution cost tuning, GIN/GiST indexes, connection pooling (PgBouncer), and MVCC concurrency.",
            "satisfaction_score": 65,
            "interview_advice": "Highlight your deep SQL query design and relational indexing experience; demonstrate how quickly you can adopt PostgreSQL specific features like JSONB and query planning."
        },
        ("PostgreSQL", "MySQL"): {
            "transferable_concepts": "Relational database concepts, SQL queries, B-Tree indexes, foreign keys, stored procedures, and ACID transaction handling.",
            "delta_to_bridge": "PostgreSQL advanced indexing (partial and expression indexes), window functions, CTE optimization, and MVCC engine differences.",
            "satisfaction_score": 80,
            "interview_advice": "Discuss your production experience managing MySQL schemas, and explain how the transition to PostgreSQL brings stronger JSONB support and richer analytics capabilities."
        },
        ("Kubernetes", "Docker"): {
            "transferable_concepts": "Container images, Dockerfiles, layer caching, container networking, environment variables, and process isolation.",
            "delta_to_bridge": "Multi-node orchestration, Pods/Deployments/Services manifests, Ingress controllers, Helm charts, ConfigMaps, Secrets, and cluster auto-scaling.",
            "satisfaction_score": 65,
            "interview_advice": "Emphasize your containerization mastery with Docker and describe how your container architecture forms the foundation for Kubernetes orchestration."
        },
        ("GraphQL", "REST APIs"): {
            "transferable_concepts": "Web service design, HTTP protocol standards, JSON serialization, status codes, backend routing, and authentication patterns.",
            "delta_to_bridge": "Schema Definition Language (SDL), query and mutation resolvers, type hierarchies, and solving N+1 queries using DataLoader batching.",
            "satisfaction_score": 65,
            "interview_advice": "Demonstrate your strong understanding of API design and explain how GraphQL solves client-side over-fetching compared to traditional REST endpoints."
        },
        ("TypeScript", "JavaScript"): {
            "transferable_concepts": "Modern ECMAScript syntax, DOM APIs, async/await, closures, npm ecosystem, and frontend/backend runtimes.",
            "delta_to_bridge": "Static type system, interfaces, generics, type guards, union/intersection types, and strict tsconfig compiler settings.",
            "satisfaction_score": 75,
            "interview_advice": "Present your extensive JavaScript experience and explain how TypeScript provides the compile-time safety and self-documenting code you value in production."
        },
        ("Next.js", "React"): {
            "transferable_concepts": "React component hierarchy, JSX syntax, hooks (useState, useEffect, useMemo), props, and component state management.",
            "delta_to_bridge": "Server-Side Rendering (SSR), Static Site Generation (SSG), App Router directory structure, Server vs Client Components, and API route handlers.",
            "satisfaction_score": 80,
            "interview_advice": "Highlight your React component design principles and discuss how Next.js accelerates performance through server rendering and route-based code splitting."
        },
        ("FastAPI", "Python"): {
            "transferable_concepts": "Python 3 modern syntax, type hinting, dictionary handling, modular packaging, and unit testing.",
            "delta_to_bridge": "Pydantic validation schemas, async/await request handling, dependency injection system, and automatic OpenAPI schema generation.",
            "satisfaction_score": 85,
            "interview_advice": "Showcase your Python programming foundation and explain how FastAPI's type hinting aligns with clean software architecture."
        },
        ("FastAPI", "Flask"): {
            "transferable_concepts": "Web routing, HTTP request/response lifecycles, blueprint/router modularity, WSGI/ASGI fundamentals, and microservice architecture.",
            "delta_to_bridge": "Asynchronous event loop execution, Pydantic request models, and built-in interactive Swagger UI documentation.",
            "satisfaction_score": 85,
            "interview_advice": "Describe your track record building Flask microservices and emphasize how easily you transitioned to FastAPI for high-concurrency async workloads."
        },
        ("Django", "Python"): {
            "transferable_concepts": "Object-oriented Python, modular architecture, unit testing, and relational database integrations.",
            "delta_to_bridge": "Django ORM, built-in admin panel, middleware pipeline, Django REST Framework (DRF) serializers, and authentication models.",
            "satisfaction_score": 75,
            "interview_advice": "Emphasize your core Python strength and explain how Django's 'batteries-included' philosophy speeds up backend delivery."
        },
        ("Amazon Web Services (AWS)", "Docker"): {
            "transferable_concepts": "Containerized application packaging, service isolation, environment configuration, and microservice deployment.",
            "delta_to_bridge": "AWS ECS/EKS container hosting, Application Load Balancers, IAM security policies, and CloudWatch log groups.",
            "satisfaction_score": 60,
            "interview_advice": "Discuss your containerization workflow and explain how you deploy container images to managed cloud environments."
        }
    }

    @classmethod
    def _get_skill_category(cls, skill_name: str) -> str:
        """Helper to retrieve category for a skill."""
        return ResumeJobMatcher.SKILL_CATEGORIES.get(skill_name, "Technical Competency")

    @classmethod
    def _generate_default_why_it_matters(cls, skill_name: str, category: str, relevance: str = "Required") -> str:
        """Synthesize a clear, job-relevant explanation for why an uncataloged skill matters."""
        if relevance == "Required":
            return (
                f"Essential {category.lower()} requirement listed for this role. Demonstrating capability in "
                f"'{skill_name}' is critical to pass preliminary recruiter screenings and technical interviews."
            )
        return (
            f"Valuable preferred qualification in {category.lower()}. While not strictly mandatory, practical experience "
            f"with '{skill_name}' will distinguish your profile from other applicants."
        )

    @classmethod
    def _generate_default_learning_direction(cls, skill_name: str, category: str) -> str:
        """Synthesize practical, hands-on learning directions for an uncataloged skill."""
        return (
            f"Review official documentation and tutorials for '{skill_name}'. Implement a small proof-of-concept project "
            f"showcasing core features, configuration, and unit test coverage to reinforce your hands-on experience."
        )

    @classmethod
    def analyze(
        cls,
        match_result: Optional[Dict[str, Any]],
        job_analysis: Optional[Dict[str, Any]],
        parsed_resume: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main entry point for Stage 5 Skill Gap Analysis.
        Accepts real results from Stage 4 matching, Stage 3 JD analysis, and Stage 2 resume parsing.
        Returns categorized gaps, weak match diagnostics, transferable bridges, and a personalized roadmap.
        """
        if match_result is None or not isinstance(match_result, dict):
            raise SkillGapError("Missing or invalid match_result payload.", code="MISSING_MATCH_RESULT")
        if job_analysis is None or not isinstance(job_analysis, dict):
            raise SkillGapError("Missing or invalid job_analysis payload.", code="MISSING_JD_ANALYSIS")
        if parsed_resume is None or not isinstance(parsed_resume, dict):
            raise SkillGapError("Missing or invalid parsed_resume payload.", code="MISSING_PARSED_RESUME")

        # Extract verified candidate skills from match results or parsed resume
        candidate_stats = match_result.get("candidate_stats", {})
        candidate_skills: Set[str] = set(candidate_stats.get("candidate_skills", []))
        if not candidate_skills:
            candidate_skills = ResumeJobMatcher.extract_candidate_skills(parsed_resume)

        # Candidate text sections for depth/evidence verification
        section_contents = parsed_resume.get("section_contents", {})
        exp_text = (section_contents.get("Experience", "") + " " + section_contents.get("Projects", "")).lower()
        skills_section_text = section_contents.get("Skills", "").lower()
        full_text = parsed_resume.get("full_text", "").lower()

        # Job requirements
        req_jd_skills = [ResumeJobMatcher.canonicalize_skill(s) for s in job_analysis.get("required_skills", []) if s]
        pref_jd_skills = [ResumeJobMatcher.canonicalize_skill(s) for s in job_analysis.get("preferred_skills", []) if s]

        # -------------------------------------------------------------
        # 1. Missing Required Skills (High Priority)
        # -------------------------------------------------------------
        missing_required_skills: List[Dict[str, Any]] = []
        raw_missing_req = match_result.get("missing_required_skills", [])
        
        for item in raw_missing_req:
            skill_name = item.get("name", "")
            if not skill_name:
                continue

            category = item.get("category") or cls._get_skill_category(skill_name)
            profile = cls.CURATED_SKILL_PROFILES.get(skill_name, {})

            why_it_matters = profile.get("why_it_matters") or item.get("impact") or cls._generate_default_why_it_matters(skill_name, category, "Required")
            learning_dir = profile.get("learning_direction") or cls._generate_default_learning_direction(skill_name, category)

            missing_required_skills.append({
                "name": skill_name,
                "relevance": "Required",
                "priority": "High",
                "category": category,
                "why_it_matters": why_it_matters,
                "suggested_learning_direction": learning_dir,
                "impact": f"Critical - Hard requirement '{skill_name}' missing from candidate resume."
            })

        # -------------------------------------------------------------
        # 2. Missing Preferred Skills (Medium / Low Priority)
        # -------------------------------------------------------------
        missing_preferred_skills: List[Dict[str, Any]] = []
        raw_missing_pref = match_result.get("missing_preferred_skills", [])

        for item in raw_missing_pref:
            skill_name = item.get("name", "")
            if not skill_name:
                continue

            category = item.get("category") or cls._get_skill_category(skill_name)
            profile = cls.CURATED_SKILL_PROFILES.get(skill_name, {})

            # Priority is Medium for core technical categories, Low for secondary tools
            priority = "Medium" if category in ("Languages", "Frameworks", "Databases", "DevOps & Cloud", "AI & Data Science") else "Low"

            why_it_matters = profile.get("why_it_matters") or item.get("impact") or cls._generate_default_why_it_matters(skill_name, category, "Preferred")
            learning_dir = profile.get("learning_direction") or cls._generate_default_learning_direction(skill_name, category)

            missing_preferred_skills.append({
                "name": skill_name,
                "relevance": "Preferred",
                "priority": priority,
                "category": category,
                "why_it_matters": why_it_matters,
                "suggested_learning_direction": learning_dir,
                "impact": f"Optional - Preferred qualification '{skill_name}' not identified in resume."
            })

        # -------------------------------------------------------------
        # 3. Weak / Low-Confidence Matches
        # -------------------------------------------------------------
        weak_matches: List[Dict[str, Any]] = []
        matched_skills = match_result.get("matched_skills", [])

        for match in matched_skills:
            skill_name = match.get("name", "")
            match_type = match.get("match_type", "exact")
            relevance = match.get("relevance", "Required")
            category = match.get("category") or cls._get_skill_category(skill_name)
            credit = match.get("credit", 1.0)
            matched_via = match.get("matched_via", "")

            # Case A: Related Match (e.g. matched via related skill with 0.65 credit)
            if match_type == "related":
                weak_matches.append({
                    "name": skill_name,
                    "relevance": relevance,
                    "match_type": "related_skill",
                    "matched_via": matched_via,
                    "credit": credit,
                    "confidence": "Medium" if relevance == "Required" else "Low",
                    "confidence_score": int(credit * 100),
                    "why_weak": f"Matched indirectly via related skill. Direct hands-on evidence of '{skill_name}' was not found in the resume.",
                    "suggested_improvement": f"Demonstrate direct hands-on application of '{skill_name}' in a project bullet point, or highlight how your transferable experience satisfies this requirement."
                })
                continue

            # Case B: Shallow Mention (Exact match, but only in skills keyword list, no bullets in Experience/Projects)
            if match_type == "exact":
                escaped_name = re.escape(skill_name.lower())
                in_experience = bool(re.search(rf"\b{escaped_name}\b", exp_text))
                in_skills_list = bool(re.search(rf"\b{escaped_name}\b", skills_section_text))

                if in_skills_list and not in_experience:
                    weak_matches.append({
                        "name": skill_name,
                        "relevance": relevance,
                        "match_type": "shallow_mention",
                        "matched_via": "Listed in Skills summary only",
                        "credit": 0.85,
                        "confidence": "Medium",
                        "confidence_score": 60,
                        "why_weak": f"'{skill_name}' is listed in the technical skills overview but lacks corroborating evidence or impact metrics in Work Experience or Projects.",
                        "suggested_improvement": f"Add at least one bullet point in Experience or Projects demonstrating how you utilized '{skill_name}' to deliver measurable business or architectural results."
                    })

        # -------------------------------------------------------------
        # 4. Related Skills Partially Satisfying Requirements
        # -------------------------------------------------------------
        partially_satisfied_requirements: List[Dict[str, Any]] = []

        # Check all required and preferred JD skills that lack an exact match in candidate_skills
        all_target_skills = [(s, "Required") for s in req_jd_skills if s not in candidate_skills] + \
                             [(s, "Preferred") for s in pref_jd_skills if s not in candidate_skills]

        for target_skill, relevance in all_target_skills:
            # Check if candidate possesses any related skill from RELATED_SKILL_MAP
            related_family = ResumeJobMatcher.RELATED_SKILL_MAP.get(target_skill, set())
            candidate_overlaps = [cand_s for cand_s in candidate_skills if cand_s in related_family]

            if not candidate_overlaps:
                continue

            # We strictly use the real related skill the candidate verified has
            cand_skill = candidate_overlaps[0]
            transfer_key = (target_skill, cand_skill)
            curated_transfer = cls.TRANSFERABILITY_DETAILS.get(transfer_key, {})

            transferable_concepts = curated_transfer.get(
                "transferable_concepts",
                f"Core software engineering foundations, architecture patterns, and lifecycle within {cls._get_skill_category(target_skill)}."
            )
            delta_to_bridge = curated_transfer.get(
                "delta_to_bridge",
                f"Platform-specific syntax, specialized APIs, deployment configurations, and advanced features of '{target_skill}'."
            )
            satisfaction_score = curated_transfer.get("satisfaction_score", 65)
            interview_advice = curated_transfer.get(
                "interview_advice",
                f"Emphasize your proven competency in '{cand_skill}' and articulate how your foundational knowledge directly accelerates ramp-up on '{target_skill}'."
            )

            partially_satisfied_requirements.append({
                "target_skill": target_skill,
                "candidate_skill": cand_skill,
                "relevance": relevance,
                "satisfaction_level": f"Partial Match ({satisfaction_score}% transferable)",
                "satisfaction_score": satisfaction_score,
                "transferable_concepts": transferable_concepts,
                "delta_to_bridge": delta_to_bridge,
                "interview_strategy": interview_advice
            })

        # -------------------------------------------------------------
        # 5. Personalized Skill Gap Closure Roadmap
        # -------------------------------------------------------------
        roadmap = cls._generate_learning_roadmap(
            missing_required=missing_required_skills,
            weak_matches=weak_matches,
            missing_preferred=missing_preferred_skills
        )

        # -------------------------------------------------------------
        # 6. Overall Assessment & Metrics
        # -------------------------------------------------------------
        total_gaps = len(missing_required_skills) + len(missing_preferred_skills)
        critical_count = len(missing_required_skills)
        preferred_count = len(missing_preferred_skills)
        weak_count = len(weak_matches)
        bridgeable_count = len(partially_satisfied_requirements)

        if critical_count == 0 and weak_count == 0:
            readiness_verdict = "Interview Ready: Zero critical required skill gaps detected."
        elif critical_count == 0:
            readiness_verdict = "Strong Match: All hard requirements met with minor weak/related competencies to fortify."
        elif critical_count <= 2:
            readiness_verdict = f"Moderate Gap: {critical_count} critical skill gaps identified. Recommended 2–3 weeks focused study."
        else:
            readiness_verdict = f"Substantial Gap: {critical_count} hard requirements missing. Structured skill acquisition recommended before applying."

        return {
            "success": True,
            "readiness_verdict": readiness_verdict,
            "total_gaps_count": total_gaps,
            "critical_gaps_count": critical_count,
            "preferred_gaps_count": preferred_count,
            "weak_matches_count": weak_count,
            "bridgeable_skills_count": bridgeable_count,
            "missing_required_skills": missing_required_skills,
            "missing_preferred_skills": missing_preferred_skills,
            "weak_matches": weak_matches,
            "partially_satisfied_requirements": partially_satisfied_requirements,
            "learning_roadmap": roadmap
        }

    @classmethod
    def _generate_learning_roadmap(
        cls,
        missing_required: List[Dict[str, Any]],
        weak_matches: List[Dict[str, Any]],
        missing_preferred: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Constructs a sequential, 3-phase study roadmap using real identified skill gaps."""
        phases: List[Dict[str, Any]] = []

        # Phase 1: Critical Required Gaps
        if missing_required:
            target_skill = missing_required[0]["name"]
            profile = cls.CURATED_SKILL_PROFILES.get(target_skill, {})
            milestones = profile.get("milestones", [
                f"Study fundamental architecture and core syntax of {target_skill}",
                f"Build a functioning CRUD module or proof-of-concept incorporating {target_skill}",
                f"Integrate unit test suites verifying edge cases and error handling"
            ])
            resource = profile.get("resource", f"Official {target_skill} Documentation and Developer Guides")

            phases.append({
                "phase": 1,
                "phase_title": f"Phase 1: Close Critical Core Gap ({target_skill})",
                "target_skill": target_skill,
                "duration_weeks": "Weeks 1–2",
                "estimated_hours": 14,
                "milestones": milestones,
                "recommended_resource": resource
            })
        elif weak_matches:
            target_skill = weak_matches[0]["name"]
            phases.append({
                "phase": 1,
                "phase_title": f"Phase 1: Fortify Related Competency ({target_skill})",
                "target_skill": target_skill,
                "duration_weeks": "Weeks 1–2",
                "estimated_hours": 10,
                "milestones": [
                    f"Bridge theoretical knowledge from related tools to direct {target_skill} implementation",
                    f"Implement an end-to-end service or feature utilizing {target_skill}",
                    f"Document measurable outcomes and add targeted bullet points to your resume"
                ],
                "recommended_resource": f"Official {target_skill} Documentation & Hands-On Workshops"
            })
        else:
            phases.append({
                "phase": 1,
                "phase_title": "Phase 1: Production System Optimization & Hardening",
                "target_skill": "Architecture & Clean Code",
                "duration_weeks": "Weeks 1–2",
                "estimated_hours": 8,
                "milestones": [
                    "Audit existing repositories for test coverage, CI linting, and error boundaries",
                    "Conduct benchmarking on high-traffic database queries and endpoint latencies",
                    "Standardize documentation and architectural decision records (ADRs)"
                ],
                "recommended_resource": "Clean Architecture by Robert C. Martin"
            })

        # Phase 2: Secondary Required Gaps or Weak Matches
        if len(missing_required) > 1:
            target_skill = missing_required[1]["name"]
            profile = cls.CURATED_SKILL_PROFILES.get(target_skill, {})
            milestones = profile.get("milestones", [
                f"Master intermediate features and configurations of {target_skill}",
                f"Implement resilient patterns and error monitoring in {target_skill}",
                f"Review common interview architectural questions regarding {target_skill}"
            ])
            resource = profile.get("resource", f"Interactive {target_skill} Tutorials & Best Practices")

            phases.append({
                "phase": 2,
                "phase_title": f"Phase 2: Remediate Secondary Core Requirement ({target_skill})",
                "target_skill": target_skill,
                "duration_weeks": "Weeks 3–4",
                "estimated_hours": 12,
                "milestones": milestones,
                "recommended_resource": resource
            })
        elif weak_matches and len(phases) < 2:
            target_skill = weak_matches[0]["name"]
            phases.append({
                "phase": 2,
                "phase_title": f"Phase 2: Solidify Evidenced Experience ({target_skill})",
                "target_skill": target_skill,
                "duration_weeks": "Weeks 3–4",
                "estimated_hours": 8,
                "milestones": [
                    f"Construct a live project demo illustrating production use of {target_skill}",
                    f"Deepen familiarity with configuration flags, security best practices, and edge cases",
                    f"Add quantified bullet points highlighting latency reductions or throughput metrics"
                ],
                "recommended_resource": f"Official Documentation & Tutorials for {target_skill}"
            })
        elif missing_preferred:
            target_skill = missing_preferred[0]["name"]
            profile = cls.CURATED_SKILL_PROFILES.get(target_skill, {})
            phases.append({
                "phase": 2,
                "phase_title": f"Phase 2: Master Preferred Qualification ({target_skill})",
                "target_skill": target_skill,
                "duration_weeks": "Weeks 3–4",
                "estimated_hours": 10,
                "milestones": profile.get("milestones", [
                    f"Explore core concepts and benefits of {target_skill}",
                    f"Build a proof-of-concept module integrating {target_skill}",
                    f"Prepare talking points detailing why {target_skill} was chosen"
                ]),
                "recommended_resource": profile.get("resource", f"Official {target_skill} Guides")
            })
        else:
            phases.append({
                "phase": 2,
                "phase_title": "Phase 2: Cloud Infrastructure & Deployment Automation",
                "target_skill": "CI/CD & Cloud Orchestration",
                "duration_weeks": "Weeks 3–4",
                "estimated_hours": 10,
                "milestones": [
                    "Configure automated deployment pipelines with GitHub Actions or GitLab CI",
                    "Implement multi-stage Docker container builds with vulnerability scanning",
                    "Deploy a resilient service to managed cloud infrastructure"
                ],
                "recommended_resource": "DevOps Roadmap & Official Cloud Provider Documentation"
            })

        # Phase 3: Bonus Qualifications & Polish
        if missing_preferred and len(phases) < 3:
            # Pick a preferred skill not already used in Phase 2
            candidate_pref = [p["name"] for p in missing_preferred if p["name"] not in [p["target_skill"] for p in phases]]
            target_skill = candidate_pref[0] if candidate_pref else missing_preferred[0]["name"]
            profile = cls.CURATED_SKILL_PROFILES.get(target_skill, {})

            phases.append({
                "phase": 3,
                "phase_title": f"Phase 3: High-Impact Bonus Competency ({target_skill})",
                "target_skill": target_skill,
                "duration_weeks": "Weeks 5–6",
                "estimated_hours": 10,
                "milestones": profile.get("milestones", [
                    f"Review advanced architecture and community standards for {target_skill}",
                    f"Integrate {target_skill} alongside your core stack in an open-source demo",
                    f"Highlight technical initiative in resume summary and interview stories"
                ]),
                "recommended_resource": profile.get("resource", f"{target_skill} Developer Hub & Official Guides")
            })
        elif len(phases) < 3:
            phases.append({
                "phase": 3,
                "phase_title": "Phase 3: Technical Interview Preparation & System Design",
                "target_skill": "Distributed Systems & Architecture",
                "duration_weeks": "Weeks 5–6",
                "estimated_hours": 10,
                "milestones": [
                    "Practice architectural system design interviews (scalability, caching, databases)",
                    "Prepare STAR method behavioral responses articulating past project ownership",
                    "Conduct mock technical interview sessions and refine live coding communication"
                ],
                "recommended_resource": "'System Design Interview' by Alex Xu & LeetCode System Design"
            })

        return phases
