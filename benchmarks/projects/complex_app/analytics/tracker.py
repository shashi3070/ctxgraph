from __future__ import annotations

from typing import Any, Dict, Optional

from complex_app.analytics.models import AnalyticsEvent, EventType
from complex_app.analytics.service import AnalyticsService


class EventTracker:
    def __init__(self, analytics_service: AnalyticsService) -> None:
        self._analytics_service = analytics_service

    def track(
        self,
        event_type: EventType,
        user_id: Optional[str],
        data: Dict[str, Any],
    ) -> None:
        self._analytics_service.track_event(
            user_id=user_id, event_type=event_type, data=data
        )

    def track_order_created(
        self, order_id: str, user_id: str, total: float
    ) -> None:
        self.track(
            event_type=EventType.ORDER_CREATED,
            user_id=user_id,
            data={"order_id": order_id, "total": total},
        )

    def track_user_login(self, user_id: str) -> None:
        self.track(
            event_type=EventType.USER_LOGIN,
            user_id=user_id,
            data={},
        )

    def track_page_view(
        self, session_id: str, path: str, user_id: Optional[str]
    ) -> None:
        self.track(
            event_type=EventType.PAGE_VIEW,
            user_id=user_id,
            data={"session_id": session_id, "path": path},
        )
