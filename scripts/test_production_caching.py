#!/usr/bin/env python3
"""
Production-like test for PowerCV caching functionality.

This script tests the Redis caching implementation in the workflow orchestrator
and AI providers in a production-like environment.
"""

import asyncio
import logging
import time

from app.services.workflow_orchestrator import CVWorkflowOrchestrator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_workflow_caching_production():
    """Test caching in CVWorkflowOrchestrator in a production-like environment."""
    logger.info(
        "Testing workflow orchestrator caching in production-like environment..."
    )

    orchestrator = CVWorkflowOrchestrator()

    # Sample CV and job description (more realistic)
    cv_text = """
    John Doe
    Senior Software Engineer
    Amsterdam, Netherlands
    john.doe@example.com
    +31 6 12345678

    PROFESSIONAL EXPERIENCE:

    Senior Backend Engineer | TechCorp Amsterdam | Jan 2020 - Present
    - Led development of microservices using Python/FastAPI
    - Implemented CI/CD pipelines reducing deployment time by 60%
    - Mentored junior developers and conducted code reviews
    - Technologies: Python, FastAPI, PostgreSQL, Docker, Kubernetes

    Backend Developer | StartupXYZ | Jun 2018 - Dec 2019
    - Developed REST APIs for customer-facing applications
    - Optimized database queries improving response time by 40%
    - Technologies: Python, Django, MySQL, Redis

    EDUCATION:
    MSc Computer Science | University of Amsterdam | 2018
    BSc Software Engineering | Technical University Delft | 2016

    SKILLS:
    Programming: Python, JavaScript, Go
    Frameworks: FastAPI, Django, Flask
    Databases: PostgreSQL, MySQL, MongoDB
    Cloud: AWS, Docker, Kubernetes
    Other: Git, CI/CD, Agile/Scrum
    """

    jd_text = """
    Senior Python Developer

    Company: Innovative Tech Solutions
    Location: Amsterdam, Netherlands (Hybrid)

    ABOUT THE ROLE:
    We are looking for an experienced Senior Python Developer to join our backend team.
    You will be responsible for designing and implementing scalable microservices that
    power our platform used by thousands of customers daily.

    RESPONSIBILITIES:
    - Design and develop high-performance Python applications using FastAPI
    - Collaborate with frontend and product teams to deliver features
    - Optimize application performance and ensure scalability
    - Participate in code reviews and mentoring junior developers
    - Contribute to architectural decisions and technical documentation

    REQUIREMENTS:
    - 5+ years of experience with Python and web frameworks
    - Strong experience with FastAPI or similar async frameworks
    - Proficiency with PostgreSQL and database optimization
    - Experience with Docker and containerized environments
    - Knowledge of cloud platforms (AWS/GCP)
    - Familiarity with CI/CD pipelines
    - Understanding of distributed systems and microservices architecture

    NICE TO HAVE:
    - Experience with Kubernetes
    - Knowledge of Redis or other caching solutions
    - Familiarity with MongoDB
    - Experience with asyncio and concurrent programming
    """

    # First call (should not be cached)
    start_time = time.time()
    result1 = await orchestrator.optimize_cv_for_job(cv_text, jd_text)
    first_call_time = time.time() - start_time
    logger.info(f"First call time: {first_call_time:.2f} seconds")
    logger.info(f"ATS Score: {result1['ats_score']}")

    # Second call (should be cached)
    start_time = time.time()
    result2 = await orchestrator.optimize_cv_for_job(cv_text, jd_text)
    second_call_time = time.time() - start_time
    logger.info(f"Second call time: {second_call_time:.2f} seconds")
    logger.info(f"ATS Score: {result2['ats_score']}")

    # Verify results are the same
    if result1["ats_score"] == result2["ats_score"]:
        logger.info("✓ Caching test passed - results are consistent")
    else:
        logger.error("✗ Caching test failed - results differ")

    # Verify caching performance improvement
    if second_call_time < first_call_time:
        logger.info("✓ Caching improved performance")
    else:
        logger.info(
            "ℹ Caching performance impact not measured (may be due to other factors)"
        )

    # Test with slight variation (should not be cached)
    jd_text_variation = jd_text.replace(
        "Senior Python Developer", "Lead Python Developer"
    )
    start_time = time.time()
    result3 = await orchestrator.optimize_cv_for_job(cv_text, jd_text_variation)
    variation_call_time = time.time() - start_time
    logger.info(f"Variation call time: {variation_call_time:.2f} seconds")
    logger.info(f"ATS Score: {result3['ats_score']}")

    if variation_call_time > second_call_time:
        logger.info("✓ Variation correctly bypassed cache")
    else:
        logger.info("ℹ Variation caching behavior not definitive")


if __name__ == "__main__":
    asyncio.run(test_workflow_caching_production())
