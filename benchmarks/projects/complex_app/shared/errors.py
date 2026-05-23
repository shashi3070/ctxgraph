from __future__ import annotations

from typing import Any, Optional


class AppError(Exception):
    def __init__(
        self,
        code: str = "internal_error",
        message: str = "An unexpected error occurred",
        status_code: int = 500,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppError):
    def __init__(
        self,
        code: str = "not_found",
        message: str = "Resource not found",
        status_code: int = 404,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class ValidationError(AppError):
    def __init__(
        self,
        code: str = "validation_error",
        message: str = "Validation failed",
        status_code: int = 422,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class AuthorizationError(AppError):
    def __init__(
        self,
        code: str = "authorization_error",
        message: str = "Access denied",
        status_code: int = 403,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class AuthenticationError(AppError):
    def __init__(
        self,
        code: str = "authentication_error",
        message: str = "Authentication required",
        status_code: int = 401,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class TokenExpiredError(AppError):
    def __init__(
        self,
        code: str = "token_expired",
        message: str = "Token has expired",
        status_code: int = 401,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class RateLimitError(AppError):
    def __init__(
        self,
        code: str = "rate_limit_exceeded",
        message: str = "Too many requests",
        status_code: int = 429,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class ServiceUnavailableError(AppError):
    def __init__(
        self,
        code: str = "service_unavailable",
        message: str = "Service is temporarily unavailable",
        status_code: int = 503,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code)
