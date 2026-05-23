"""OAuth2 integration for third-party authentication."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import asyncio
import secrets
import string
import uuid

from shared.events import EventBus, Event, EventType
from shared.tracing import Tracer, trace, SpanKind
from shared.retry import retry, AsyncRetryPolicy
from shared.logging import get_logger
from shared.metrics import get_collector


class OAuth2Flow(str, Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    IMPLICIT = "implicit"
    PASSWORD = "password"
    REFRESH_TOKEN = "refresh_token"


class OAuth2ResponseType(str, Enum):
    CODE = "code"
    TOKEN = "id_token"
    CODE_ID_TOKEN = "code id_token"


@dataclass
class OAuth2Client:
    client_id: str
    client_secret: str
    name: str
    redirect_uris: List[str]
    allowed_scopes: Set[str]
    allowed_flows: Set[OAuth2Flow]
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OAuth2AuthorizationCode:
    code: str
    client_id: str
    user_id: str
    redirect_uri: str
    scope: str
    expires_at: datetime
    used: bool = False
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None


@dataclass
class OAuth2TokenResponse:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None


@dataclass
class OAuth2ErrorResponse:
    error: str
    error_description: Optional[str] = None
    error_uri: Optional[str] = None


class OAuth2Provider(ABC):
    @abstractmethod
    async def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        response_type: OAuth2ResponseType = OAuth2ResponseType.CODE,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> str:
        pass

    @abstractmethod
    async def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> OAuth2TokenResponse:
        pass

    @abstractmethod
    async def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None
    ) -> OAuth2TokenResponse:
        pass

    @abstractmethod
    async def revoke_token(
        self,
        token: str,
        client_id: str,
        client_secret: str,
        token_type_hint: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    async def introspect_token(
        self,
        token: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        pass


class InternalOAuth2Provider(OAuth2Provider):
    def __init__(
        self,
        clients: Dict[str, OAuth2Client],
        event_bus: EventBus,
        tracer: Tracer
    ):
        self.clients = clients
        self.event_bus = event_bus
        self.tracer = tracer
        self.logger = get_logger("OAuth2Provider", "auth-service")
        self.metrics = get_collector("auth-service")
        self._auth_codes: Dict[str, OAuth2AuthorizationCode] = {}
        self._refresh_tokens: Dict[str, Dict[str, Any]] = {}

    def _generate_code(self, length: int = 32) -> str:
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(length))

    @trace("oauth2_authorize", SpanKind.SERVER)
    async def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        response_type: OAuth2ResponseType = OAuth2ResponseType.CODE,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> str:
        if client_id not in self.clients:
            raise ValueError(f"Unknown client: {client_id}")

        client = self.clients[client_id]

        if redirect_uri not in client.redirect_uris:
            raise ValueError(f"Redirect URI not allowed: {redirect_uri}")

        requested_scopes = set(scope.split()) if scope else set()
        if not requested_scopes.issubset(client.allowed_scopes):
            raise ValueError(f"Scope not allowed: {requested_scopes - client.allowed_scopes}")

        code = self._generate_code(48)
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        self._auth_codes[code] = OAuth2AuthorizationCode(
            code=code,
            client_id=client_id,
            user_id="demo-user-id",
            redirect_uri=redirect_uri,
            scope=scope,
            expires_at=expires_at,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )

        self.metrics.increment_counter("oauth2_authorizations_total")
        self.logger.info(f"Generated authorization code for client: {client_id}")

        base_url = redirect_uri
        separator = "&" if "?" in base_url else "?"
        url = f"{base_url}{separator}code={code}"
        if state:
            url += f"&state={state}"
        return url

    @trace("oauth2_token_exchange", SpanKind.SERVER)
    @retry(max_attempts=2)
    async def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> OAuth2TokenResponse:
        if code not in self._auth_codes:
            raise ValueError("Invalid or expired authorization code")

        auth_code = self._auth_codes[code]

        if auth_code.used:
            raise ValueError("Authorization code already used")

        if auth_code.client_id != client_id:
            raise ValueError("Client ID mismatch")

        if auth_code.redirect_uri != redirect_uri:
            raise ValueError("Redirect URI mismatch")

        if datetime.utcnow() > auth_code.expires_at:
            del self._auth_codes[code]
            raise ValueError("Authorization code expired")

        client = self.clients.get(client_id)
        if not client:
            raise ValueError("Unknown client")

        if not client.is_public and client.client_secret != client_secret:
            raise ValueError("Invalid client secret")

        auth_code.used = True

        access_token = self._generate_code(64)
        refresh_token = self._generate_code(64)

        self._refresh_tokens[refresh_token] = {
            "client_id": client_id,
            "user_id": auth_code.user_id,
            "scope": auth_code.scope,
            "created_at": datetime.utcnow()
        }

        self.metrics.increment_counter("oauth2_tokens_issued_total")
        self.logger.info(f"Exchanged code for tokens: client={client_id}")

        return OAuth2TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            refresh_token=refresh_token,
            scope=auth_code.scope
        )

    @trace("oauth2_refresh", SpanKind.SERVER)
    async def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None
    ) -> OAuth2TokenResponse:
        if refresh_token not in self._refresh_tokens:
            raise ValueError("Invalid refresh token")

        token_data = self._refresh_tokens[refresh_token]

        if token_data["client_id"] != client_id:
            raise ValueError("Client ID mismatch")

        access_token = self._generate_code(64)

        self.metrics.increment_counter("oauth2_tokens_refreshed_total")

        return OAuth2TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            scope=token_data.get("scope")
        )

    async def revoke_token(
        self,
        token: str,
        client_id: str,
        client_secret: str,
        token_type_hint: Optional[str] = None
    ) -> None:
        if token in self._refresh_tokens:
            if self._refresh_tokens[token]["client_id"] == client_id:
                del self._refresh_tokens[token]
                self.logger.info(f"Revoked refresh token for client: {client_id}")

    async def introspect_token(
        self,
        token: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        if token in self._refresh_tokens:
            token_data = self._refresh_tokens[token]
            return {
                "active": True,
                "scope": token_data.get("scope"),
                "client_id": token_data["client_id"],
                "sub": token_data["user_id"],
                "token_type": "refresh_token"
            }
        return {"active": False}


def create_default_oauth_provider(event_bus: EventBus, tracer: Tracer) -> InternalOAuth2Provider:
    clients = {
        "gateway-client": OAuth2Client(
            client_id="gateway-client",
            client_secret="gateway-secret",
            name="API Gateway",
            redirect_uris=["http://localhost:8080/callback"],
            allowed_scopes={"read", "write", "admin", "openid", "profile", "email"},
            allowed_flows={OAuth2Flow.AUTHORIZATION_CODE, OAuth2Flow.CLIENT_CREDENTIALS, OAuth2Flow.REFRESH_TOKEN},
            is_public=False
        ),
        "spa-client": OAuth2Client(
            client_id="spa-client",
            client_secret="",
            name="Single Page App",
            redirect_uris=["http://localhost:3000/callback"],
            allowed_scopes={"read", "write", "openid", "profile", "email"},
            allowed_flows={OAuth2Flow.AUTHORIZATION_CODE, OAuth2Flow.REFRESH_TOKEN},
            is_public=True
        )
    }
    return InternalOAuth2Provider(clients, event_bus, tracer)
