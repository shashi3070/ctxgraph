from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from complex_app.shared.base import BaseModel


@dataclass
class Category(BaseModel):
    name: str = ""
    slug: str = ""
    description: str = ""
    parent_id: Optional[str] = None
    sort_order: int = 0


@dataclass
class Product(BaseModel):
    name: str = ""
    slug: str = ""
    description: str = ""
    price: float = 0.0
    currency: str = "USD"
    category_id: str = ""
    tags: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    image_urls: List[str] = field(default_factory=list)


@dataclass
class StockItem(BaseModel):
    product_id: str = ""
    warehouse_id: str = ""
    quantity: int = 0
    reserved_quantity: int = 0
    reorder_point: int = 0
    reorder_quantity: int = 0


@dataclass
class Warehouse(BaseModel):
    name: str = ""
    location: str = ""
    is_active: bool = True
    capacity: int = 0
    used_capacity: int = 0


class TransactionType(Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"


@dataclass
class InventoryTransaction:
    product_id: str = ""
    warehouse_id: str = ""
    type: TransactionType = TransactionType.IN
    quantity: int = 0
    reference: str = ""
    user_id: str = ""
