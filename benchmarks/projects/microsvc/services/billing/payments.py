"""Payment processing providers: Stripe, PayPal, etc."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import asyncio
import uuid

from shared.logging import get_logger
from shared.metrics import get_collector


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethodType(str, Enum):
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    ALIPAY = "alipay"
    WECHAT = "wechat"


class CardBrand(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    DINERS = "diners"
    JCB = "jcb"
    UNIONPAY = "unionpay"


@dataclass
class CardDetails:
    last4: str
    exp_month: int
    exp_year: int
    brand: CardBrand
    funding: str = "credit"
    country: Optional[str] = None


@dataclass
class PaymentMethod:
    method_id: str
    customer_id: str
    type: PaymentMethodType
    card: Optional[CardDetails] = None
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PaymentResult:
    payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    processor: str
    transaction_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RefundResult:
    refund_id: str
    payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    transaction_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class PaymentProcessor(ABC):
    @abstractmethod
    async def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        pass

    @abstractmethod
    async def refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        pass

    @abstractmethod
    async def get_payment(self, payment_id: str) -> Optional[PaymentResult]:
        pass

    @abstractmethod
    async def create_payment_method(
        self,
        customer_id: str,
        payment_details: Dict[str, Any]
    ) -> PaymentMethod:
        pass

    @abstractmethod
    async def delete_payment_method(self, method_id: str) -> bool:
        pass

    @abstractmethod
    def processor_name(self) -> str:
        pass


class StripeProcessor(PaymentProcessor):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = get_logger("StripeProcessor", "billing-service")
        self.metrics = get_collector("billing-service")
        self._payments: Dict[str, PaymentResult] = {}
        self._payment_methods: Dict[str, PaymentMethod] = {}

    def processor_name(self) -> str:
        return "stripe"

    async def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        self.logger.info(f"Stripe charge: {amount} {currency}, method: {payment_method_id}")
        self.metrics.increment_counter("payment_attempts_total")

        payment_id = f"pi_{uuid.uuid4().hex[:24]}"
        transaction_id = f"txn_{uuid.uuid4().hex[:16]}"

        success = True
        error_code = None
        error_message = None

        if payment_method_id == "failed-card":
            success = False
            error_code = "card_declined"
            error_message = "Your card was declined."

        result = PaymentResult(
            payment_id=payment_id,
            status=PaymentStatus.SUCCEEDED if success else PaymentStatus.FAILED,
            amount=amount,
            currency=currency,
            processor="stripe",
            transaction_id=transaction_id if success else None,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {}
        )

        self._payments[payment_id] = result

        if success:
            self.metrics.increment_counter("payment_successes_total")
        else:
            self.metrics.increment_counter("payment_failures_total")

        return result

    async def refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        self.logger.info(f"Stripe refund: payment={payment_id}, amount={amount}")

        payment = self._payments.get(payment_id)
        if not payment:
            return RefundResult(
                refund_id=f"re_{uuid.uuid4().hex[:24]}",
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=amount or Decimal("0"),
                currency="USD"
            )

        refund_amount = amount or payment.amount
        refund_id = f"re_{uuid.uuid4().hex[:24]}"

        return RefundResult(
            refund_id=refund_id,
            payment_id=payment_id,
            status=PaymentStatus.REFUNDED,
            amount=refund_amount,
            currency=payment.currency,
            transaction_id=f"txn_{uuid.uuid4().hex[:16]}"
        )

    async def get_payment(self, payment_id: str) -> Optional[PaymentResult]:
        return self._payments.get(payment_id)

    async def create_payment_method(
        self,
        customer_id: str,
        payment_details: Dict[str, Any]
    ) -> PaymentMethod:
        method_id = f"pm_{uuid.uuid4().hex[:24]}"

        card_type = payment_details.get("card_type", "visa")
        try:
            brand = CardBrand(card_type)
        except ValueError:
            brand = CardBrand.VISA

        card = CardDetails(
            last4=payment_details.get("last4", "4242"),
            exp_month=payment_details.get("exp_month", 12),
            exp_year=payment_details.get("exp_year", 2028),
            brand=brand
        )

        method = PaymentMethod(
            method_id=method_id,
            customer_id=customer_id,
            type=PaymentMethodType.CARD,
            card=card,
            is_default=payment_details.get("is_default", False)
        )

        self._payment_methods[method_id] = method
        return method

    async def delete_payment_method(self, method_id: str) -> bool:
        if method_id in self._payment_methods:
            del self._payment_methods[method_id]
            return True
        return False


class PayPalProcessor(PaymentProcessor):
    def __init__(self, client_id: str, client_secret: str, mode: str = "sandbox"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.mode = mode
        self.logger = get_logger("PayPalProcessor", "billing-service")
        self.metrics = get_collector("billing-service")
        self._payments: Dict[str, PaymentResult] = {}
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    def processor_name(self) -> str:
        return "paypal"

    async def _get_access_token(self) -> str:
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        self._access_token = f"paypal_token_{uuid.uuid4().hex[:32]}"
        self._token_expires_at = datetime.utcnow() + timedelta(hours=8)
        return self._access_token

    async def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        self.logger.info(f"PayPal charge: {amount} {currency}")
        await self._get_access_token()
        self.metrics.increment_counter("payment_attempts_total")

        payment_id = f"paypal_{uuid.uuid4().hex[:16]}"

        result = PaymentResult(
            payment_id=payment_id,
            status=PaymentStatus.SUCCEEDED,
            amount=amount,
            currency=currency,
            processor="paypal",
            transaction_id=f"PAYID-{uuid.uuid4().hex[:16].upper()}",
            metadata=metadata or {}
        )

        self._payments[payment_id] = result
        self.metrics.increment_counter("payment_successes_total")

        return result

    async def refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        self.logger.info(f"PayPal refund: {payment_id}")

        payment = self._payments.get(payment_id)
        if not payment:
            return RefundResult(
                refund_id=f"refund_{uuid.uuid4().hex[:16]}",
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=amount or Decimal("0"),
                currency="USD"
            )

        return RefundResult(
            refund_id=f"refund_{uuid.uuid4().hex[:16]}",
            payment_id=payment_id,
            status=PaymentStatus.REFUNDED,
            amount=amount or payment.amount,
            currency=payment.currency
        )

    async def get_payment(self, payment_id: str) -> Optional[PaymentResult]:
        return self._payments.get(payment_id)

    async def create_payment_method(
        self,
        customer_id: str,
        payment_details: Dict[str, Any]
    ) -> PaymentMethod:
        method_id = f"ba_{uuid.uuid4().hex[:24]}"
        return PaymentMethod(
            method_id=method_id,
            customer_id=customer_id,
            type=PaymentMethodType.PAYPAL
        )

    async def delete_payment_method(self, method_id: str) -> bool:
        return True
