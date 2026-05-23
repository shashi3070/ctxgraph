import time
import logging
from typing import Any, Dict, Optional
from . import BaseMiddleware


logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware that validates JWT tokens from the Authorization header.

    Extracts the Bearer token, delegates decoding to the auth service, and
    attaches the authenticated user to request['user']. Public endpoints
    listed in exclude_paths bypass authentication.
    """

    def __init__(
        self,
        auth_service: Any,
        options: Optional[Dict[str, Any]] = None,
        exclude_paths: Optional[list] = None,
    ):
        super().__init__(options)
        self._auth_service = auth_service
        self._exclude_paths = exclude_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/docs",
            "/openapi.json",
        ]

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        path = request.get("path", "")
        if any(path.startswith(ex) for ex in self._exclude_paths):
            request["user"] = None
            return request

        auth_header = request.get("headers", {}).get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise PermissionError("Missing or malformed Authorization header")

        token = auth_header[7:]
        try:
            payload = self._auth_service.decode_jwt(token)
            user = self._auth_service.get_user_by_id(payload.get("sub"))
            if not user or not user.is_active:
                raise PermissionError("User not found or inactive")
            request["user"] = user
            request["token_payload"] = payload
        except Exception as exc:
            method = request.get("method", "GET")
            logger.warning("Auth failed for %s %s: %s", method, path, str(exc))
            raise PermissionError(f"Authentication failed: {exc}") from exc

        return request

    async def process_response(
        self, request: Dict[str, Any], response: Dict[str, Any]
    ) -> Dict[str, Any]:
        if request.get("user"):
            response.setdefault("headers", {})["X-User-ID"] = request["user"].id
        return response
