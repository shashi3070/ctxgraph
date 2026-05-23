"""Prometheus metrics collection for microservices."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import functools
import time


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricLabel:
    name: str
    value: str


@dataclass
class Counter:
    name: str
    description: str
    labels: List[MetricLabel] = field(default_factory=list)
    _value: float = 0.0

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        self._value += amount

    def value(self) -> float:
        return self._value


@dataclass
class Gauge:
    name: str
    description: str
    labels: List[MetricLabel] = field(default_factory=list)
    _value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        self._value -= amount

    def set(self, value: float) -> None:
        self._value = value

    def value(self) -> float:
        return self._value


@dataclass
class Histogram:
    name: str
    description: str
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0])
    labels: List[MetricLabel] = field(default_factory=list)
    _buckets_count: Dict[float, int] = field(default_factory=dict)
    _sum: float = 0.0
    _count: int = 0

    def observe(self, value: float) -> None:
        self._sum += value
        self._count += 1
        for bucket in self.buckets:
            if value <= bucket:
                self._buckets_count[bucket] = self._buckets_count.get(bucket, 0) + 1

    def sum(self) -> float:
        return self._sum

    def count(self) -> int:
        return self._count


class MetricsCollector:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._start_time = datetime.utcnow()

    def counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[MetricLabel]] = None
    ) -> Counter:
        full_name = f"{self.service_name}_{name}"
        if full_name not in self._counters:
            self._counters[full_name] = Counter(
                name=full_name,
                description=description,
                labels=labels or []
            )
        return self._counters[full_name]

    def gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[MetricLabel]] = None
    ) -> Gauge:
        full_name = f"{self.service_name}_{name}"
        if full_name not in self._gauges:
            self._gauges[full_name] = Gauge(
                name=full_name,
                description=description,
                labels=labels or []
            )
        return self._gauges[full_name]

    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[List[MetricLabel]] = None
    ) -> Histogram:
        full_name = f"{self.service_name}_{name}"
        if full_name not in self._histograms:
            self._histograms[full_name] = Histogram(
                name=full_name,
                description=description,
                buckets=buckets or Histogram.__dataclass_fields__["buckets"].default_factory(),
                labels=labels or []
            )
        return self._histograms[full_name]

    def increment_counter(self, name: str, amount: float = 1.0) -> None:
        self.counter(name).inc(amount)

    def set_gauge(self, name: str, value: float) -> None:
        self.gauge(name).set(value)

    def observe_histogram(self, name: str, value: float) -> None:
        self.histogram(name).observe(value)

    def generate_report(self) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds(),
            "counters": {k: v.value() for k, v in self._counters.items()},
            "gauges": {k: v.value() for k, v in self._gauges.items()},
            "histograms": {
                k: {"count": v.count(), "sum": v.sum()}
                for k, v in self._histograms.items()
            }
        }


_collectors: Dict[str, MetricsCollector] = {}


def get_collector(service_name: str) -> MetricsCollector:
    if service_name not in _collectors:
        _collectors[service_name] = MetricsCollector(service_name)
    return _collectors[service_name]


def counter(name: str, description: str = "", service: str = "default"):
    def decorator(func: Callable) -> Callable:
        collector = get_collector(service)
        metric = collector.counter(name, description)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                metric.inc()
                return result
            except Exception:
                metric.inc()
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                metric.inc()
                return result
            except Exception:
                metric.inc()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def histogram(name: str, description: str = "", service: str = "default"):
    def decorator(func: Callable) -> Callable:
        collector = get_collector(service)
        metric = collector.histogram(name, description)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.monotonic() - start
                metric.observe(duration)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.monotonic() - start
                metric.observe(duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
