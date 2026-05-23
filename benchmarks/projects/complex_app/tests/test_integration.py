from __future__ import annotations

from complex_app.analytics.models import EventType
from complex_app.analytics.service import AnalyticsService
from complex_app.analytics.tracker import EventTracker
from complex_app.auth.jwt import JWTManager
from complex_app.auth.service import AuthService
from complex_app.billing.service import BillingService
from complex_app.inventory.models import Product
from complex_app.notifications.models import NotificationPriority, NotificationType
from complex_app.notifications.service import NotificationService
from complex_app.orders.models import Cart, CartItem, Order, OrderStatus
from complex_app.shared.cache import get_cache
from complex_app.shared.database import get_database


def test_create_order_full_flow() -> None:
    db = get_database()
    db.connect()
    cache = get_cache()
    jwt_manager = JWTManager(secret="test-secret")
    auth_service = AuthService(db, cache, jwt_manager)
    notification_service = NotificationService(db, cache, auth_service)
    analytics_service = AnalyticsService(db, cache, auth_service)
    tracker = EventTracker(analytics_service)

    user = auth_service.create_user(
        username="testuser",
        email="test@example.com",
        password="password123",
    )
    assert user.id is not None
    assert user.username == "testuser"

    product = Product(
        name="Test Widget", price=29.99, description="A test product"
    )
    cart_item = CartItem(
        product_id=product.id,
        name=product.name,
        quantity=2,
        unit_price=product.price,
        total_price=59.98,
    )
    cart = Cart(
        user_id=user.id,
        items=[cart_item],
        subtotal=59.98,
        tax=4.80,
        total=64.78,
    )

    billing_service = BillingService(db, auth_service, notification_service)
    invoice = billing_service.process_payment(
        user_id=user.id,
        amount=cart.total,
        currency="USD",
        payment_method_id="pm_test_123",
    )
    assert invoice.status == "paid"

    order = Order(
        user_id=user.id,
        items=[cart_item],
        subtotal=cart.subtotal,
        tax=cart.tax,
        total=cart.total,
        status=OrderStatus.CONFIRMED,
        invoice_id=invoice.id,
        payment_id="pi_test_456",
    )
    assert order.status == OrderStatus.CONFIRMED

    notif = notification_service.send_notification(
        user_id=user.id,
        notification_type="payment_receipt",
        data={
            "invoice_id": invoice.id,
            "amount": invoice.total,
            "currency": "USD",
        },
    )
    assert notif is not None
    assert notif.status == "sent"
    assert notif.type == NotificationType.EMAIL

    event = analytics_service.track_event(
        user_id=user.id,
        event_type=EventType.ORDER_CREATED,
        data={
            "order_id": order.id,
            "total": order.total,
            "currency": "USD",
        },
    )
    assert event is not None
    assert event.event_type == EventType.ORDER_CREATED
    assert event.user_id == user.id

    login_event = analytics_service.track_event(
        user_id=user.id,
        event_type=EventType.USER_LOGIN,
        data={},
    )
    assert login_event.event_type == EventType.USER_LOGIN

    notifications = notification_service.get_user_notifications(
        user.id, unread_only=True
    )
    assert isinstance(notifications, list)

    metrics = analytics_service.get_user_metrics(user.id)
    assert metrics["login_count"] >= 1
    assert metrics["order_count"] >= 1
    assert metrics["total_spent"] >= order.total

    tracker.track_order_created(
        order_id=order.id, user_id=user.id, total=order.total
    )
    tracker.track_user_login(user_id=user.id)
    tracker.track_page_view(
        session_id="sess_001", path="/products", user_id=user.id
    )

    db.disconnect()
