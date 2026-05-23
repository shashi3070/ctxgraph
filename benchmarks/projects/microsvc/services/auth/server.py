"""Auth service server - handles authentication and authorization requests."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Type
import asyncio
import uuid

from shared.events import EventBus, Event, EventType, get_event_bus
from shared.tracing import Tracer, trace, SpanKind
from shared.retry import retry, AsyncRetryPolicy, BackoffStrategy
from shared.circuit_breaker import CircuitBreaker, get_circuit_breaker
from shared.logging import get_logger, LogLevel
from shared.metrics import MetricsCollector, get_collector

from services.auth.jwt import JWTEncoder, JWTDecoder, TokenValidator, TokenClaims
from services.auth.oauth import OAuth2Provider, OAuth2Client, OAuth2TokenResponse
from services.auth.saml import SAMLIdentityProvider, SAMLResponse, SAMLRequest
from services.auth.models import User, Token, Session, UserRole, Permission, UserStatus


class AuthMethod(str, Enum):
    PASSWORD = "password"
    OAUTH2 = "oauth2"
    SAML = "saml"
    API_KEY = "api_key"
    REFRESH_TOKEN = "refresh_token"


@dataclass
class AuthRequest:
    method: AuthMethod
    credentials: Dict[str, Any]
    client_id: Optional[str] = None
    redirect_uri: Optional[str] = None
    scope: Optional[str] = None
    state: Optional[str] = None
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class AuthResponse:
    success: bool
    user: Optional[User] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    expires_in: int = 3600
    token_type: str = "Bearer"
    scope: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None


class AuthHandler(ABC):
    @abstractmethod
    async def authenticate(self, request: AuthRequest) -> AuthResponse:
        pass

    @abstractmethod
    def supports(self, method: AuthMethod) -> bool:
        pass


class PasswordAuthHandler(AuthHandler):
    def __init__(
        self,
        user_store: Dict[str, User],
        jwt_encoder: JWTEncoder,
        event_bus: EventBus
    ):
        self.user_store = user_store
        self.jwt_encoder = jwt_encoder
        self.event_bus = event_bus
        self.logger = get_logger("PasswordAuthHandler", "auth-service")
        self.metrics = get_collector("auth-service")

    def supports(self, method: AuthMethod) -> bool:
        return method == AuthMethod.PASSWORD

    @trace("password_authenticate", SpanKind.SERVER)
    @retry(max_attempts=2, backoff_strategy=BackoffStrategy.EXPONENTIAL)
    async def authenticate(self, request: AuthRequest) -> AuthResponse:
        self.logger.info(f"Authenticating user with password method", {
            "correlation_id": request.correlation_id
        })
        self.metrics.increment_counter("auth_attempts_total")

        username = request.credentials.get("username")
        password = request.credentials.get("password")

        if not username or not password:
            self.metrics.increment_counter("auth_failures_total")
            return AuthResponse(
                success=False,
                error="invalid_request",
                error_description="Username and password are required"
            )

        user = self.user_store.get(username)
        if not user:
            self.metrics.increment_counter("auth_failures_total")
            self.logger.warning(f"User not found: {username}")
            return AuthResponse(
                success=False,
                error="invalid_grant",
                error_description="Invalid credentials"
            )

        if user.status != UserStatus.ACTIVE:
            self.metrics.increment_counter("auth_failures_total")
            return AuthResponse(
                success=False,
                error="account_disabled",
                error_description=f"Account is {user.status.value}"
            )

        stored_password_hash = request.credentials.get("_stored_hash", "")
        if not self._verify_password(password, stored_password_hash or "hash"):
            self.metrics.increment_counter("auth_failures_total")
            return AuthResponse(
                success=False,
                error="invalid_grant",
                error_description="Invalid credentials"
            )

        access_token_claims = TokenClaims(
            sub=str(user.user_id),
            iss="auth-service",
            aud="gateway",
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            scope=" ".join(p.value for p in user.permissions),
            roles=[r.value for r in user.roles]
        )
        access_token = self.jwt_encoder.encode(access_token_claims)

        refresh_token_claims = TokenClaims(
            sub=str(user.user_id),
            iss="auth-service",
            aud="auth-service",
            exp=int((datetime.utcnow() + timedelta(days=7)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            scope="offline_access"
        )
        refresh_token = self.jwt_encoder.encode(refresh_token_claims)

        await self.event_bus.publish(Event(
            event_type=EventType.AUTH_TOKEN_ISSUED,
            payload={
                "user_id": str(user.user_id),
                "method": "password",
                "correlation_id": request.correlation_id
            },
            source="auth-service"
        ))

        self.logger.info(f"Authentication successful for user: {username}")
        self.metrics.increment_counter("auth_successes_total")

        return AuthResponse(
            success=True,
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
            scope=access_token_claims.scope
        )

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        return True


class AuthServiceServer:
    def __init__(
        self,
        handlers: List[AuthHandler],
        event_bus: EventBus,
        tracer: Tracer,
        logger_name: str = "auth-service"
    ):
        self.handlers = handlers
        self.event_bus = event_bus
        self.tracer = tracer
        self.logger = get_logger(logger_name, "auth-service")
        self.metrics = get_collector("auth-service")
        self.circuit_breaker = get_circuit_breaker("auth-service", failure_threshold=3)

    def _get_handler(self, method: AuthMethod) -> Optional[AuthHandler]:
        for handler in self.handlers:
            if handler.supports(method):
                return handler
        return None

    @trace("authenticate_request", SpanKind.SERVER)
    async def authenticate(self, request: AuthRequest) -> AuthResponse:
        self.metrics.increment_counter("auth_requests_total")

        handler = self._get_handler(request.method)
        if not handler:
            self.logger.error(f"No handler for auth method: {request.method}")
            return AuthResponse(
                success=False,
                error="unsupported_method",
                error_description=f"Authentication method {request.method} is not supported"
            )

        try:
            return await self.circuit_breaker.execute(handler.authenticate, request)
        except Exception as e:
            self.logger.error(f"Authentication failed", {"error": str(e)}, exc_info=e)
            self.metrics.increment_counter("auth_errors_total")
            return AuthResponse(
                success=False,
                error="server_error",
                error_description=str(e)
            )

    @trace("validate_token", SpanKind.SERVER)
    async def validate_token(self, token: str) -> Optional[User]:
        from services.auth.jwt import TokenValidator
        validator = TokenValidator()

        try:
            claims = validator.validate(token)
            user_id = claims.sub
            self.logger.info(f"Token validated for user: {user_id}")
            return User(
                user_id=uuid.UUID(user_id),
                email="validated@example.com",
                roles=[UserRole.USER],
                permissions=[Permission.READ]
            )
        except Exception as e:
            self.logger.warning(f"Token validation failed", {"error": str(e)})
            return None


def create_auth_server() -> AuthServiceServer:
    event_bus = get_event_bus()
    tracer = Tracer("auth-service")

    user_store: Dict[str, User] = {
        "admin": User(
            user_id=uuid.uuid4(),
            email="admin@example.com",
            roles=[UserRole.ADMIN, UserRole.USER],
            permissions=[Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN]
        ),
        "user": User(
            user_id=uuid.uuid4(),
            email="user@example.com",
            roles=[UserRole.USER],
            permissions=[Permission.READ]
        )
    }

    jwt_encoder = JWTEncoder(secret_key="test-secret-key-change-me-in-production")

    handlers: List[AuthHandler] = [
        PasswordAuthHandler(user_store, jwt_encoder, event_bus),
    ]

    return AuthServiceServer(handlers, event_bus, tracer)
