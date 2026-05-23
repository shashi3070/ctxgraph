"""Billing service server - handles subscription and payment operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import asyncio
import uuid

from shared.events import EventBus, Event, EventType, get_event_bus
from shared.tracing import Tracer, trace, SpanKind
from shared.retry import retry, AsyncRetryPolicy, BackoffStrategy
from shared.circuit_breaker import CircuitBreaker, get_circuit_breaker
from shared.logging import get_logger
from shared.metrics import MetricsCollector, get_collector

from services.billing.payments import PaymentProcessor, PaymentResult, PaymentMethod, PaymentStatus
from services.billing.plans import PlanManager, SubscriptionPlan, BillingCycle
from services.billing.invoices import InvoiceGenerator, Invoice, InvoiceStatus
from services.billing.models import Subscription, SubscriptionStatus, Customer


class BillingCommand(str, Enum):
    CREATE_SUBSCRIPTION = "create_subscription"
    CANCEL_SUBSCRIPTION = "cancel_subscription"
    UPDATE_SUBSCRIPTION = "update_subscription"
    PROCESS_PAYMENT = "process_payment"
    ISSUE_INVOICE = "issue_invoice"
    REFUND_PAYMENT = "refund_payment"


@dataclass
class BillingResponse:
    success: bool
    subscription: Optional[Subscription] = None
    payment: Optional[PaymentResult] = None
    invoice: Optional[Invoice] = None
    subscriptions: List[Subscription] = field(default_factory=list)
    error: Optional[str] = None
    error_code: Optional[str] = None


class BillingServiceServer:
    def __init__(
        self,
        payment_processors: Dict[str, PaymentProcessor],
        plan_manager: PlanManager,
        invoice_generator: InvoiceGenerator,
        event_bus: EventBus,
        tracer: Tracer
    ):
        self.payment_processors = payment_processors
        self.plan_manager = plan_manager
        self.invoice_generator = invoice_generator
        self.event_bus = event_bus
        self.tracer = tracer
        self.logger = get_logger("BillingServiceServer", "billing-service")
        self.metrics = get_collector("billing-service")
        self.circuit_breaker = get_circuit_breaker("billing-service", failure_threshold=3)
        self._subscriptions: Dict[uuid.UUID, Subscription] = {}
        self._customers: Dict[uuid.UUID, Customer] = {}

    def get_payment_processor(self, processor_id: str) -> Optional[PaymentProcessor]:
        return self.payment_processors.get(processor_id)

    @trace("billing_create_subscription", SpanKind.SERVER)
    @retry(max_attempts=3, backoff_strategy=BackoffStrategy.EXPONENTIAL, retry_on_exceptions=(Exception,))
    async def create_subscription(
        self,
        customer_id: uuid.UUID,
        plan_id: str,
        payment_method_id: str,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        trial_days: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BillingResponse:
        self.metrics.increment_counter("subscription_attempts_total")

        plan = self.plan_manager.get_plan(plan_id)
        if not plan:
            return BillingResponse(
                success=False,
                error=f"Plan {plan_id} not found",
                error_code="PLAN_NOT_FOUND"
            )

        customer = self._customers.get(customer_id)
        if not customer:
            return BillingResponse(
                success=False,
                error=f"Customer {customer_id} not found",
                error_code="CUSTOMER_NOT_FOUND"
            )

        now = datetime.utcnow()
        trial_ends_at = now + timedelta(days=trial_days) if trial_days > 0 else None
        current_period_start = trial_ends_at or now
        current_period_end = current_period_start + timedelta(days=30 if billing_cycle == BillingCycle.MONTHLY else 365)

        subscription = Subscription(
            subscription_id=uuid.uuid4(),
            customer_id=customer_id,
            plan_id=plan_id,
            status=SubscriptionStatus.TRIALING if trial_days > 0 else SubscriptionStatus.ACTIVE,
            billing_cycle=billing_cycle,
            payment_method_id=payment_method_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_start=now if trial_days > 0 else None,
            trial_end=trial_ends_at,
            metadata=metadata or {}
        )

        self._subscriptions[subscription.subscription_id] = subscription

        if trial_days == 0:
            invoice = await self.invoice_generator.generate(
                subscription=subscription,
                customer=customer,
                plan=plan
            )

            processor = self.get_payment_processor("stripe")
            if processor:
                payment_result = await processor.charge(
                    amount=plan.price_per_cycle(billing_cycle),
                    currency="USD",
                    payment_method_id=payment_method_id,
                    description=f"Subscription: {plan.name}"
                )

                if payment_result.status == PaymentStatus.SUCCEEDED:
                    invoice.status = InvoiceStatus.PAID
                    invoice.paid_at = datetime.utcnow()
                    await self.event_bus.publish(Event(
                        event_type=EventType.PAYMENT_SUCCEEDED,
                        payload={
                            "subscription_id": str(subscription.subscription_id),
                            "customer_id": str(customer_id),
                            "amount": float(plan.price_per_cycle(billing_cycle))
                        },
                        source="billing-service"
                    ))
                else:
                    return BillingResponse(
                        success=False,
                        error=f"Payment failed: {payment_result.error_message}",
                        error_code="PAYMENT_FAILED"
                    )

        await self.event_bus.publish(Event(
            event_type=EventType.SUBSCRIPTION_STARTED,
            payload={
                "subscription_id": str(subscription.subscription_id),
                "customer_id": str(customer_id),
                "plan_id": plan_id
            },
            source="billing-service"
        ))

        self.logger.info(f"Created subscription: {subscription.subscription_id}")
        self.metrics.increment_counter("subscriptions_created_total")

        return BillingResponse(
            success=True,
            subscription=subscription
        )

    @trace("billing_cancel_subscription", SpanKind.SERVER)
    async def cancel_subscription(
        self,
        subscription_id: uuid.UUID,
        at_period_end: bool = True,
        reason: Optional[str] = None
    ) -> BillingResponse:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return BillingResponse(
                success=False,
                error=f"Subscription {subscription_id} not found",
                error_code="NOT_FOUND"
            )

        if subscription.status in (SubscriptionStatus.CANCELLED, SubscriptionStatus.PAST_DUE):
            return BillingResponse(
                success=False,
                error=f"Subscription is already {subscription.status.value}",
                error_code="INVALID_STATE"
            )

        if at_period_end:
            subscription.status = SubscriptionStatus.CANCELLED_AT_PERIOD_END
            subscription.cancel_at_period_end = True
        else:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.canceled_at = datetime.utcnow()

        subscription.cancellation_reason = reason

        await self.event_bus.publish(Event(
            event_type=EventType.SUBSCRIPTION_CANCELLED,
            payload={
                "subscription_id": str(subscription_id),
                "at_period_end": at_period_end,
                "reason": reason
            },
            source="billing-service"
        ))

        self.logger.info(f"Cancelled subscription: {subscription_id}")
        self.metrics.increment_counter("subscriptions_cancelled_total")

        return BillingResponse(
            success=True,
            subscription=subscription
        )

    @trace("billing_get_subscription", SpanKind.SERVER)
    async def get_subscription(self, subscription_id: uuid.UUID) -> BillingResponse:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return BillingResponse(
                success=False,
                error="Subscription not found",
                error_code="NOT_FOUND"
            )
        return BillingResponse(success=True, subscription=subscription)

    @trace("billing_list_customer_subscriptions", SpanKind.SERVER)
    async def list_customer_subscriptions(self, customer_id: uuid.UUID) -> BillingResponse:
        subscriptions = [
            s for s in self._subscriptions.values()
            if s.customer_id == customer_id
        ]
        return BillingResponse(success=True, subscriptions=subscriptions)


def create_billing_server() -> BillingServiceServer:
    event_bus = get_event_bus()
    tracer = Tracer("billing-service")

    from services.billing.payments import StripeProcessor, PayPalProcessor

    payment_processors = {
        "stripe": StripeProcessor("sk_test_fake_key"),
        "paypal": PayPalProcessor("client_id", "client_secret")
    }

    plan_manager = PlanManager()
    invoice_generator = InvoiceGenerator()

    return BillingServiceServer(
        payment_processors=payment_processors,
        plan_manager=plan_manager,
        invoice_generator=invoice_generator,
        event_bus=event_bus,
        tracer=tracer
    )
