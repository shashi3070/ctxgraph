from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from complex_app.shared.base import BaseModel


class NotificationType(Enum):
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification(BaseModel):
    user_id: str = ""
    type: NotificationType = NotificationType.EMAIL
    title: str = ""
    body: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.MEDIUM
    read_at: Optional[str] = None
    sent_at: Optional[str] = None
    status: str = "pending"


@dataclass
class NotificationTemplate:
    name: str = ""
    subject: str = ""
    body_template: str = ""
    type: NotificationType = NotificationType.EMAIL
    variables: List[str] = field(default_factory=list)


@dataclass
class NotificationPreference:
    user_id: str = ""
    type: NotificationType = NotificationType.EMAIL
    enabled: bool = True
    digest_frequency: str = "instant"
