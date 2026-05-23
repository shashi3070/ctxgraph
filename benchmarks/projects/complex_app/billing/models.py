from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from complex_app.shared.base import BaseModel


@dataclass
class PaymentMethod(BaseModel):
    user_id: str = ""
    type: str = ""
    last_four: str = ""
    expiry_month: int = 1
    expiry_year: int = 2026
    is_default: bool = False
    billing_address: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice(BaseModel):
    user_id: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    status: str = "pending"
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    payment_method_id: Optional[str] = None


@dataclass
class Subscription(BaseModel):
    user_id: str = ""
    plan_id: str = ""
    status: str = "active"
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    trial_end: Optional[str] = None


@dataclass
class Plan:
    id: str = ""
    name: str = ""
    description: str = ""
    price: float = 0.0
    currency: str = "USD"
    interval: str = "month"
    features: List[str] = field(default_factory=list)
    trial_days: int = 0
