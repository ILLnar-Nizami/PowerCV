"""AI Clients for Cerebras, OpenAI, and other providers."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=str(dotenv_path), override=True)

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
        model: str = "gpt-oss-120b",
    ):
        import os

        api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY not set")
        super().__init__(api_key, api_base, model)

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
        import os

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        super().__init__(api_key, api_base, model)

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


def get_ai_client(provider: str = "cerebras") -> AIClientBase:
    """Get the appropriate AI client based on provider."""
    if provider == "cerebras":
        return CerebrasClient()
    elif provider == "openai":
        return OpenAIClient()
    else:
        raise ValueError(f"Unknown AI provider: {provider}")
