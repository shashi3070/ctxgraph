"""Distributed tracing utilities for microservices."""

from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class SpanKind(str, Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    sampled: bool = True
    baggage: Dict[str, Any] = field(default_factory=dict)


_current_span: ContextVar[Optional[TraceContext]] = ContextVar("current_span", default=None)


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    kind: SpanKind = SpanKind.INTERNAL
    status: str = "OK"

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        self.end_time = datetime.utcnow()

    def duration_ms(self) -> float:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0


class Tracer:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._spans: list[Span] = []

    def start_span(
        self,
        name: str,
        parent: Optional[TraceContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        parent_ctx = parent or _current_span.get()
        span_id = str(uuid.uuid4())[:16]
        trace_id = parent_ctx.trace_id if parent_ctx else str(uuid.uuid4())
        parent_span_id = parent_ctx.span_id if parent_ctx else None

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            kind=kind,
            attributes=attributes or {}
        )
        self._spans.append(span)
        _current_span.set(TraceContext(trace_id, span_id, parent_span_id))
        return span

    @asynccontextmanager
    async def trace(self, name: str, kind: SpanKind = SpanKind.INTERNAL):
        span = self.start_span(name, kind=kind)
        try:
            yield span
        except Exception as e:
            span.status = "ERROR"
            span.set_attribute("error", str(e))
            raise
        finally:
            span.end()


def get_trace_context() -> Optional[TraceContext]:
    return _current_span.get()


def trace(name: str, kind: SpanKind = SpanKind.INTERNAL):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = Tracer(func.__module__)
            async with tracer.trace(name, kind):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
