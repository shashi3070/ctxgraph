from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Any, Optional


class Counter:
    def __init__(self, name: str, tags: Optional[dict] = None):
        self.name = name
        self.tags = tags or {}
        self._value: int = 0
        self._lock = Lock()

    def inc(self, amount: int = 1) -> None:
        with self._lock:
            self._value += amount

    @property
    def value(self) -> int:
        with self._lock:
            return self._value


class Gauge:
    def __init__(self, name: str, tags: Optional[dict] = None):
        self.name = name
        self.tags = tags or {}
        self._value: float = 0.0
        self._lock = Lock()

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    @property
    def value(self) -> float:
        with self._lock:
            return self._value


class Histogram:
    def __init__(self, name: str, tags: Optional[dict] = None):
        self.name = name
        self.tags = tags or {}
        self._values: list[float] = []
        self._lock = Lock()

    def observe(self, value: float) -> None:
        with self._lock:
            self._values.append(value)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._values)

    @property
    def sum(self) -> float:
        with self._lock:
            return sum(self._values)

    @property
    def avg(self) -> float:
        with self._lock:
            return sum(self._values) / max(len(self._values), 1)

    @property
    def max(self) -> float:
        with self._lock:
            return max(self._values) if self._values else 0.0

    @property
    def min(self) -> float:
        with self._lock:
            return min(self._values) if self._values else 0.0


class MetricsCollector:
    def __init__(self):
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._lock = Lock()
        self._start_time = time.time()

    def counter(self, name: str, tags: Optional[dict] = None) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, tags)
            return self._counters[name]

    def gauge(self, name: str, tags: Optional[dict] = None) -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, tags)
            return self._gauges[name]

    def histogram(self, name: str, tags: Optional[dict] = None) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, tags)
            return self._histograms[name]

    def record_success(self, name: str) -> None:
        self.counter("pipeline_success", {"name": name}).inc()
        self.counter("pipeline_total", {"name": name}).inc()

    def record_failure(self, name: str) -> None:
        self.counter("pipeline_failure", {"name": name}).inc()
        self.counter("pipeline_total", {"name": name}).inc()

    def record_duration(self, name: str, duration: float) -> None:
        self.histogram("pipeline_duration", {"name": name}).observe(duration)

    def uptime(self) -> float:
        return time.time() - self._start_time

    def to_dict(self) -> dict:
        return {
            "counters": {k: v.value for k, v in self._counters.items()},
            "gauges": {k: v.value for k, v in self._gauges.items()},
            "histograms": {
                k: {"count": v.count, "sum": v.sum, "avg": v.avg, "min": v.min, "max": v.max}
                for k, v in self._histograms.items()
            },
            "uptime": self.uptime(),
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._start_time = time.time()
