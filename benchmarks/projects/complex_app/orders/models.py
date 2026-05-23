from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from complex_app.shared.base import BaseModel


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class CartItem:
    product_id: str = ""
    name: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0


@dataclass
class Cart(BaseModel):
    user_id: str = ""
    items: List[CartItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    coupon_code: Optional[str] = None
    discount: float = 0.0


@dataclass
class Order(BaseModel):
    user_id: str = ""
    items: List[CartItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    payment_id: Optional[str] = None
    invoice_id: Optional[str] = None
    coupon_code: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Shipment(BaseModel):
    order_id: str = ""
    carrier: str = ""
    tracking_number: str = ""
    status: str = ""
    estimated_delivery: Optional[str] = None
    delivered_at: Optional[str] = None
    items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Coupon:
    code: str = ""
    discount_type: str = "PERCENTAGE"
    discount_value: float = 0.0
    min_order_amount: float = 0.0
    max_uses: int = 100
    used_count: int = 0
    expires_at: Optional[str] = None
    is_active: bool = True
