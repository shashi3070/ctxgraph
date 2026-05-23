"""JWT token handling."""
import hashlib
import json
import time
from src.core.exceptions import AuthenticationError


class TokenValidator:
    def __init__(self, secret):
        self.secret = secret

    def validate(self, token):
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            payload_b64 = parts[1]
            payload = json.loads(self._b64_decode(payload_b64))
            if payload.get("exp", 0) < time.time():
                raise AuthenticationError("Token expired")
            return payload
        except (json.JSONDecodeError, IndexError):
            return None

    def generate(self, user_id, role="user"):
        header = self._b64_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
        payload = self._b64_encode(
            json.dumps(
                {
                    "sub": user_id,
                    "role": role,
                    "exp": int(time.time()) + 3600,
                    "iat": int(time.time()),
                }
            )
        )
        signature = self._sign(f"{header}.{payload}")
        return f"{header}.{payload}.{signature}"

    def _sign(self, data):
        return hashlib.sha256(f"{data}.{self.secret}".encode()).hexdigest()

    def _b64_encode(self, data):
        return data.encode("utf-8").hex()

    def _b64_decode(self, data):
        return bytes.fromhex(data).decode("utf-8")
