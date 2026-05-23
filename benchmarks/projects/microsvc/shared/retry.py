"""Retry policy with exponential backoff for resilient service calls."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, List, Optional, Tuple, Type, Union
import asyncio
import functools
import random


class BackoffStrategy(str, Enum):
    CONSTANT = "constant"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    FULL_JITTER = "full_jitter"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 30000
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    jitter: bool = True

    def calculate_delay(self, attempt: int) -> float:
        if attempt <= 0:
            return 0

        delay_ms = self.initial_delay_ms

        if self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay_ms = self.initial_delay_ms * (2 ** (attempt - 1))
        elif self.backoff_strategy == BackoffStrategy.FIBONACCI:
            a, b = 0, self.initial_delay_ms
            for _ in range(attempt - 1):
                a, b = b, a + b
            delay_ms = b
        elif self.backoff_strategy == BackoffStrategy.FULL_JITTER:
            delay_ms = self.initial_delay_ms * (2 ** (attempt - 1))
            delay_ms = random.uniform(0, delay_ms)

        delay_ms = min(delay_ms, self.max_delay_ms)

        if self.jitter and self.backoff_strategy != BackoffStrategy.FULL_JITTER:
            delay_ms = delay_ms * (0.5 + random.random())

        return delay_ms / 1000.0

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        if attempt >= self.max_attempts:
            return False
        return isinstance(exception, self.retry_on_exceptions)


class AsyncRetryPolicy(RetryPolicy):
    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        attempt = 0
        while True:
            attempt += 1
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except Exception as e:
                if not self.should_retry(attempt, e):
                    raise
                delay = self.calculate_delay(attempt)
                await asyncio.sleep(delay)


def retry(
    max_attempts: int = 3,
    initial_delay_ms: int = 100,
    max_delay_ms: int = 30000,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    policy = AsyncRetryPolicy(
        max_attempts=max_attempts,
        initial_delay_ms=initial_delay_ms,
        max_delay_ms=max_delay_ms,
        backoff_strategy=backoff_strategy,
        retry_on_exceptions=retry_on_exceptions
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await policy.execute(func, *args, **kwargs)
        return wrapper
    return decorator
