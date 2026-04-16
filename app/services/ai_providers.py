"""Multi-provider AI client using LiteLLM for unified management."""

import hashlib
import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from litellm import completion, exceptions

from app.config.redis import get_redis
from app.config.settings import get_settings
from app.core.exceptions import MissingApiKeyError

load_dotenv()
logger = logging.getLogger(__name__)


class AIProviderClient:
    """Supports multiple cloud-based AI providers via LiteLLM."""

    # Supported providers and their models
    PROVIDERS = {
        "cerebras": {
            "model": "llama3.1-8b",
            "fallback": ["deepseek/deepseek-chat"],
            "key": "CEREBRAS_API_KEY",
        },
        "openai": {
            "model": "gpt-4o-mini",
            "fallback": ["deepseek/deepseek-chat"],
            "key": "OPENAI_API_KEY",
        },
        "deepseek": {
            "model": "deepseek/deepseek-chat",
            "fallback": ["openai/gpt-4o-mini"],
            "key": "DEEPSEEK_API_KEY",
        },
    }

    def __init__(self, provider: Optional[str] = None):
        """Initialize AI client with specified provider.

        Args:
            provider: AI provider name ('cerebras', 'openai', 'deepseek')
                     If None, uses AI_PROVIDER env variable, defaults to 'cerebras'
        """
        self.provider = provider or os.getenv("AI_PROVIDER", "cerebras")
        self.redis = get_redis()
        # Cost tracking
        self.cost_tracker = {"total_cost": 0.0, "total_tokens": 0, "requests": 0}

        if self.provider not in self.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {self.provider}. "
                f"Supported: {list(self.PROVIDERS.keys())}"
            )

        settings = get_settings()
        config = self.PROVIDERS[self.provider]
        self.model = config["model"]
        self.fallback_models = config["fallback"]
        self.api_key = getattr(settings, config["key"].lower(), None)

        if not self.api_key:
            raise MissingApiKeyError(str(config["key"]), str(self.provider))

        logger.info(f"Initialized AI client: {self.provider} ({self.model})")

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 60,
    ) -> str:
        """Send chat completion request with fallback support, Redis caching, and cost tracking.

        Args:
            system_prompt: System instructions
            user_message: User's input
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Returns:
            str: Model's response

        Raises:
            Exception: If all providers fail
        """
        # Create cache key from inputs (using SHA-256 for better security than MD5)
        cache_key = f"ai_completion:{hashlib.sha256(f'{self.provider}:{self.model}:{system_prompt}:{user_message}:{temperature}:{max_tokens}'.encode()).hexdigest()}"

        # Try to get from cache first
        cached_response = await self.redis.get(cache_key)
        if cached_response:
            logger.info("Returning cached AI response")
            return cached_response

        # Increment request count
        self.cost_tracker["requests"] += 1

        # Try primary provider first
        models_to_try = [self.model] + self.fallback_models
        last_exception = None

        for model in models_to_try:
            try:
                logger.debug(f"Attempting completion with model: {model}")
                response = await completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )

                content = response.choices[0].message.content
                logger.debug(
                    f"Response received from {model}: {len(content or '')} chars"
                )

                # Track cost and tokens (simplified estimation)
                if hasattr(response, "usage") and response.usage:
                    prompt_tokens = response.usage.get("prompt_tokens", 0)
                    completion_tokens = response.usage.get("completion_tokens", 0)
                    total_tokens = prompt_tokens + completion_tokens

                    # Simplified cost calculation (replace with actual pricing)
                    cost = (prompt_tokens * 0.00001) + (completion_tokens * 0.00003)
                    self.cost_tracker["total_cost"] += cost
                    self.cost_tracker["total_tokens"] += total_tokens

                    logger.info(f"AI cost: ${cost:.6f}, tokens: {total_tokens}")

                # Cache the response for 1 hour
                if content:
                    await self.redis.setex(cache_key, 3600, content)

                return content or ""

            except exceptions.RateLimitError as e:
                logger.warning(f"Rate limit exceeded for {model}: {str(e)}")
                last_exception = e
                continue

            except exceptions.Timeout as e:
                logger.warning(f"Timeout for {model}: {str(e)}")
                last_exception = e
                continue

            except exceptions.APIError as e:
                logger.warning(f"API error for {model}: {str(e)}")
                last_exception = e
                continue

            except Exception as e:
                logger.error(
                    f"Unexpected error with {model}: {type(e).__name__}: {str(e)}"
                )
                last_exception = e
                continue

        # If all providers failed
        error_msg = f"All AI providers failed. Last error: {type(last_exception).__name__}: {str(last_exception)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def get_provider_info(self) -> Dict[str, Any]:
        """Get current provider information."""
        return {
            "provider": self.provider,
            "model": self.model,
            "fallback_models": self.fallback_models,
        }


# Convenience function for backward compatibility
def get_ai_client(provider: Optional[str] = None) -> AIProviderClient:
    """Get AI client instance.

    Args:
        provider: Optional provider override

    Returns:
        AIProviderClient: Configured client instance
    """
    return AIProviderClient(provider=provider)


# Backwards compatibility: keep the old name available
AIClient = AIProviderClient

__all__ = ["AIProviderClient", "AIClient", "get_ai_client"]
