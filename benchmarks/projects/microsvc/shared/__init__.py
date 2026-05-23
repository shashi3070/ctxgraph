"""Shared utilities and libraries for microservices ecosystem."""

from shared.events import EventBus, Event, EventHandler
from shared.tracing import Tracer, TraceContext, trace
from shared.retry import retry, RetryPolicy, AsyncRetryPolicy
from shared.circuit_breaker import CircuitBreaker, CircuitState
from shared.logging import get_logger, structured_log
from shared.metrics import MetricsCollector, counter, histogram

__all__ = [
    "EventBus", "Event", "EventHandler",
    "Tracer", "TraceContext", "trace",
    "retry", "RetryPolicy", "AsyncRetryPolicy",
    "CircuitBreaker", "CircuitState",
    "get_logger", "structured_log",
    "MetricsCollector", "counter", "histogram"
]
