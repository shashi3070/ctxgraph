from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from complex_app.shared.config import get_config
from complex_app.shared.errors import ServiceUnavailableError


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        ...


class SMTPEmailProvider(EmailProvider):
    def __init__(self) -> None:
        config = get_config()
        self._host: str = config.api_keys.get("smtp_host", "")
        self._port: int = int(config.api_keys.get("smtp_port", "587"))
        self._username: str = config.api_keys.get("smtp_user", "")
        self._password: str = config.api_keys.get("smtp_pass", "")

    def send(self, to: str, subject: str, body: str) -> None:
        if not self._host:
            raise ServiceUnavailableError(
                code="smtp_not_configured",
                message="SMTP server is not configured",
            )


class SendGridProvider(EmailProvider):
    def __init__(self) -> None:
        config = get_config()
        self._api_key: str = config.api_keys.get("sendgrid_api_key", "")

    def send(self, to: str, subject: str, body: str) -> None:
        if not self._api_key:
            raise ServiceUnavailableError(
                code="sendgrid_not_configured",
                message="SendGrid API key is not configured",
            )


class MockEmailProvider(EmailProvider):
    def __init__(self) -> None:
        self.sent_emails: List[Dict[str, Any]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent_emails.append({"to": to, "subject": subject, "body": body})
