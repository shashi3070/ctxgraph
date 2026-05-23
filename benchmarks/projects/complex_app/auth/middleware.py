from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, List, Optional, Sequence

from complex_app.auth.service import AuthService
from complex_app.shared.errors import AuthenticationError, AuthorizationError

_current_user: Any = None


def get_current_user() -> Any:
    global _current_user
    return _current_user


def _get_auth_service() -> AuthService:
    from complex_app.auth.jwt import JWTManager
    from complex_app.shared.cache import get_cache
    from complex_app.shared.database import get_database
    from complex_app.shared.config import get_config

    config = get_config()
    jwt_manager = JWTManager(secret_key=config.secret_key)
    db = get_database()
    cache = get_cache()
    return AuthService(db=db, cache=cache, jwt_manager=jwt_manager)


def require_auth(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = kwargs.get("token")
        if token is None:
            for arg in args:
                if isinstance(arg, str) and len(arg) > 20:
                    token = arg
                    break

        if not token:
            raise AuthenticationError(
                code="missing_token", message="Authentication token is required"
            )

        auth_service = _get_auth_service()
        user = auth_service.validate_token(token)

        global _current_user
        _current_user = user

        try:
            return func(*args, **kwargs)
        finally:
            _current_user = None

    return wrapper


def require_role(*roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            token = kwargs.get("token")
            if token is None:
                for arg in args:
                    if isinstance(arg, str) and len(arg) > 20:
                        token = arg
                        break

            if not token:
                raise AuthenticationError(
                    code="missing_token",
                    message="Authentication token is required",
                )

            auth_service = _get_auth_service()
            user = auth_service.validate_token(token)

            has_role = any(role in user.roles for role in roles)
            if not has_role:
                raise AuthorizationError(
                    code="insufficient_role",
                    message="User does not have the required role",
                )

            global _current_user
            _current_user = user

            try:
                return func(*args, **kwargs)
            finally:
                _current_user = None

        return wrapper

    return decorator


def require_permission(
    *permissions: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            token = kwargs.get("token")
            if token is None:
                for arg in args:
                    if isinstance(arg, str) and len(arg) > 20:
                        token = arg
                        break

            if not token:
                raise AuthenticationError(
                    code="missing_token",
                    message="Authentication token is required",
                )

            auth_service = _get_auth_service()
            user = auth_service.validate_token(token)

            for permission in permissions:
                if not auth_service.has_permission(user, permission):
                    raise AuthorizationError(
                        code="insufficient_permissions",
                        message=f"User does not have the '{permission}' permission",
                    )

            global _current_user
            _current_user = user

            try:
                return func(*args, **kwargs)
            finally:
                _current_user = None

        return wrapper

    return decorator
