"""JWT (JSON Web Token) creation and validation utilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import hashlib
import hmac
import json
import base64


class Algorithm(str, Enum):
    HS256 = "HS256"
    HS384 = "HS384"
    HS512 = "HS512"
    RS256 = "RS256"
    RS384 = "RS384"
    RS512 = "RS512"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    ID = "id"


@dataclass
class TokenClaims:
    sub: str
    iss: str
    aud: str
    exp: int
    iat: int
    nbf: Optional[int] = None
    jti: Optional[str] = None
    scope: Optional[str] = None
    roles: Optional[List[str]] = None
    email: Optional[str] = None
    name: Optional[str] = None
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "sub": self.sub,
            "iss": self.iss,
            "aud": self.aud,
            "exp": self.exp,
            "iat": self.iat
        }
        if self.nbf is not None:
            result["nbf"] = self.nbf
        if self.jti:
            result["jti"] = self.jti
        if self.scope:
            result["scope"] = self.scope
        if self.roles:
            result["roles"] = self.roles
        if self.email:
            result["email"] = self.email
        if self.name:
            result["name"] = self.name
        if self.custom:
            result.update(self.custom)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenClaims":
        custom = {k: v for k, v in data.items() if k not in cls.__dataclass_fields__}
        return cls(
            sub=data.get("sub", ""),
            iss=data.get("iss", ""),
            aud=data.get("aud", ""),
            exp=data.get("exp", 0),
            iat=data.get("iat", 0),
            nbf=data.get("nbf"),
            jti=data.get("jti"),
            scope=data.get("scope"),
            roles=data.get("roles"),
            email=data.get("email"),
            name=data.get("name"),
            custom=custom
        )


class JWTError(Exception):
    pass


class TokenExpiredError(JWTError):
    pass


class InvalidSignatureError(JWTError):
    pass


class InvalidClaimError(JWTError):
    pass


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


class JWTEncoder:
    def __init__(self, secret_key: str, algorithm: Algorithm = Algorithm.HS256):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def _sign(self, msg: bytes, key: bytes) -> bytes:
        if self.algorithm == Algorithm.HS256:
            return hmac.new(key, msg, hashlib.sha256).digest()
        elif self.algorithm == Algorithm.HS384:
            return hmac.new(key, msg, hashlib.sha384).digest()
        elif self.algorithm == Algorithm.HS512:
            return hmac.new(key, msg, hashlib.sha512).digest()
        raise ValueError(f"Unsupported algorithm: {self.algorithm}")

    def encode(self, claims: TokenClaims) -> str:
        header = {
            "alg": self.algorithm.value,
            "typ": "JWT"
        }

        header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
        claims_json = json.dumps(claims.to_dict(), separators=(",", ":")).encode("utf-8")

        header_b64 = base64url_encode(header_json)
        claims_b64 = base64url_encode(claims_json)

        signing_input = f"{header_b64}.{claims_b64}".encode("utf-8")
        signature = self._sign(signing_input, self.secret_key.encode("utf-8"))
        signature_b64 = base64url_encode(signature)

        return f"{header_b64}.{claims_b64}.{signature_b64}"


class JWTDecoder:
    def __init__(self, secret_key: str, algorithm: Algorithm = Algorithm.HS256):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def _verify_signature(self, header_b64: str, claims_b64: str, signature_b64: str) -> bool:
        encoder = JWTEncoder(self.secret_key, self.algorithm)
        signing_input = f"{header_b64}.{claims_b64}".encode("utf-8")
        expected_signature = encoder._sign(signing_input, self.secret_key.encode("utf-8"))
        expected_b64 = base64url_encode(expected_signature)
        return hmac.compare_digest(signature_b64, expected_b64)

    def decode(self, token: str, verify: bool = True) -> TokenClaims:
        parts = token.split(".")
        if len(parts) != 3:
            raise JWTError("Invalid JWT format: expected 3 parts")

        header_b64, claims_b64, signature_b64 = parts

        if verify:
            if not self._verify_signature(header_b64, claims_b64, signature_b64):
                raise InvalidSignatureError("Invalid token signature")

        try:
            claims_json = base64url_decode(claims_b64)
            claims_dict = json.loads(claims_json)
            return TokenClaims.from_dict(claims_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise JWTError(f"Failed to decode claims: {e}")


class TokenValidator:
    def __init__(
        self,
        secret_key: str = "test-secret-key-change-me-in-production",
        allowed_issuers: Optional[List[str]] = None,
        allowed_audiences: Optional[List[str]] = None,
        clock_skew_seconds: int = 0
    ):
        self.secret_key = secret_key
        self.allowed_issuers = allowed_issuers or ["auth-service"]
        self.allowed_audiences = allowed_audiences or ["gateway"]
        self.clock_skew_seconds = clock_skew_seconds
        self.decoder = JWTDecoder(secret_key)

    def validate(self, token: str) -> TokenClaims:
        try:
            claims = self.decoder.decode(token, verify=True)
        except InvalidSignatureError:
            raise
        except JWTError as e:
            raise InvalidClaimError(f"Token decode failed: {e}")

        now = int(datetime.utcnow().timestamp())

        if claims.exp <= now - self.clock_skew_seconds:
            raise TokenExpiredError(f"Token expired at {datetime.fromtimestamp(claims.exp)}")

        if claims.nbf and claims.nbf > now + self.clock_skew_seconds:
            raise InvalidClaimError(f"Token not yet valid (nbf: {claims.nbf})")

        if claims.iss not in self.allowed_issuers:
            raise InvalidClaimError(f"Invalid issuer: {claims.iss}")

        if claims.aud not in self.allowed_audiences:
            raise InvalidClaimError(f"Invalid audience: {claims.aud}")

        return claims

    async def validate_async(self, token: str) -> TokenClaims:
        return self.validate(token)
