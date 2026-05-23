"""Circuit breaker pattern for preventing cascading failures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import asyncio
import functools
import time


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    pass


class CircuitOpenError(CircuitBreakerError):
    pass


@dataclass
class CircuitBreakerMetrics:
    success_count: int = 0
    failure_count: int = 0
    slow_count: int = 0
    timeout_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_failure_exception: Optional[Exception] = None


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout_ms: int = 30000
    expected_exception_types: tuple = (Exception,)
    slow_call_threshold_ms: int = 5000
    slow_call_ratio_threshold: float = 1.0
    minimum_number_of_calls: int = 10
    sliding_window_size: int = 100
    permitted_number_of_calls_in_half_open: int = 3

    _state: CircuitState = CircuitState.CLOSED
    _metrics: CircuitBreakerMetrics = field(default_factory=CircuitBreakerMetrics)
    _open_time: Optional[datetime] = None
    _half_open_attempts: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def state(self) -> CircuitState:
        self._try_auto_transition_from_open()
        return self._state

    def _try_auto_transition_from_open(self) -> None:
        if self._state == CircuitState.OPEN and self._open_time:
            elapsed_ms = (datetime.utcnow() - self._open_time).total_seconds() * 1000
            if elapsed_ms >= self.recovery_timeout_ms:
                self._state = CircuitState.HALF_OPEN
                self._half_open_attempts = 0

    def _record_success(self) -> None:
        self._metrics.success_count += 1
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_attempts += 1
            if self._half_open_attempts >= self.permitted_number_of_calls_in_half_open:
                self._transition_to_closed()

    def _record_failure(self, exception: Exception) -> None:
        self._metrics.failure_count += 1
        self._metrics.last_failure_time = datetime.utcnow()
        self._metrics.last_failure_exception = exception

        if self._state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif self._state == CircuitState.CLOSED:
            total_calls = self._metrics.success_count + self._metrics.failure_count
            if total_calls >= self.minimum_number_of_calls:
                failure_ratio = self._metrics.failure_count / total_calls
                if self._metrics.failure_count >= self.failure_threshold:
                    self._transition_to_open()

    def _transition_to_open(self) -> None:
        self._state = CircuitState.OPEN
        self._open_time = datetime.utcnow()

    def _transition_to_closed(self) -> None:
        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        self._open_time = None

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            current_state = self.state
            if current_state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is OPEN. "
                    f"Last error: {self._metrics.last_failure_exception}"
                )

        try:
            start_time = time.monotonic()
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            async with self._lock:
                if elapsed_ms > self.slow_call_threshold_ms:
                    self._metrics.slow_count += 1
                self._record_success()
            return result

        except self.expected_exception_types as e:
            async with self._lock:
                self._record_failure(e)
            raise

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await self.execute(func, *args, **kwargs)
        return wrapper


_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout_ms: int = 30000
) -> CircuitBreaker:
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout_ms=recovery_timeout_ms
        )
    return _circuit_breakers[name]
