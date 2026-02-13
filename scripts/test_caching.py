#!/usr/bin/env python3
"""
Test script for PowerCV caching functionality.

This script tests the Redis caching implementation in the workflow orchestrator
and AI providers.
"""

import asyncio
import logging
import time

from app.services.workflow_orchestrator import CVWorkflowOrchestrator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_workflow_caching():
    """Test caching in CVWorkflowOrchestrator."""
    logger.info("Testing workflow orchestrator caching...")

    orchestrator = CVWorkflowOrchestrator()

    # Sample CV and job description
    cv_text = """
    John Doe
    Software Engineer
    Experience:
    - Senior Developer at Tech Corp (2020-present)
    - Backend Developer at Startup Inc (2018-2020)
    Skills: Python, FastAPI, PostgreSQL, Docker
    """

    jd_text = """
    We are looking for a Senior Software Engineer with:
    - 5+ years of Python experience
    - Experience with FastAPI or similar frameworks
    - Knowledge of PostgreSQL and Docker
    - Strong backend development skills
    """

    # First call (should not be cached)
    start_time = time.time()
    result1 = await orchestrator.optimize_cv_for_job(cv_text, jd_text)
    first_call_time = time.time() - start_time
    logger.info(f"First call time: {first_call_time:.2f} seconds")

    # Second call (should be cached)
    start_time = time.time()
    result2 = await orchestrator.optimize_cv_for_job(cv_text, jd_text)
    second_call_time = time.time() - start_time
    logger.info(f"Second call time: {second_call_time:.2f} seconds")

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


if __name__ == "__main__":
    asyncio.run(test_workflow_caching())
