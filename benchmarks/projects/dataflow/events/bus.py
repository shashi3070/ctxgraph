from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Optional

from dataflow.events.handler import EventHandler
from dataflow.events.types import Event


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: list[EventHandler] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> EventBus:
        self._handlers[event_type].append(handler)
        return self

    def subscribe_all(self, handler: EventHandler) -> EventBus:
        self._wildcard_handlers.append(handler)
        return self

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: Event) -> None:
        for handler in self._wildcard_handlers:
            handler.handle(event)
        for handler in self._handlers.get(event.type, []):
            handler.handle(event)
        for handler in self._handlers.get("*", []):
            handler.handle(event)

    async def emit_async(self, event: Event) -> None:
        tasks = []
        for handler in self._wildcard_handlers:
            if hasattr(handler, "handle_async"):
                tasks.append(handler.handle_async(event))
            else:
                handler.handle(event)
        for handler in self._handlers.get(event.type, []):
            if hasattr(handler, "handle_async"):
                tasks.append(handler.handle_async(event))
            else:
                handler.handle(event)
        if tasks:
            await asyncio.gather(*tasks)

    def clear(self) -> None:
        self._handlers.clear()
        self._wildcard_handlers.clear()

    def handler_count(self) -> int:
        count = len(self._wildcard_handlers)
        for handlers in self._handlers.values():
            count += len(handlers)
        return count
