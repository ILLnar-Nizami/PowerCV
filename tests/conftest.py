"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_redis():
    """Provide a mocked Redis client for all tests."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def mock_settings():
    """Provide mocked settings for all tests."""
    settings = MagicMock()
    settings.cerebras_api_key = "test-cerebras-api-key-for-ci"
    settings.cerebras_api_base = "https://api.cerebras.ai/v1"
    settings.cerebras_model = "gpt-oss-120b"
    settings.openai_api_key = "test-openai-api-key-for-ci"
    settings.openai_api_base = "https://api.openai.com/v1"
    settings.openai_model = "gpt-4-turbo"
    settings.deepseek_api_key = "test-deepseek-api-key-for-ci"
    settings.deepseek_api_base = "https://api.deepseek.com/v1"
    settings.deepseek_model = "deepseek-chat"
    return settings


@pytest.fixture(autouse=True)
async def cleanup_redis():
    """Ensure Redis connections are cleaned up after each test."""
    yield
    # Cleanup code here if needed
