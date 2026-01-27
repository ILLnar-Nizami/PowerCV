"""Redis configuration and connection management."""

import logging
import os
from typing import Optional

import redis.asyncio as redis

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Get the Redis client instance, creating it if it doesn't exist."""
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        redis_url = settings.redis_url or "redis://localhost:6379"

        # Create Redis client
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )

        logger.info(f"Redis client initialized with URL: {redis_url}")

    return _redis_client


async def close_redis():
    """Close the Redis connection."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


async def test_redis_connection():
    """Test Redis connection."""
    try:
        redis_client = get_redis()
        await redis_client.ping()
        logger.info("Redis connection test successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False
