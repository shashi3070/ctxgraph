import logging
from typing import Any, Dict, List
from . import BaseRouter
from ..services.auth_service import AuthService
from ..services.user_service import UserService


logger = logging.getLogger(__name__)


class AuthRouter(BaseRouter):
    """Route handlers for public authentication endpoints (register, login, refresh)."""

    def __init__(self, auth_service: AuthService, user_service: UserService):
        super().__init__(prefix="/auth")
        self._auth_service = auth_service
        self._user_service = user_service

    async def handle_register(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user account."""
        body = request.get("body", {})
        username = body.get("username", "")
        email = body.get("email", "")
        password = body.get("password", "")

        if not username or not email or not password:
            return {"status_code": 400, "body": {"error": "username, email, and password are required"}}

        if len(password) < 8:
            return {"status_code": 400, "body": {"error": "Password must be at least 8 characters"}}

        existing = self._user_service.get_by_email(email)
        if existing:
            return {"status_code": 409, "body": {"error": "Email already registered"}}

        existing_username = self._user_service.get_by_username(username)
        if existing_username:
            return {"status_code": 409, "body": {"error": "Username already taken"}}

        try:
            hashed = self._auth_service.hash_password(password)
            user = self._user_service.create(
                username=username, email=email, hashed_password=hashed
            )
            token = self._auth_service.create_jwt(user.id, {"role": user.role})
            return {
                "status_code": 201,
                "body": {
                    "user": user.to_dict(),
                    "token": token,
                    "message": "User registered successfully",
                },
            }
        except ValueError as exc:
            return {"status_code": 400, "body": {"error": str(exc)}}

    async def handle_login(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate with email/password and receive a JWT."""
        body = request.get("body", {})
        email = body.get("email", "")
        password = body.get("password", "")

        if not email or not password:
            return {"status_code": 400, "body": {"error": "email and password are required"}}

        user = self._user_service.get_by_email(email)
        if not user:
            return {"status_code": 401, "body": {"error": "Invalid email or password"}}

        if not self._auth_service.verify_password(password, user.hashed_password):
            return {"status_code": 401, "body": {"error": "Invalid email or password"}}

        if not user.is_active:
            return {"status_code": 403, "body": {"error": "Account is deactivated"}}

        session = self._auth_service.create_session(user.id)
        return {
            "status_code": 200,
            "body": {
                "token": session.token,
                "user": user.to_dict(),
                "expires_at": session.expires_at,
            },
        }

    async def handle_refresh(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Issue a new JWT in exchange for a valid, non-expired one."""
        auth_header = request.get("headers", {}).get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {"status_code": 401, "body": {"error": "Missing or invalid token"}}

        token = auth_header[7:]
        session = self._auth_service.validate_session(token)
        if not session:
            return {"status_code": 401, "body": {"error": "Session expired or invalid"}}

        self._auth_service.invalidate_session(token)
        new_session = self._auth_service.create_session(session.user_id)
        return {
            "status_code": 200,
            "body": {
                "token": new_session.token,
                "expires_at": new_session.expires_at,
                "message": "Token refreshed successfully",
            },
        }

    def register_routes(self) -> List[Dict[str, Any]]:
        return [
            {
                "method": "POST",
                "path": f"{self.prefix}/register",
                "handler": self.handle_register,
                "auth_required": False,
            },
            {
                "method": "POST",
                "path": f"{self.prefix}/login",
                "handler": self.handle_login,
                "auth_required": False,
            },
            {
                "method": "POST",
                "path": f"{self.prefix}/refresh",
                "handler": self.handle_refresh,
                "auth_required": True,
            },
        ]
