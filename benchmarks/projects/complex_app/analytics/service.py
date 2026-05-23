from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from complex_app.analytics.models import (
    AnalyticsEvent,
    Dashboard,
    EventType,
    MetricDefinition,
    MetricType,
    Report,
)
from complex_app.shared.base import BaseService
from complex_app.shared.cache import get_cache
from complex_app.shared.database import get_database
from complex_app.shared.errors import NotFoundError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalyticsService(BaseService):
    def __init__(self, db, cache, auth_service) -> None:
        self._db = db
        self._cache = cache
        self._auth_service = auth_service

    def _validate(self, user: Optional[Any] = None) -> None:
        pass

    def _authorize(self, user: Optional[Any] = None) -> None:
        pass

    def track_event(
        self,
        user_id: Optional[str],
        event_type: EventType,
        data: Dict[str, Any],
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=data.get("session_id", ""),
            data=data,
            timestamp=_now(),
            ip_address=data.get("ip_address", ""),
            user_agent=data.get("user_agent", ""),
        )
        self._db.execute(
            "INSERT INTO analytics_events (id, event_type, user_id, session_id, data, timestamp, ip_address, user_agent, created_at, updated_at) VALUES (:id, :event_type, :user_id, :session_id, :data, :timestamp, :ip_address, :user_agent, :created_at, :updated_at)",
            event.to_dict(),
        )
        self._cache.set(f"event:{event.id}", event.to_dict())
        return event

    def get_user_events(
        self,
        user_id: str,
        event_type: Optional[EventType] = None,
        limit: int = 50,
    ) -> List[AnalyticsEvent]:
        if event_type is not None:
            rows = self._db.fetch_all(
                "SELECT * FROM analytics_events WHERE user_id = :user_id AND event_type = :event_type ORDER BY timestamp DESC LIMIT :limit",
                {
                    "user_id": user_id,
                    "event_type": event_type.value,
                    "limit": limit,
                },
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM analytics_events WHERE user_id = :user_id ORDER BY timestamp DESC LIMIT :limit",
                {"user_id": user_id, "limit": limit},
            )
        return [AnalyticsEvent.from_dict(row) for row in rows]

    def get_event_counts(
        self, event_type: EventType, since: str, until: str
    ) -> int:
        rows = self._db.fetch_all(
            "SELECT COUNT(*) as count FROM analytics_events WHERE event_type = :event_type AND timestamp >= :since AND timestamp <= :until",
            {
                "event_type": event_type.value,
                "since": since,
                "until": until,
            },
        )
        return rows[0].get("count", 0) if rows else 0

    def generate_report(
        self, name: str, metrics: List[str], date_range: tuple
    ) -> Report:
        since, until = date_range
        data: Dict[str, Any] = {}
        for metric in metrics:
            try:
                et = EventType(metric.upper())
                data[metric] = self.get_event_counts(et, since, until)
            except ValueError:
                data[metric] = 0
        return Report(
            name=name,
            metrics=metrics,
            date_range=date_range,
            data=data,
            generated_at=_now(),
        )

    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        user = self._auth_service.get_user(user_id)
        events = self.get_user_events(user_id, limit=1000)

        login_count = sum(
            1 for e in events if e.event_type == EventType.USER_LOGIN
        )
        order_count = sum(
            1 for e in events if e.event_type == EventType.ORDER_CREATED
        )
        page_views = sum(
            1 for e in events if e.event_type == EventType.PAGE_VIEW
        )
        total_spent = 0.0
        for e in events:
            if e.event_type == EventType.ORDER_CREATED and "total" in e.data:
                total_spent += float(e.data.get("total", 0))

        return {
            "user_id": user_id,
            "username": user.username,
            "login_count": login_count,
            "order_count": order_count,
            "page_views": page_views,
            "total_spent": total_spent,
        }

    def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        rows = self._db.fetch_all(
            "SELECT * FROM dashboards WHERE id = :id",
            {"id": dashboard_id},
        )
        if not rows:
            raise NotFoundError(
                code="dashboard_not_found",
                message="Dashboard not found",
            )
        dashboard = Dashboard.from_dict(rows[0])
        widgets_data: List[Dict[str, Any]] = []
        for widget in dashboard.widgets:
            et_name = widget.get("event_type", "")
            try:
                et = EventType(et_name.upper().replace(" ", "_"))
                count = self.get_event_counts(
                    et,
                    "1970-01-01T00:00:00",
                    _now(),
                )
                widgets_data.append(
                    {
                        "name": widget.get("name", ""),
                        "value": count,
                        "type": "count",
                    }
                )
            except ValueError:
                widgets_data.append(
                    {
                        "name": widget.get("name", ""),
                        "value": 0,
                        "type": "error",
                    }
                )
        return {
            "dashboard": dashboard,
            "widgets": widgets_data,
        }
