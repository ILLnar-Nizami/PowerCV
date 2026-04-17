"""Tests for enhanced AI providers - runs in ai-service context."""

import os
import sys

# Setup path to ai-service from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ai_service_path = os.path.join(project_root, "ai-service")
sys.path.insert(0, ai_service_path)
os.chdir(ai_service_path)

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from clients.providers import (
    AIClientBase,
    AnthropicClient,
    CerebrasClient,
    DeepSeekClient,
    GoogleGeminiClient,
    OllamaClient,
    OpenAIClient,
    OpenRouterClient,
    get_ai_client,
)


class TestAIClientBase:
    """Test base AI client functionality."""

    @pytest.mark.asyncio
    async def test_base_class_raises_not_implemented(self):
        """Test base class raises NotImplementedError."""
        client = AIClientBase("key", "http://base", "model")

        with pytest.raises(NotImplementedError):
            await client.chat_completion([])


class TestGetAIClient:
    """Test AI client factory function."""

    @patch.dict("os.environ", {"CEREBRAS_API_KEY": "test-key"})
    def test_get_cerebras_client(self):
        """Test getting Cerebras client."""
        client = get_ai_client("cerebras")
        assert isinstance(client, CerebrasClient)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_get_openai_client(self):
        """Test getting OpenAI client."""
        client = get_ai_client("openai")
        assert isinstance(client, OpenAIClient)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_get_anthropic_client(self):
        """Test getting Anthropic client."""
        client = get_ai_client("anthropic")
        assert isinstance(client, AnthropicClient)

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    def test_get_deepseek_client(self):
        """Test getting DeepSeek client."""
        client = get_ai_client("deepseek")
        assert isinstance(client, DeepSeekClient)

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"})
    def test_get_google_client(self):
        """Test getting Google Gemini client."""
        client = get_ai_client("google")
        assert isinstance(client, GoogleGeminiClient)

    def test_get_ollama_client(self):
        """Test getting Ollama client (no API key required)."""
        client = get_ai_client("ollama")
        assert isinstance(client, OllamaClient)

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_get_openrouter_client(self):
        """Test getting OpenRouter client."""
        client = get_ai_client("openrouter")
        assert isinstance(client, OpenRouterClient)

    def test_get_ai_client_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        with patch.dict("os.environ", {"CEREBRAS_API_KEY": "test-key"}):
            client = get_ai_client("CEREBRAS")
            assert isinstance(client, CerebrasClient)

            client = get_ai_client("CeReBrAs")
            assert isinstance(client, CerebrasClient)

    def test_get_ai_client_invalid_provider(self):
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_ai_client("invalid_provider")

        assert "Unknown AI provider" in str(exc_info.value)


class TestOllamaClient:
    """Test Ollama client."""

    @pytest.mark.asyncio
    @patch("clients.providers.httpx.AsyncClient")
    async def test_chat_completion(self, mock_client_class):
        """Test Ollama chat completion."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"message": {"content": "test"}})

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = OllamaClient(api_base="http://localhost:11434", model="llama3.1")
        result = await client.chat_completion([{"role": "user", "content": "hello"}])

        assert "message" in result


class TestAnthropicClient:
    """Test Anthropic client."""

    @pytest.mark.asyncio
    @patch("clients.providers.httpx.AsyncClient")
    async def test_chat_completion(self, mock_client_class):
        """Test Anthropic chat completion."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"content": [{"text": "test"}]})

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            client = AnthropicClient(api_key="test-key")
            result = await client.chat_completion(
                [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "hello"},
                ]
            )

        assert "content" in result


class TestDeepSeekClient:
    """Test DeepSeek client."""

    @pytest.mark.asyncio
    @patch("clients.providers.httpx.AsyncClient")
    async def test_chat_completion(self, mock_client_class):
        """Test DeepSeek chat completion."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={"choices": [{"message": {"content": "test"}}]}
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
            client = DeepSeekClient(api_key="test-key")
            result = await client.chat_completion(
                [{"role": "user", "content": "hello"}]
            )

        assert "choices" in result


class TestGoogleGeminiClient:
    """Test Google Gemini client."""

    @pytest.mark.asyncio
    @patch("clients.providers.httpx.AsyncClient")
    async def test_chat_completion(self, mock_client_class):
        """Test Google Gemini chat completion."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={"candidates": [{"content": {"parts": [{"text": "test"}]}}]}
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            client = GoogleGeminiClient(api_key="test-key")
            result = await client.chat_completion(
                [{"role": "user", "content": "hello"}]
            )

        assert "candidates" in result


class TestOpenRouterClient:
    """Test OpenRouter client."""

    @pytest.mark.asyncio
    @patch("clients.providers.httpx.AsyncClient")
    async def test_chat_completion(self, mock_client_class):
        """Test OpenRouter chat completion."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={"choices": [{"message": {"content": "test"}}]}
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            client = OpenRouterClient(api_key="test-key")
            result = await client.chat_completion(
                [{"role": "user", "content": "hello"}]
            )

        assert "choices" in result
