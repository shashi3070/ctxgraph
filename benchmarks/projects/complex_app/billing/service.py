from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from complex_app.auth.service import AuthService
from complex_app.billing.models import Invoice, Plan, Subscription
from complex_app.notifications.service import NotificationService
from complex_app.shared.base import BaseService
from complex_app.shared.config import get_config
from complex_app.shared.database import get_database
from complex_app.shared.errors import NotFoundError, ValidationError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BillingService(BaseService):
    def __init__(
        self,
        db: Any,
        auth_service: AuthService,
        notification_service: NotificationService,
    ) -> None:
        self._db = db
        self._auth_service = auth_service
        self._notification_service = notification_service

    def _validate(self, user: Any = None) -> None:
        pass

    def _authorize(self, user: Any = None) -> None:
        pass

    def create_subscription(
        self, user_id: str, plan_id: str, payment_method_id: str
    ) -> Subscription:
        user = self._auth_service.get_user(user_id)
        self._validate(user)

        if not plan_id or not payment_method_id:
            raise ValidationError(
                code="missing_fields",
                message="plan_id and payment_method_id are required",
            )

        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status="active",
            current_period_start=_now(),
        )

        self._db.execute(
            "INSERT INTO subscriptions (id, user_id, plan_id, status, current_period_start, current_period_end, cancel_at_period_end, trial_end, created_at, updated_at) VALUES (:id, :user_id, :plan_id, :status, :current_period_start, :current_period_end, :cancel_at_period_end, :trial_end, :created_at, :updated_at)",
            subscription.to_dict(),
        )

        self._notification_service.send_notification(
            user_id=user_id,
            notification_type="subscription_created",
            data={"subscription_id": subscription.id, "plan_id": plan_id},
        )

        return subscription

    def cancel_subscription(
        self, user_id: str, subscription_id: str
    ) -> Subscription:
        user = self._auth_service.get_user(user_id)
        self._authorize(user)

        rows = self._db.fetch_all(
            "SELECT * FROM subscriptions WHERE id = :id",
            {"id": subscription_id},
        )
        sub_data = rows[0] if rows else None

        if not sub_data:
            raise NotFoundError(
                code="subscription_not_found",
                message="Subscription not found",
            )

        subscription = Subscription.from_dict(sub_data)
        subscription.status = "canceled"
        subscription.updated_at = _now()

        self._db.execute(
            "UPDATE subscriptions SET status = :status, updated_at = :updated_at WHERE id = :id",
            subscription.to_dict(),
        )

        self._notification_service.send_notification(
            user_id=user_id,
            notification_type="subscription_canceled",
            data={"subscription_id": subscription_id},
        )

        return subscription

    def process_payment(
        self,
        user_id: str,
        amount: float,
        currency: str,
        payment_method_id: str,
    ) -> Invoice:
        user = self._auth_service.get_user(user_id)
        self._validate(user)

        if amount <= 0:
            raise ValidationError(
                code="invalid_amount", message="Amount must be positive"
            )

        config = get_config()

        invoice = Invoice(
            user_id=user_id,
            items=[{"amount": amount, "currency": currency}],
            subtotal=amount,
            tax=amount * 0.08,
            total=amount * 1.08,
            currency=currency,
            status="paid",
            paid_at=_now(),
            payment_method_id=payment_method_id,
        )

        self._db.execute(
            "INSERT INTO invoices (id, user_id, items, subtotal, tax, total, currency, status, due_date, paid_at, payment_method_id, created_at, updated_at) VALUES (:id, :user_id, :items, :subtotal, :tax, :total, :currency, :status, :due_date, :paid_at, :payment_method_id, :created_at, :updated_at)",
            invoice.to_dict(),
        )

        self._notification_service.send_notification(
            user_id=user_id,
            notification_type="payment_receipt",
            data={
                "invoice_id": invoice.id,
                "amount": amount,
                "currency": currency,
            },
        )

        return invoice

    def get_invoice(self, invoice_id: str) -> Invoice:
        rows = self._db.fetch_all(
            "SELECT * FROM invoices WHERE id = :id", {"id": invoice_id}
        )
        invoice_data = rows[0] if rows else None

        if not invoice_data:
            raise NotFoundError(
                code="invoice_not_found", message="Invoice not found"
            )

        return Invoice.from_dict(invoice_data)

    def list_invoices(self, user_id: str) -> List[Invoice]:
        rows = self._db.fetch_all(
            "SELECT * FROM invoices WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        return [Invoice.from_dict(row) for row in rows]

    def get_subscription(self, subscription_id: str) -> Subscription:
        rows = self._db.fetch_all(
            "SELECT * FROM subscriptions WHERE id = :id",
            {"id": subscription_id},
        )
        sub_data = rows[0] if rows else None

        if not sub_data:
            raise NotFoundError(
                code="subscription_not_found",
                message="Subscription not found",
            )

        return Subscription.from_dict(sub_data)

    def get_available_plans(self) -> List[Plan]:
        config = get_config()
        return [
            Plan(
                id="plan_basic",
                name="Basic",
                description="Basic plan with core features",
                price=9.99,
                currency="USD",
                interval="month",
                features=["core_access", "email_support"],
                trial_days=14,
            ),
            Plan(
                id="plan_pro",
                name="Pro",
                description="Pro plan with advanced features",
                price=29.99,
                currency="USD",
                interval="month",
                features=[
                    "core_access",
                    "priority_support",
                    "analytics",
                    "api_access",
                ],
                trial_days=14,
            ),
            Plan(
                id="plan_enterprise",
                name="Enterprise",
                description="Enterprise plan with full features",
                price=99.99,
                currency="USD",
                interval="month",
                features=[
                    "core_access",
                    "dedicated_support",
                    "analytics",
                    "api_access",
                    "custom_integrations",
                    "sla",
                ],
                trial_days=30,
            ),
        ]
