from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from complex_app.shared.config import get_config
from complex_app.shared.errors import ServiceUnavailableError


class PushProvider(ABC):
    @abstractmethod
    def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...


class FCMProvider(PushProvider):
    def __init__(self) -> None:
        config = get_config()
        self._server_key: str = config.api_keys.get("fcm_server_key", "")

    def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._server_key:
            raise ServiceUnavailableError(
                code="fcm_not_configured",
                message="FCM server key is not configured",
            )


class APNsProvider(PushProvider):
    def __init__(self) -> None:
        config = get_config()
        self._key_id: str = config.api_keys.get("apns_key_id", "")
        self._team_id: str = config.api_keys.get("apns_team_id", "")
        self._topic: str = config.api_keys.get("apns_topic", "")

    def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._key_id:
            raise ServiceUnavailableError(
                code="apns_not_configured",
                message="APNs is not configured",
            )
