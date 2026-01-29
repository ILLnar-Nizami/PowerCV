"""Tests for AIProviderClient using LiteLLM."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_providers import AIProviderClient


@pytest.mark.asyncio
@patch("app.services.ai_providers.get_settings")
async def test_chat_completion_success(mock_get_settings):
    """Test successful chat completion with primary provider."""
    # Mock settings with API key
    mock_settings = MagicMock()
    mock_settings.cerebras_api_key = "test-cerebras-api-key-for-ci"
    mock_settings.cerebras_api_base = "https://api.cerebras.ai/v1"
    mock_settings.cerebras_model = "gpt-oss-120b"
    mock_get_settings.return_value = mock_settings

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Optimized resume content"

    with patch(
        "app.services.ai_providers.completion", new_callable=AsyncMock
    ) as mock_completion:
        mock_completion.return_value = mock_response

        client = AIProviderClient(provider="cerebras")
        response = await client.chat_completion(
            system_prompt="Optimize this resume",
            user_message="John Doe, Software Engineer",
        )

        assert response == "Optimized resume content"
        mock_completion.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.ai_providers.get_settings")
async def test_chat_completion_fallback(mock_get_settings):
    """Test fallback to secondary provider when primary fails."""
    # Mock settings with API keys
    mock_settings = MagicMock()
    mock_settings.cerebras_api_key = "test-cerebras-api-key-for-ci"
    mock_settings.cerebras_api_base = "https://api.cerebras.ai/v1"
    mock_settings.cerebras_model = "gpt-oss-120b"
    mock_settings.openai_api_key = "test-openai-api-key-for-ci"
    mock_settings.openai_api_base = "https://api.openai.com/v1"
    mock_settings.openai_model = "gpt-4"
    mock_get_settings.return_value = mock_settings

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Fallback optimized content"

    with patch(
        "app.services.ai_providers.completion", new_callable=AsyncMock
    ) as mock_completion:
        # First call fails, second succeeds
        mock_completion.side_effect = [
            Exception("Primary provider failed"),
            mock_response,
        ]

        client = AIProviderClient(provider="cerebras")
        response = await client.chat_completion(
            system_prompt="Optimize this resume",
            user_message="John Doe, Software Engineer",
        )

        assert response == "Fallback optimized content"
        assert mock_completion.call_count == 2


@pytest.mark.asyncio
@patch("app.services.ai_providers.get_settings")
async def test_chat_completion_all_fail(mock_get_settings):
    """Test exception when all providers fail."""
    # Mock settings with API keys
    mock_settings = MagicMock()
    mock_settings.cerebras_api_key = "test-cerebras-api-key-for-ci"
    mock_settings.cerebras_api_base = "https://api.cerebras.ai/v1"
    mock_settings.cerebras_model = "gpt-oss-120b"
    mock_settings.openai_api_key = "test-openai-api-key-for-ci"
    mock_settings.openai_api_base = "https://api.openai.com/v1"
    mock_settings.openai_model = "gpt-4"
    mock_get_settings.return_value = mock_settings

    with patch(
        "app.services.ai_providers.completion", new_callable=AsyncMock
    ) as mock_completion:
        mock_completion.side_effect = Exception("All providers failed")

        client = AIProviderClient(provider="cerebras")

        with pytest.raises(Exception) as exc_info:
            await client.chat_completion(
                system_prompt="Optimize this resume",
                user_message="John Doe, Software Engineer",
            )

        assert "All providers failed" in str(exc_info.value)


def test_get_provider_info():
    """Test provider information retrieval."""
    # Mock the API key check to avoid MissingApiKeyError
    with patch("app.services.ai_providers.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "mock_api_key"
        mock_settings.cerebras_api_key = "mock_api_key"
        mock_settings.deepseek_api_key = "mock_api_key"
        mock_settings.api_key = "mock_api_key"
        mock_get_settings.return_value = mock_settings

        client = AIProviderClient(provider="openai")
        info = client.get_provider_info()

        assert info["provider"] == "openai"
        assert info["model"] == "openai/gpt-4-turbo"
        assert "fallback_models" in info
