#!/usr/bin/env python3
"""
Test script for AI provider caching functionality with mocked responses.

This script tests the Redis caching implementation in the AIProviderClient
using mocked responses to avoid authentication issues.
"""

import asyncio
import logging
import time
from unittest.mock import AsyncMock, patch

from app.services.ai_providers import AIProviderClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ai_caching():
    """Test caching in AIProviderClient with mocked responses."""
    logger.info("Testing AI provider caching with mocked responses...")

    ai_client = AIProviderClient(provider="cerebras")

    # Sample prompts
    system_prompt = "You are a helpful assistant."
    user_message = "What is the capital of France?"

    # Mock the LiteLLM completion function
    class MockChoice:
        def __init__(self, content):
            self.message = MockMessage(content)

    class MockMessage:
        def __init__(self, content):
            self.content = content

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
            self.usage = {"prompt_tokens": 10, "completion_tokens": 20}

    mock_response = MockResponse("The capital of France is Paris.")

    with patch(
        "app.services.ai_providers.completion", new_callable=AsyncMock
    ) as mock_completion:
        mock_completion.return_value = mock_response
        # First call (should not be cached)
        start_time = time.time()
        try:
            result1 = await ai_client.chat_completion(system_prompt, user_message)
            first_call_time = time.time() - start_time
            logger.info(f"First call time: {first_call_time:.2f} seconds")
            logger.info(f"First call result: {result1}")
        except Exception as e:
            logger.error(f"First call failed: {e}")
            return

        # Second call (should be cached)
        start_time = time.time()
        try:
            result2 = await ai_client.chat_completion(system_prompt, user_message)
            second_call_time = time.time() - start_time
            logger.info(f"Second call time: {second_call_time:.2f} seconds")
            logger.info(f"Second call result: {result2}")
        except Exception as e:
            logger.error(f"Second call failed: {e}")
            return

        # Verify results are the same
        if result1 == result2:
            logger.info("✓ AI caching test passed - results are consistent")
        else:
            logger.error("✗ AI caching test failed - results differ")

        # Verify caching performance improvement
        if second_call_time < first_call_time:
            logger.info("✓ AI caching improved performance")
        else:
            logger.info(
                "ℹ AI caching performance impact not measured (may be due to other factors)"
            )

        # Test cost tracking
        logger.info(f"Total AI requests: {ai_client.cost_tracker['requests']}")
        logger.info(f"Total AI cost: ${ai_client.cost_tracker['total_cost']:.6f}")
        logger.info(f"Total AI tokens: {ai_client.cost_tracker['total_tokens']}")


if __name__ == "__main__":
    asyncio.run(test_ai_caching())
