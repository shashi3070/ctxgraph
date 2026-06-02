from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Callable, Optional

from dataflow.processors.base import Processor


class AggregateProcessor(Processor):
    def __init__(self, name: str, aggregate_fn: Callable, config: Optional[dict] = None):
        super().__init__(name, config)
        self._aggregate_fn = aggregate_fn
        self._state: dict[str, Any] = {}

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if isinstance(data, list):
            return self._aggregate_fn(data, self._state, context or {})
        return self._aggregate_fn([data], self._state, context or {})

    def reset(self) -> None:
        self._state.clear()


class WindowProcessor(Processor):
    def __init__(self, name: str, window_size: int = 10, stride: int = 1, config: Optional[dict] = None):
        super().__init__(name, config)
        self._window_size = window_size
        self._stride = stride
        self._buffer: list = []

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if isinstance(data, list):
            self._buffer.extend(data)
        else:
            self._buffer.append(data)

        windows = []
        while len(self._buffer) >= self._window_size:
            window = self._buffer[:self._window_size]
            windows.append(window)
            self._buffer = self._buffer[self._stride:]
        return windows

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)


class GroupByProcessor(Processor):
    def __init__(self, name: str, key_fn: Callable, config: Optional[dict] = None):
        super().__init__(name, config)
        self._key_fn = key_fn

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if not isinstance(data, list):
            return {self._key_fn(data, context or {}): [data]}
        groups = defaultdict(list)
        for item in data:
            key = self._key_fn(item, context or {})
            groups[key].append(item)
        return dict(groups)


class SlidingWindowProcessor(WindowProcessor):
    def __init__(self, name: str, window_size: int = 10, stride: int = 1, ttl: float = 60.0, config: Optional[dict] = None):
        super().__init__(name, window_size, stride, config)
        self._ttl = ttl
        self._timestamps: list[float] = []

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        now = time.time()
        cutoff = now - self._ttl
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        while len(self._timestamps) > 0 and self._timestamps[0] <= cutoff:
            self._timestamps.pop(0)

        result = super().process(data, context)
        if isinstance(data, list):
            self._timestamps.extend([now] * len(data))
        else:
            self._timestamps.append(now)
        return result
