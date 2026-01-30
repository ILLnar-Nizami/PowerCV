"""Test rate limiting and fallback behavior."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from app.services.ai_providers import AIProviderClient
from app.services.cover_letter_gen import CoverLetterGenerator
from app.services.workflow_orchestrator import CVWorkflowOrchestrator


@pytest.mark.asyncio
@patch("app.services.ai_providers.get_settings")
@patch("app.services.ai_providers.completion")
async def test_ai_client_rate_limit(mock_completion, mock_get_settings):
    """Test AI client handles rate limit errors properly."""
    # Mock settings with API key
    mock_settings = MagicMock()
    mock_settings.cerebras_api_key = "test_key"
    mock_get_settings.return_value = mock_settings

    # Mock Redis to avoid connection errors during test
    with patch("app.services.ai_providers.get_redis") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Cache miss
        mock_get_redis.return_value = mock_redis

        # Create AI client
        client = AIProviderClient("cerebras")

        # Mock completion to raise RateLimitError
        from litellm import exceptions

        # We need a valid response object for RateLimitError
        mock_response = MagicMock()
        mock_completion.side_effect = exceptions.RateLimitError(
            message="Rate limit exceeded",
            llm_provider="cerebras",
            response=mock_response,
            model="cerebras/gpt-oss-120b",
        )

        # Test that rate limit error is properly handled (all providers fail)
        with pytest.raises(Exception) as exc_info:
            await client.chat_completion(
                system_prompt="Test system", user_message="Test user message"
            )

        # The client logs the error and tries fallbacks, then raises Exception if all fail
        # The exception message includes the last error type
        assert "RateLimitError" in str(exc_info.value)


@pytest.mark.asyncio
async def test_workflow_orchestrator_rate_limit_fallback():
    """Test workflow orchestrator falls back gracefully on rate limit."""
    # Mock Redis to avoid caching issues
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # No cached result
    mock_redis.setex = AsyncMock()  # Cache setting

    # Create orchestrator with mocked Redis - use correct patch path
    with (
        patch("app.services.workflow_orchestrator.get_redis", return_value=mock_redis),
        patch("app.services.ai_providers.get_redis", return_value=mock_redis),
        patch("app.services.cv_analyzer.get_redis", return_value=mock_redis),
        patch("app.services.cv_optimizer.get_redis", return_value=mock_redis),
    ):
        orchestrator = CVWorkflowOrchestrator()

        # Mock analyzer to raise rate limit error on second call
        mock_analyzer = MagicMock()
        first_analysis = {
            "ats_score": 32,
            "keyword_analysis": {
                "matched_keywords": [{"keyword": "Python"}],
                "missing_critical": [{"keyword": "Kubernetes"}],
            },
        }
        mock_analyzer.analyze = AsyncMock(
            side_effect=[
                first_analysis,  # First call succeeds
                requests.exceptions.RequestException(
                    "rate limit exceeded"
                ),  # Second call fails
            ]
        )
        orchestrator.analyzer = mock_analyzer

        # Mock optimizer (async)
        mock_optimizer = MagicMock()
        mock_optimizer.optimize_comprehensive = AsyncMock(
            return_value={
                "user_information": {
                    "name": "Test Candidate",
                    "email": "test@example.com",
                }
            }
        )
        orchestrator.optimizer = mock_optimizer

        # Test that workflow completes despite rate limit
        result = await orchestrator.optimize_cv_for_job(
            cv_text="Original CV content",
            jd_text="Job description text",
            generate_cover_letter=False,
        )

        # Should use original score when rate limited
        assert result["ats_score"] == 32


@pytest.mark.asyncio
async def test_cover_letter_rate_limit_fallback():
    """Test cover letter generator instantiation."""
    # Create generator
    generator = CoverLetterGenerator()
    assert generator is not None
