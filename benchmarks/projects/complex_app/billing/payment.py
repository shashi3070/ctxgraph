from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from complex_app.billing.models import Invoice, PaymentMethod
from complex_app.shared.errors import ServiceUnavailableError


class PaymentGateway(ABC):
    @abstractmethod
    def charge(
        self,
        amount: float,
        currency: str,
        payment_method: PaymentMethod,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    def refund(
        self,
        transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


class StripeGateway(PaymentGateway):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def charge(
        self,
        amount: float,
        currency: str,
        payment_method: PaymentMethod,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "gateway": "stripe",
            "transaction_id": f"ch_{payment_method.id}",
            "amount": amount,
            "currency": currency,
            "status": "succeeded",
        }

    def refund(
        self,
        transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "gateway": "stripe",
            "transaction_id": transaction_id,
            "amount": amount,
            "status": "refunded",
        }


class PayPalGateway(PaymentGateway):
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: Optional[str] = None

    def _authenticate(self) -> str:
        self._access_token = f"paypal_token_{self._client_id}"
        return self._access_token

    def charge(
        self,
        amount: float,
        currency: str,
        payment_method: PaymentMethod,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        token = self._authenticate()
        return {
            "gateway": "paypal",
            "transaction_id": f"pay_{payment_method.id}",
            "amount": amount,
            "currency": currency,
            "status": "succeeded",
            "access_token": token,
        }

    def refund(
        self,
        transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "gateway": "paypal",
            "transaction_id": transaction_id,
            "amount": amount,
            "reason": reason,
            "status": "refunded",
        }


@dataclass
class PaymentRouter:
    gateways: Dict[str, PaymentGateway]

    def route_payment(
        self,
        method: PaymentMethod,
        amount: float,
        currency: str,
    ) -> Invoice:
        gateway = self.gateways.get(method.type)
        if gateway is None:
            raise ServiceUnavailableError(
                code="unsupported_payment_method",
                message=f"No gateway configured for payment type: {method.type}",
            )

        result = gateway.charge(amount, currency, method)

        return Invoice(
            user_id=method.user_id,
            items=[{"amount": amount, "currency": currency}],
            subtotal=amount,
            tax=amount * 0.08,
            total=amount * 1.08,
            currency=currency,
            status="paid",
            payment_method_id=method.id,
        )

    def process_refund(
        self,
        invoice: Invoice,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not invoice.payment_method_id:
            raise ServiceUnavailableError(
                code="no_payment_method",
                message="Invoice has no associated payment method",
            )
        return {}
