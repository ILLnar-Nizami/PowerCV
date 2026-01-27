#!/usr/bin/env python3
"""
Performance monitoring script for PowerCV.

This script monitors the performance impact of caching and other optimizations.
"""

import asyncio
import logging
import time
from unittest.mock import AsyncMock, patch

from app.services.ai_providers import AIProviderClient
from app.services.workflow_orchestrator import CVWorkflowOrchestrator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def monitor_caching_performance():
    """Monitor the performance impact of caching."""
    logger.info("Starting performance monitoring...")

    # Test data
    cv_text = (
        "John Doe\nSoftware Engineer\nExperience: 5 years Python, FastAPI, PostgreSQL"
    )
    jd_text = "Looking for Senior Python Developer with FastAPI experience"

    system_prompt = "You are a helpful assistant."
    user_message = "What are the key skills for a Python developer?"

    # Mock AI response
    class MockChoice:
        def __init__(self, content):
            self.message = MockMessage(content)

    class MockMessage:
        def __init__(self, content):
            self.content = content

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
            self.usage = {"prompt_tokens": 50, "completion_tokens": 100}

    mock_response = MockResponse("Python, FastAPI, PostgreSQL, Docker, Kubernetes")

    with patch(
        "app.services.ai_providers.completion", new_callable=AsyncMock
    ) as mock_completion:
        mock_completion.return_value = mock_response

        # Test AI provider performance
        ai_client = AIProviderClient(provider="cerebras")

        # Warm up cache
        await ai_client.chat_completion(system_prompt, user_message)

        # Measure cached performance
        times = []
        for _ in range(10):
            start = time.time()
            await ai_client.chat_completion(system_prompt, user_message)
            times.append(time.time() - start)

        avg_cached_time = sum(times) / len(times)
        logger.info(f"Average cached AI call time: {avg_cached_time:.4f} seconds")

    # Test workflow orchestrator performance
    orchestrator = CVWorkflowOrchestrator()

    # Warm up cache
    await orchestrator.optimize_cv_for_job(cv_text, jd_text)

    # Measure cached performance
    times = []
    for _ in range(5):
        start = time.time()
        await orchestrator.optimize_cv_for_job(cv_text, jd_text)
        times.append(time.time() - start)

    avg_cached_time = sum(times) / len(times)
    logger.info(f"Average cached workflow time: {avg_cached_time:.4f} seconds")

    logger.info("Performance monitoring completed.")


if __name__ == "__main__":
    asyncio.run(monitor_caching_performance())
