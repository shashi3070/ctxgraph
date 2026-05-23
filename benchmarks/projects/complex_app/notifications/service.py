from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from complex_app.notifications.email import EmailProvider, MockEmailProvider
from complex_app.notifications.models import (
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationTemplate,
    NotificationType,
)
from complex_app.notifications.push import PushProvider
from complex_app.shared.base import BaseService
from complex_app.shared.database import get_database
from complex_app.shared.errors import NotFoundError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotificationService(BaseService):
    def __init__(self, db, cache, auth_service) -> None:
        self._db = db
        self._cache = cache
        self._auth_service = auth_service
        self._email_provider: EmailProvider = MockEmailProvider()
        self._push_provider: Optional[PushProvider] = None
        self._templates: Dict[str, NotificationTemplate] = {
            "welcome": NotificationTemplate(
                name="welcome",
                subject="Welcome!",
                body_template="Hello {{name}}, welcome to our platform!",
                type=NotificationType.EMAIL,
                variables=["name"],
            ),
            "subscription_created": NotificationTemplate(
                name="subscription_created",
                subject="Subscription Created",
                body_template="Your subscription {{plan_id}} has been created.",
                type=NotificationType.EMAIL,
                variables=["subscription_id", "plan_id"],
            ),
            "subscription_canceled": NotificationTemplate(
                name="subscription_canceled",
                subject="Subscription Canceled",
                body_template="Your subscription has been canceled.",
                type=NotificationType.EMAIL,
                variables=["subscription_id"],
            ),
            "payment_receipt": NotificationTemplate(
                name="payment_receipt",
                subject="Payment Receipt",
                body_template="Payment of {{amount}} {{currency}} received.",
                type=NotificationType.EMAIL,
                variables=["invoice_id", "amount", "currency"],
            ),
        }

    def _validate(self, user: Optional[Any] = None) -> None:
        pass

    def _authorize(self, user: Optional[Any] = None) -> None:
        pass

    def _resolve_template(
        self, template: str, data: Dict[str, Any]
    ) -> str:
        result = template
        for key, value in data.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result

    def send_notification(
        self,
        user_id: str,
        notification_type: str,
        data: Dict[str, Any],
    ) -> Notification:
        user = self._auth_service.get_user(user_id)
        self._validate(user)

        template = self._templates.get(notification_type)
        if template is None:
            raise NotFoundError(
                code="template_not_found",
                message=f"Notification template '{notification_type}' not found",
            )

        pref = self.get_preference(user_id, template.type)
        if not pref.enabled:
            notification = Notification(
                user_id=user_id,
                type=template.type,
                title=template.subject,
                body=self._resolve_template(template.body_template, data),
                data=data,
                priority=NotificationPriority.LOW,
                status="skipped",
            )
            self._db.execute(
                "INSERT INTO notifications (id, user_id, type, title, body, data, priority, read_at, sent_at, status, created_at, updated_at) VALUES (:id, :user_id, :type, :title, :body, :data, :priority, :read_at, :sent_at, :status, :created_at, :updated_at)",
                notification.to_dict(),
            )
            return notification

        notification = Notification(
            user_id=user_id,
            type=template.type,
            title=template.subject,
            body=self._resolve_template(template.body_template, data),
            data=data,
            priority=NotificationPriority.MEDIUM,
            sent_at=_now(),
            status="sent",
        )

        if template.type == NotificationType.EMAIL:
            self._email_provider.send(
                notification.user_id,
                notification.title,
                notification.body,
            )
        elif (
            template.type == NotificationType.PUSH
            and self._push_provider is not None
        ):
            self._push_provider.send_push(
                notification.user_id,
                notification.title,
                notification.body,
            )

        self._db.execute(
            "INSERT INTO notifications (id, user_id, type, title, body, data, priority, read_at, sent_at, status, created_at, updated_at) VALUES (:id, :user_id, :type, :title, :body, :data, :priority, :read_at, :sent_at, :status, :created_at, :updated_at)",
            notification.to_dict(),
        )
        self._cache.set(f"notification:{notification.id}", notification.to_dict())
        return notification

    def send_bulk_notification(
        self,
        user_ids: List[str],
        notification_type: str,
        data: Dict[str, Any],
    ) -> List[Notification]:
        return [
            self.send_notification(
                user_id=uid, notification_type=notification_type, data=data
            )
            for uid in user_ids
        ]

    def get_user_notifications(
        self, user_id: str, unread_only: bool = False
    ) -> List[Notification]:
        if unread_only:
            rows = self._db.fetch_all(
                "SELECT * FROM notifications WHERE user_id = :user_id AND read_at IS NULL ORDER BY created_at DESC",
                {"user_id": user_id},
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM notifications WHERE user_id = :user_id ORDER BY created_at DESC",
                {"user_id": user_id},
            )
        return [Notification.from_dict(row) for row in rows]

    def mark_as_read(self, notification_id: str) -> None:
        rows = self._db.fetch_all(
            "SELECT * FROM notifications WHERE id = :id",
            {"id": notification_id},
        )
        if not rows:
            raise NotFoundError(
                code="notification_not_found",
                message="Notification not found",
            )
        self._db.execute(
            "UPDATE notifications SET read_at = :read_at, updated_at = :updated_at WHERE id = :id",
            {
                "read_at": _now(),
                "updated_at": _now(),
                "id": notification_id,
            },
        )

    def update_preference(
        self, user_id: str, pref: NotificationPreference
    ) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO notification_preferences (user_id, type, enabled, digest_frequency, created_at, updated_at) VALUES (:user_id, :type, :enabled, :digest_frequency, :created_at, :updated_at)",
            {
                "user_id": user_id,
                "type": pref.type.value,
                "enabled": pref.enabled,
                "digest_frequency": pref.digest_frequency,
                "created_at": _now(),
                "updated_at": _now(),
            },
        )

    def get_preference(
        self, user_id: str, notif_type: NotificationType
    ) -> NotificationPreference:
        rows = self._db.fetch_all(
            "SELECT * FROM notification_preferences WHERE user_id = :user_id AND type = :type",
            {"user_id": user_id, "type": notif_type.value},
        )
        if rows:
            row = rows[0]
            return NotificationPreference(
                user_id=row["user_id"],
                type=NotificationType(row["type"]),
                enabled=row["enabled"],
                digest_frequency=row.get("digest_frequency", "instant"),
            )
        return NotificationPreference(
            user_id=user_id,
            type=notif_type,
            enabled=True,
            digest_frequency="instant",
        )

    def set_email_provider(self, provider: EmailProvider) -> None:
        self._email_provider = provider

    def set_push_provider(self, provider: PushProvider) -> None:
        self._push_provider = provider
