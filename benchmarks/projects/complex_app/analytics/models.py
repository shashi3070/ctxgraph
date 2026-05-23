from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from complex_app.shared.base import BaseModel


class EventType(Enum):
    PAGE_VIEW = "page_view"
    ORDER_CREATED = "order_created"
    ORDER_CANCELLED = "order_cancelled"
    PAYMENT_RECEIVED = "payment_received"
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    PRODUCT_VIEWED = "product_viewed"
    SEARCH_PERFORMED = "search_performed"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class AnalyticsEvent(BaseModel):
    event_type: EventType = EventType.PAGE_VIEW
    user_id: Optional[str] = None
    session_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    ip_address: str = ""
    user_agent: str = ""


@dataclass
class MetricDefinition:
    name: str = ""
    type: MetricType = MetricType.COUNTER
    unit: str = ""
    description: str = ""


@dataclass
class Report:
    name: str = ""
    metrics: List[str] = field(default_factory=list)
    date_range: tuple = ("", "")
    data: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""


@dataclass
class Dashboard:
    name: str = ""
    widgets: List[Dict[str, Any]] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 60
