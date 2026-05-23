from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from complex_app.orders.models import Cart, Coupon, Order, OrderStatus
from complex_app.shared.base import BaseService
from complex_app.shared.config import get_config
from complex_app.shared.database import get_database
from complex_app.shared.errors import NotFoundError, ValidationError


class OrderService(BaseService):
    def __init__(
        self,
        db,
        cache,
        auth_service,
        billing_service,
        inventory_service,
        notification_service,
        analytics_service,
    ) -> None:
        self._db = db
        self._cache = cache
        self._auth_service = auth_service
        self._billing_service = billing_service
        self._inventory_service = inventory_service
        self._notification_service = notification_service
        self._analytics_service = analytics_service

    def _validate(self, user=None) -> None:
        self._auth_service._validate(user)

    def _authorize(self, user=None) -> None:
        self._auth_service._authorize(user)

    def create_order(
        self,
        user_id: str,
        cart: Cart,
        payment_method_id: str,
        shipping_address: Dict[str, Any],
    ) -> Order:
        user = self._auth_service.get_user(user_id)
        self._validate(user)
        self._authorize(user)

        for item in cart.items:
            stock_ok = self._inventory_service.check_stock(
                item.product_id, warehouse_id="default"
            )
            if not stock_ok:
                raise ValidationError(
                    code="insufficient_stock",
                    message=f"Insufficient stock for product {item.product_id}",
                )

        config = get_config()
        currency = "USD"

        payment = self._billing_service.process_payment(
            user_id, cart.total, currency, payment_method_id
        )

        for item in cart.items:
            self._inventory_service.reserve_stock(
                item.product_id, "default", item.quantity
            )

        invoice = self._billing_service.generate_invoice(
            user_id, cart.items, cart.total, currency
        )

        order = Order(
            user_id=user_id,
            items=cart.items,
            subtotal=cart.subtotal,
            tax=cart.tax,
            total=cart.total,
            status=OrderStatus.CONFIRMED,
            shipping_address=shipping_address,
            billing_address=payment.get("billing_address"),
            payment_id=payment.get("id"),
            invoice_id=invoice.get("id"),
            coupon_code=cart.coupon_code,
        )

        self._db.execute(
            "INSERT INTO orders (id, user_id, subtotal, tax, total, status, payment_id, invoice_id, coupon_code, created_at, updated_at) VALUES (:id, :user_id, :subtotal, :tax, :total, :status, :payment_id, :invoice_id, :coupon_code, :created_at, :updated_at)",
            order.to_dict(),
        )

        self._notification_service.send_notification(
            user_id,
            "order_confirmation",
            {
                "order_id": order.id,
                "total": order.total,
                "items": len(order.items),
            },
        )

        self._analytics_service.track_event(
            "order_created",
            {
                "user_id": user_id,
                "order_id": order.id,
                "total": order.total,
                "item_count": len(order.items),
            },
        )

        return order

    def cancel_order(self, user_id: str, order_id: str) -> Order:
        user = self._auth_service.get_user(user_id)
        self._validate(user)
        self._authorize(user)

        order = self.get_order(order_id)

        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ValidationError(
                code="cannot_cancel",
                message=f"Cannot cancel order in status {order.status.value}",
            )

        for item in order.items:
            self._inventory_service.release_stock(
                item.product_id, "default", item.quantity
            )

        if order.payment_id:
            self._billing_service.process_refund(
                user_id, order.payment_id, order.total, "USD"
            )

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc).isoformat()

        self._db.execute(
            "UPDATE orders SET status = :status, updated_at = :updated_at WHERE id = :id",
            {"status": order.status.value, "updated_at": order.updated_at, "id": order.id},
        )

        self._notification_service.send_notification(
            user_id,
            "order_cancelled",
            {
                "order_id": order.id,
                "status": order.status.value,
            },
        )

        self._analytics_service.track_event(
            "order_cancelled",
            {
                "user_id": user_id,
                "order_id": order.id,
                "previous_status": order.status.value,
            },
        )

        return order

    def get_order(self, order_id: str) -> Order:
        rows = self._db.fetch_all(
            "SELECT * FROM orders WHERE id = :id", {"id": order_id}
        )
        order_data = rows[0] if rows else None

        if not order_data:
            raise NotFoundError(
                code="order_not_found", message=f"Order {order_id} not found"
            )

        return Order.from_dict(order_data)

    def list_user_orders(
        self, user_id: str, page: int = 1, per_page: int = 20
    ) -> List[Order]:
        offset = (page - 1) * per_page
        rows = self._db.fetch_all(
            "SELECT * FROM orders WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit OFFSET :offset",
            {"user_id": user_id, "limit": per_page, "offset": offset},
        )
        return [Order.from_dict(r) for r in rows]

    def update_order_status(
        self, order_id: str, status: OrderStatus
    ) -> Order:
        order = self.get_order(order_id)

        if not self._is_valid_transition(order.status, status):
            raise ValidationError(
                code="invalid_status_transition",
                message=f"Cannot transition from {order.status.value} to {status.value}",
            )

        order.status = status
        order.updated_at = datetime.now(timezone.utc).isoformat()

        self._db.execute(
            "UPDATE orders SET status = :status, updated_at = :updated_at WHERE id = :id",
            {"status": order.status.value, "updated_at": order.updated_at, "id": order.id},
        )

        self._analytics_service.track_event(
            "order_status_changed",
            {
                "order_id": order.id,
                "from_status": order.status.value,
                "to_status": status.value,
            },
        )

        if status == OrderStatus.SHIPPED:
            self._notification_service.send_notification(
                order.user_id,
                "order_shipped",
                {"order_id": order.id},
            )
        elif status == OrderStatus.DELIVERED:
            self._notification_service.send_notification(
                order.user_id,
                "order_delivered",
                {"order_id": order.id},
            )

        return order

    def apply_coupon(self, code: str, cart_total: float) -> Dict[str, Any]:
        rows = self._db.fetch_all(
            "SELECT * FROM coupons WHERE code = :code", {"code": code}
        )
        data = rows[0] if rows else None

        if not data:
            raise NotFoundError(
                code="coupon_not_found", message=f"Coupon {code} not found"
            )

        coupon = Coupon(**data)

        if not coupon.is_active:
            raise ValidationError(
                code="coupon_inactive", message="Coupon is no longer active"
            )

        if coupon.expires_at:
            expires = datetime.fromisoformat(coupon.expires_at)
            if expires < datetime.now(timezone.utc):
                raise ValidationError(
                    code="coupon_expired", message="Coupon has expired"
                )

        if coupon.used_count >= coupon.max_uses:
            raise ValidationError(
                code="coupon_exhausted", message="Coupon usage limit reached"
            )

        if cart_total < coupon.min_order_amount:
            raise ValidationError(
                code="min_order_not_met",
                message=f"Minimum order amount of {coupon.min_order_amount} not met",
            )

        if coupon.discount_type == "PERCENTAGE":
            discount = cart_total * (coupon.discount_value / 100)
        else:
            discount = min(coupon.discount_value, cart_total)

        return {
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
            "discount": round(discount, 2),
            "total_after_discount": round(cart_total - discount, 2),
        }

    def _is_valid_transition(
        self, from_status: OrderStatus, to_status: OrderStatus
    ) -> bool:
        valid_transitions = {
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
        return to_status in valid_transitions.get(from_status, [])
