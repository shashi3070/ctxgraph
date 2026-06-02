from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from dataflow.events.types import Event


class EventHandler(ABC):
    @abstractmethod
    def handle(self, event: Event) -> Any:
        ...


class AsyncEventHandler(EventHandler):
    async def handle_async(self, event: Event) -> Any:
        return self.handle(event)


class CallbackHandler(EventHandler):
    def __init__(self, callback: Callable[[Event], Any], name: Optional[str] = None):
        self._callback = callback
        self._name = name or callback.__name__

    def handle(self, event: Event) -> Any:
        return self._callback(event)

    def __repr__(self) -> str:
        return f"CallbackHandler({self._name})"


class LoggingHandler(EventHandler):
    def __init__(self, prefix: str = "[EVENT]"):
        self._prefix = prefix

    def handle(self, event: Event) -> None:
        print(f"{self._prefix} {event.type} from {event.source}")


class MetricsHandler(EventHandler):
    def __init__(self):
        self._event_counts: dict[str, int] = {}

    def handle(self, event: Event) -> None:
        self._event_counts[event.type] = self._event_counts.get(event.type, 0) + 1

    def get_count(self, event_type: str) -> int:
        return self._event_counts.get(event_type, 0)

    def reset(self) -> None:
        self._event_counts.clear()
