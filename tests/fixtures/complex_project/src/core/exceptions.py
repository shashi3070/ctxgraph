"""Custom exception hierarchy."""


class AppError(Exception):
    pass


class ConfigError(AppError):
    pass


class AuthenticationError(AppError):
    pass


class ConnectionError(AppError):
    pass


class ValidationError(AppError):
    pass


class NotFoundError(AppError):
    pass
