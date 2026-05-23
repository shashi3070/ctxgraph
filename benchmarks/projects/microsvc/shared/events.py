"""Event bus implementation for pub/sub communication between services."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import asyncio
import uuid


class EventType(str, Enum):
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    SUBSCRIPTION_STARTED = "subscription.started"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    NOTIFICATION_SENT = "notification.sent"
    AUTH_TOKEN_ISSUED = "auth.token.issued"
    AUTH_TOKEN_EXPIRED = "auth.token.expired"


@dataclass
class Event:
    event_type: EventType
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""
    correlation_id: Optional[str] = None


class EventHandler(ABC):
    @abstractmethod
    async def handle(self, event: Event) -> None:
        pass


class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._pending_events: asyncio.Queue = asyncio.Queue()

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h is not handler
            ]

    async def publish(self, event: Event) -> None:
        await self._pending_events.put(event)
        await self._dispatch(event)

    async def _dispatch(self, event: Event) -> None:
        handlers = self._subscribers.get(event.event_type, [])
        await asyncio.gather(
            *[handler.handle(event) for handler in handlers],
            return_exceptions=True
        )


_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
