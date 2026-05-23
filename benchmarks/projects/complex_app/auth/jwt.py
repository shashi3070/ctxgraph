from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any, Dict

from complex_app.auth.models import TokenPayload, TokenType
from complex_app.shared.config import get_config
from complex_app.shared.errors import AuthenticationError, TokenExpiredError


class JWTManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256") -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm

    def _base64url_encode(self, data: bytes) -> str:
        return urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    def _base64url_decode(self, data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return urlsafe_b64decode(data)

    def _sign(self, header_b64: str, payload_b64: str) -> str:
        message = f"{header_b64}.{payload_b64}".encode("utf-8")
        signer = hmac.new(
            self._secret_key.encode("utf-8"), message, hashlib.sha256
        )
        return self._base64url_encode(signer.digest())

    def create_token(self, payload: Dict[str, Any]) -> str:
        header = {"alg": self._algorithm, "typ": "JWT"}
        payload_with_time = {
            **payload,
            "iat": payload.get("iat", time.time()),
            "exp": payload.get(
                "exp", time.time() + 3600
            ),
        }
        header_b64 = self._base64url_encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_b64 = self._base64url_encode(
            json.dumps(payload_with_time, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        signature = self._sign(header_b64, payload_b64)
        return f"{header_b64}.{payload_b64}.{signature}"

    def verify_token(self, token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError(
                code="invalid_token", message="Token has invalid structure"
            )

        header_b64, payload_b64, signature_b64 = parts
        expected_sig = self._sign(header_b64, payload_b64)

        if not hmac.compare_digest(signature_b64, expected_sig):
            raise AuthenticationError(
                code="invalid_signature",
                message="Token signature is invalid",
            )

        payload_data = self._base64url_decode(payload_b64)
        payload: Dict[str, Any] = json.loads(payload_data)

        exp = payload.get("exp")
        if exp is not None and time.time() > exp:
            raise TokenExpiredError(
                code="token_expired", message="Token has expired"
            )

        return payload

    def decode_token(self, token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError(
                code="invalid_token", message="Token has invalid structure"
            )

        _, payload_b64, _ = parts
        payload_data = self._base64url_decode(payload_b64)
        return json.loads(payload_data)


def create_jwt_manager() -> JWTManager:
    config = get_config()
    return JWTManager(secret_key=config.secret_key)
