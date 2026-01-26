"""Tests for AIProviderClient using LiteLLM."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.ai_providers import AIProviderClient

@pytest.mark.asyncio
async def test_chat_completion_success():
    """Test successful chat completion with primary provider."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Optimized resume content"

    with patch("app.services.ai_providers.completion", new_callable=AsyncMock) as mock_completion:
        mock_completion.return_value = mock_response

        client = AIProviderClient(provider="cerebras")
        response = await client.chat_completion(
            system_prompt="Optimize this resume",
            user_message="John Doe, Software Engineer"
        )

        assert response == "Optimized resume content"
        mock_completion.assert_called_once()

@pytest.mark.asyncio
async def test_chat_completion_fallback():
    """Test fallback to secondary provider if primary fails."""
    mock_response_success = MagicMock()
    mock_response_success.choices = [MagicMock()]
    mock_response_success.choices[0].message = MagicMock()
    mock_response_success.choices[0].message.content = "Optimized resume content"

    with patch("app.services.ai_providers.completion", new_callable=AsyncMock) as mock_completion:
        mock_completion.side_effect = [
            Exception("Rate limit exceeded"),  # Primary fails
            mock_response_success
        ]

        client = AIProviderClient(provider="cerebras")
        response = await client.chat_completion(
            system_prompt="Optimize this resume",
            user_message="John Doe, Software Engineer"
        )

        assert response == "Optimized resume content"
        assert mock_completion.call_count == 2

@pytest.mark.asyncio
async def test_chat_completion_all_fail():
    """Test exception when all providers fail."""
    with patch("app.services.ai_providers.completion", new_callable=AsyncMock) as mock_completion:
        mock_completion.side_effect = Exception("All providers failed")

        client = AIProviderClient(provider="cerebras")
        with pytest.raises(Exception, match="All AI providers failed"):
            await client.chat_completion(
                system_prompt="Optimize this resume",
                user_message="John Doe, Software Engineer"
            )

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
