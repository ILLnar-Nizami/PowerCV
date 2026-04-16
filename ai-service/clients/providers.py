"""AI Clients for Cerebras, OpenAI, Anthropic, DeepSeek, Google, Ollama, and other providers."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# Load environment variables once at module level
dotenv_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=str(dotenv_path))

logger = logging.getLogger(__name__)


class AIClientBase:
    """Base class for AI clients."""

    def __init__(self, api_key: str, api_base: str, model: str = ""):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class CerebrasClient(AIClientBase):
    """Cerebras API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.cerebras.ai/v1",
        model: str = "llama3.1-8b",
    ):
        self.api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not set")
        super().__init__(self.api_key, api_base, model)

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Make a chat completion request to Cerebras."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_tokens": kwargs.get("max_tokens", 4096),
                },
            )
            response.raise_for_status()
            return response.json()


class OpenAIClient(AIClientBase):
    """OpenAI API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        super().__init__(self.api_key, api_base, model)

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Make a chat completion request to OpenAI."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_tokens": kwargs.get("max_tokens", 4096),
                },
            )
            response.raise_for_status()
            return response.json()


class AnthropicClient(AIClientBase):
    """Anthropic Claude API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.anthropic.com/v1",
        model: str = "claude-sonnet-4-20250514",
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        super().__init__(self.api_key, api_base, model)

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Make a chat completion request to Anthropic."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            system_message = ""
            anthropic_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    anthropic_messages.append(
                        {
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        }
                    )

            response = await client.post(
                f"{self.api_base}/messages",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": kwargs.get("max_tokens", 4096),
                    "system": system_message,
                    "messages": anthropic_messages,
                    "temperature": kwargs.get("temperature", 0.3),
                },
            )
            response.raise_for_status()
            return response.json()


class DeepSeekClient(AIClientBase):
    """DeepSeek API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        super().__init__(self.api_key, api_base, model)

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Make a chat completion request to DeepSeek."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_tokens": kwargs.get("max_tokens", 4096),
                },
            )
            response.raise_for_status()
            return response.json()


class GoogleGeminiClient(AIClientBase):
    """Google Gemini API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "gemini-2.0-flash",
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        super().__init__(self.api_key, api_base, model)

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Make a chat completion request to Google Gemini."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            contents = []
            for msg in messages:
                if msg.get("role") == "user":
                    parts = [{"text": msg.get("content", "")}]
                elif msg.get("role") == "assistant":
                    parts = [{"text": msg.get("content", "")}]
                else:
                    continue
                contents.append(
                    {
                        "role": "model" if msg.get("role") == "assistant" else "user",
                        "parts": parts,
                    }
                )

            response = await client.post(
                f"{self.api_base}/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": kwargs.get("temperature", 0.3),
                        "maxOutputTokens": kwargs.get("max_tokens", 4096),
                    },
                },
            )
            response.raise_for_status()
            return response.json()


class OllamaClient(AIClientBase):
    """Ollama local AI client."""

    def __init__(
        self,
        api_base: str = "http://localhost:11434",
        model: str = "llama3.1",
    ):
        super().__init__("", api_base, model)

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Make a chat completion request to Ollama."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            ollama_messages = []
            for msg in messages:
                if msg.get("role") != "system":
                    ollama_messages.append(
                        {
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        }
                    )

            response = await client.post(
                f"{self.api_base}/api/chat",
                json={
                    "model": self.model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.3),
                        "num_predict": kwargs.get("max_tokens", 4096),
                    },
                },
            )
            response.raise_for_status()
            return response.json()


class OpenRouterClient(AIClientBase):
    """OpenRouter aggregate API client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://openrouter.ai/api/v1",
        model: str = "anthropic/claude-3.5-sonnet",
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        super().__init__(self.api_key, api_base, model)

    async def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Make a chat completion request to OpenRouter."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_tokens": kwargs.get("max_tokens", 4096),
                },
            )
            response.raise_for_status()
            return response.json()


def get_ai_client(provider: str = "cerebras") -> AIClientBase:
    """Get the appropriate AI client based on provider.

    Supported providers:
    - cerebras: Cerebras AI (fast, cheap inference)
    - openai: OpenAI GPT models
    - anthropic: Anthropic Claude models
    - deepseek: DeepSeek models
    - google: Google Gemini models
    - ollama: Local Ollama models
    - openrouter: OpenRouter aggregate API
    """
    provider = provider.lower()

    if provider == "cerebras":
        return CerebrasClient()
    elif provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    elif provider == "deepseek":
        return DeepSeekClient()
    elif provider == "google":
        return GoogleGeminiClient()
    elif provider == "ollama":
        return OllamaClient()
    elif provider == "openrouter":
        return OpenRouterClient()
    else:
        raise ValueError(
            f"Unknown AI provider: {provider}. "
            f"Supported: cerebras, openai, anthropic, deepseek, google, ollama, openrouter"
        )
