"""API route definitions."""
from src.api.middleware import AuthMiddleware, RateLimiter
from src.api.handlers import HealthHandler, UserHandler, AdminHandler
from src.core.exceptions import ConfigError


def create_app(config):
    if not config:
        raise ConfigError("Configuration required")

    routes = {
        "/health": HealthHandler(),
        "/users/login": UserHandler(),
        "/users/register": UserHandler(),
        "/admin/users": AdminHandler(),
    }

    middleware = [
        RateLimiter(config.get("rate_limit", 100)),
        AuthMiddleware(config.get("jwt_secret", "default-secret")),
    ]

    return App(routes, middleware)


class App:
    def __init__(self, routes, middleware):
        self.routes = routes
        self.middleware = middleware

    def run(self, host, port):
        print(f"Starting on {host}:{port}")
