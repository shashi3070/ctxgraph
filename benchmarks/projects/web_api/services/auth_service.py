import hashlib
import hmac
import json
import time
import uuid
import logging
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from ..models.user import User
from ..config import settings
from . import BaseService


logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents an authenticated user session backed by a JWT."""

    token: str
    user_id: str
    created_at: float
    expires_at: float
    is_valid: bool = True


class AuthService(BaseService):
    """Handles user authentication: password hashing, JWT creation/validation,
    and session lifecycle management."""

    def __init__(self, user_service: Optional[Any] = None):
        self._user_service = user_service
        self._sessions: Dict[str, Session] = {}
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm

    async def initialize(self) -> None:
        logger.info("AuthService initialized with algorithm %s", self._algorithm)

    async def health_check(self) -> Dict[str, Any]:
        return {
            "service": "auth",
            "status": "healthy",
            "active_sessions": len(self._sessions),
        }

    def set_user_service(self, user_service: Any) -> None:
        """Inject or replace the user-service dependency."""
        self._user_service = user_service

    # ------------------------------------------------------------------
    # Base64url helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        import base64
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    # ------------------------------------------------------------------
    # JWT operations
    # ------------------------------------------------------------------
    def _sign(self, signing_input: str) -> bytes:
        return hmac.new(
            self._secret.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()

    def create_jwt(self, user_id: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
        """Create a signed JWT with standard and optional custom claims."""
        now = int(time.time())
        payload: Dict[str, Any] = {
            "sub": user_id,
            "iat": now,
            "exp": now + settings.jwt_expiration_minutes * 60,
            "jti": str(uuid.uuid4()),
        }
        if extra_claims:
            payload.update(extra_claims)

        header = {"alg": self._algorithm, "typ": "JWT"}
        header_b64 = self._base64url_encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = self._base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{header_b64}.{payload_b64}"
        signature_b64 = self._base64url_encode(self._sign(signing_input))
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def decode_jwt(self, token: str) -> Dict[str, Any]:
        """Decode and verify a JWT.  Raises ValueError on failure."""
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("JWT must have exactly 3 parts separated by dots")

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        expected_sig = self._sign(signing_input)
        actual_sig = self._base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid JWT signature")

        payload_bytes = self._base64url_decode(payload_b64)
        payload: Dict[str, Any] = json.loads(payload_bytes)

        if payload.get("exp", 0) < time.time():
            raise ValueError("JWT has expired")

        return payload

    # ------------------------------------------------------------------
    # Password hashing  (PBKDF2-HMAC-SHA256 with random salt)
    # ------------------------------------------------------------------
    def hash_password(self, password: str) -> str:
        """Hash a plaintext password with a random salt and return
        a 'salt$hash' string for storage."""
        salt = uuid.uuid4().hex
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}${dk.hex()}"

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a 'salt$hash' string."""
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
        salt, stored_hash = parts
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(computed.hex(), stored_hash)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def create_session(self, user_id: str) -> Session:
        """Create a new session for *user_id* and return it."""
        now = time.time()
        expires_at = now + settings.jwt_expiration_minutes * 60
        token = self.create_jwt(user_id)
        session = Session(
            token=token,
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
        )
        self._sessions[token] = session
        return session

    def validate_session(self, token: str) -> Optional[Session]:
        """Look up and validate a session.  Returns None if invalid/expired."""
        session = self._sessions.get(token)
        if not session or not session.is_valid:
            return None
        if time.time() > session.expires_at:
            session.is_valid = False
            return None
        return session

    def invalidate_session(self, token: str) -> bool:
        """Mark a session as invalid.  Returns True if the session existed."""
        session = self._sessions.get(token)
        if session:
            session.is_valid = False
            return True
        return False

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Convenience: delegate to the injected user service if available."""
        if self._user_service:
            return self._user_service.get_by_id(user_id)
        return None
