from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from complex_app.orders.models import Order, OrderStatus
from complex_app.shared.errors import ValidationError


class OrderWorkflow:
    transitions: Dict[OrderStatus, List[OrderStatus]] = {
        OrderStatus.PENDING: [
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.CONFIRMED: [
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.PROCESSING: [
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.SHIPPED: [
            OrderStatus.DELIVERED,
        ],
        OrderStatus.DELIVERED: [],
        OrderStatus.CANCELLED: [
            OrderStatus.REFUNDED,
        ],
        OrderStatus.REFUNDED: [],
    }

    def __init__(self, order_service) -> None:
        self._order_service = order_service

    def validate_transition(
        self, from_status: OrderStatus, to_status: OrderStatus
    ) -> bool:
        allowed = self.transitions.get(from_status, [])
        return to_status in allowed

    def execute_transition(
        self, order: Order, target_status: OrderStatus, user_id: str
    ) -> Order:
        if not self.validate_transition(order.status, target_status):
            raise ValidationError(
                code="invalid_workflow_transition",
                message=(
                    f"Invalid order workflow transition: "
                    f"from {order.status.value} to {target_status.value}"
                ),
            )

        if target_status == OrderStatus.CANCELLED:
            return self._order_service.cancel_order(user_id, order.id)

        return self._order_service.update_order_status(order.id, target_status)
