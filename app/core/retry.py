"""Retry logic utilities for external API calls.

This module provides robust retry mechanisms with exponential backoff,
circuit breaker pattern, and error handling for external service calls.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: List[Type[Exception]] = None
    non_retryable_exceptions: List[Type[Exception]] = None

    def __post_init__(self):
        """Initialize default exception lists."""
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [
                ConnectionError,
                TimeoutError,
                OSError,
                # Add common HTTP/network exceptions
            ]

        if self.non_retryable_exceptions is None:
            self.non_retryable_exceptions = [
                ValueError,
                KeyError,
                TypeError,
                # Add authentication/authorization errors
            ]


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascade failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to function."""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                self._on_success()
                return result

            except self.expected_exception as e:
                self._on_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result

            except self.expected_exception as e:
                self._on_failure()
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        return (
            self.last_failure_time
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class RetryManager:
    """Manager for retry logic with various strategies."""

    def __init__(self, config: RetryConfig = None):
        """Initialize retry manager.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()

    def __call__(self, func: Callable = None, *, config: RetryConfig = None):
        """Decorator to apply retry logic to function."""

        def decorator(f: Callable) -> Callable:
            retry_config = config or self.config

            @wraps(f)
            async def async_wrapper(*args, **kwargs):
                return await self._retry_async(f, retry_config, *args, **kwargs)

            @wraps(f)
            def sync_wrapper(*args, **kwargs):
                return self._retry_sync(f, retry_config, *args, **kwargs)

            return async_wrapper if asyncio.iscoroutinefunction(f) else sync_wrapper

        if func is None:
            return decorator
        else:
            return decorator(func)

    async def _retry_async(self, func: Callable, config: RetryConfig, *args, **kwargs):
        """Retry logic for async functions."""
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                return await func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                # Check if exception is non-retryable
                if any(
                    isinstance(e, exc_type)
                    for exc_type in config.non_retryable_exceptions
                ):
                    logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    raise

                # Check if exception is retryable
                if not any(
                    isinstance(e, exc_type) for exc_type in config.retryable_exceptions
                ):
                    logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    raise

                if attempt < config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)

        logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}")
        raise last_exception

    def _retry_sync(self, func: Callable, config: RetryConfig, *args, **kwargs):
        """Retry logic for sync functions."""
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                # Check if exception is non-retryable
                if any(
                    isinstance(e, exc_type)
                    for exc_type in config.non_retryable_exceptions
                ):
                    logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    raise

                # Check if exception is retryable
                if not any(
                    isinstance(e, exc_type) for exc_type in config.retryable_exceptions
                ):
                    logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    raise

                if attempt < config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)

        logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}")
        raise last_exception

    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for next retry attempt."""
        if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier**attempt)
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * (attempt + 1)
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        else:  # IMMEDIATE
            delay = 0

        # Apply maximum delay limit
        delay = min(delay, config.max_delay)

        # Add jitter to prevent thundering herd
        if config.jitter and delay > 0:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)


# Predefined retry configurations
API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    jitter=True,
)

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    jitter=True,
)

CONSERVATIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=60.0,
    strategy=RetryStrategy.LINEAR_BACKOFF,
    jitter=False,
)


# Decorator shortcuts
def retry_with_config(config: RetryConfig):
    """Retry decorator with custom configuration."""
    return RetryManager(config)


def retry_api_call(func: Callable = None, *, max_attempts: int = 3):
    """Retry decorator specifically for API calls."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True,
    )
    return RetryManager(config)(func)


def retry_database_call(func: Callable = None):
    """Retry decorator specifically for database calls."""
    config = RetryConfig(
        max_attempts=2,
        base_delay=0.5,
        max_delay=5.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True,
    )
    return RetryManager(config)(func)


# Context manager for retry operations
class RetryContext:
    """Context manager for retry operations."""

    def __init__(self, config: RetryConfig):
        """Initialize retry context.

        Args:
            config: Retry configuration
        """
        self.config = config
        self.attempt = 0

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt."""
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier**attempt)
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        else:  # IMMEDIATE
            delay = 0

        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter and delay > 0:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    async def __aenter__(self):
        """Enter context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context with retry logic."""
        if exc_type is None:
            return True  # Success, don't retry

        self.attempt += 1

        # Check if we should retry
        if self.attempt >= self.config.max_attempts:
            return False  # Don't retry, max attempts reached

        # Check if exception is retryable
        if any(
            isinstance(exc_val, exc_type)
            for exc_type in self.config.non_retryable_exceptions
        ):
            return False  # Don't retry, non-retryable exception

        if not any(
            isinstance(exc_val, exc_type)
            for exc_type in self.config.retryable_exceptions
        ):
            return False  # Don't retry, not in retryable list

        # Calculate delay and wait
        delay = self._calculate_delay(self.attempt - 1)
        logger.warning(f"Retrying after {delay:.2f}s (attempt {self.attempt + 1})")
        await asyncio.sleep(delay)

        return True  # Retry


# Utility functions
def is_retryable_error(error: Exception, config: RetryConfig = None) -> bool:
    """Check if an error is retryable.

    Args:
        error: Exception to check
        config: Retry configuration

    Returns:
        True if error is retryable, False otherwise
    """
    config = config or RetryConfig()

    # Check non-retryable first
    if any(isinstance(error, exc_type) for exc_type in config.non_retryable_exceptions):
        return False

    # Check retryable
    return any(isinstance(error, exc_type) for exc_type in config.retryable_exceptions)


def create_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception,
) -> CircuitBreaker:
    """Create a circuit breaker with specified parameters.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time to wait before attempting recovery
        expected_exception: Exception type that counts as failure

    Returns:
        CircuitBreaker instance
    """
    return CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)


# Combined decorators
def resilient_api_call(
    func: Callable = None,
    *,
    max_attempts: int = 3,
    circuit_breaker_threshold: int = 5,
):
    """Combined retry and circuit breaker decorator for API calls."""

    def decorator(f: Callable):
        # Apply circuit breaker first
        cb = create_circuit_breaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=60.0,
        )
        wrapped_func = cb(f)

        # Apply retry logic
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=1.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=True,
        )

        return RetryManager(config)(wrapped_func)

    if func is None:
        return decorator
    else:
        return decorator(func)
