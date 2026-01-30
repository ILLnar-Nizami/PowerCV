#!/usr/bin/env python3
"""
Test script for AI provider caching functionality.

This script tests the Redis caching implementation in the AIProviderClient.
"""

import asyncio
import logging
import time

from app.services.ai_providers import AIProviderClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ai_caching():
    """Test caching in AIProviderClient."""
    logger.info("Testing AI provider caching...")

    ai_client = AIProviderClient(provider="cerebras")

    # Sample prompts
    system_prompt = "You are a helpful assistant."
    user_message = "What is the capital of France?"

    # First call (should not be cached)
    start_time = time.time()
    try:
        result1 = await ai_client.chat_completion(system_prompt, user_message)
        first_call_time = time.time() - start_time
        logger.info(f"First call time: {first_call_time:.2f} seconds")
        logger.info(f"First call result: {result1[:50]}...")
    except Exception as e:
        logger.error(f"First call failed: {e}")
        return

    # Second call (should be cached)
    start_time = time.time()
    try:
        result2 = await ai_client.chat_completion(system_prompt, user_message)
        second_call_time = time.time() - start_time
        logger.info(f"Second call time: {second_call_time:.2f} seconds")
        logger.info(f"Second call result: {result2[:50]}...")
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
