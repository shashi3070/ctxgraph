import asyncio
import logging
from typing import Any, Dict, List, Callable

from config import settings
from middleware.auth import AuthMiddleware
from middleware.logging import LoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware, RateLimitExceededError
from routes.auth import AuthRouter
from routes.users import UserRouter
from routes.posts import PostRouter
from routes.admin import AdminRouter
from services.auth_service import AuthService
from services.user_service import UserService
from services.post_service import PostService


logger = logging.getLogger(__name__)


class Application:
    """Minimal web framework that simulates a FastAPI-like request lifecycle.

    Composes middleware into a pipeline, registers route handlers grouped
    by router, and dispatches incoming requests through the chain.
    """

    def __init__(self):
        self._routes: List[Dict[str, Any]] = []
        self._middleware: List[Callable] = []
        self._services: Dict[str, Any] = {}
        self._route_map: Dict[str, Dict[str, Any]] = {}

        self._setup_logging()
        self._init_services()
        self._init_middleware()
        self._init_routes()

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
            format=settings.log_format,
        )
        logger.info(
            "Starting %s in %s mode",
            settings.app_name,
            "debug" if settings.debug else "production",
        )

    def _init_services(self) -> None:
        self._services["user_service"] = UserService()
        self._services["post_service"] = PostService()
        self._services["auth_service"] = AuthService(
            user_service=self._services["user_service"]
        )

    def _init_middleware(self) -> None:
        self._middleware = [
            LoggingMiddleware(
                options={"log_request_body": settings.debug}
            ),
            RateLimitMiddleware(
                capacity=settings.rate_limit_requests,
                refill_rate=settings.rate_limit_requests
                / settings.rate_limit_window_seconds,
            ),
            AuthMiddleware(auth_service=self._services["auth_service"]),
        ]

    def _init_routes(self) -> None:
        auth_router = AuthRouter(
            self._services["auth_service"], self._services["user_service"]
        )
        user_router = UserRouter(
            self._services["user_service"], self._services["auth_service"]
        )
        post_router = PostRouter(self._services["post_service"])
        admin_router = AdminRouter(
            self._services["user_service"],
            self._services["post_service"],
            self._services["auth_service"],
        )

        for router in (auth_router, user_router, post_router, admin_router):
            for route in router.get_routes():
                full_path = f"{settings.api_prefix}{route['path']}"
                method = route["method"]
                key = f"{method}:{full_path}"

                if key in self._route_map:
                    logger.warning("Duplicate route: %s", key)

                self._route_map[key] = route
                self._routes.append(route)
                logger.debug("Registered %s %s", method, full_path)

    async def startup(self) -> None:
        """Initialize all registered services."""
        logger.info("Initializing services...")
        for name, service in self._services.items():
            await service.initialize()
        logger.info("All services initialized. Ready to handle requests.")

    async def _apply_middleware_chain(
        self, request: Dict[str, Any], handler: Callable
    ) -> Dict[str, Any]:
        """Build a call chain by nesting middleware around the route handler."""

        async def call_handler(req: Dict[str, Any]) -> Dict[str, Any]:
            return await handler(req)

        chain = call_handler
        for mw in reversed(self._middleware):

            async def layer(req: Dict[str, Any], mw=mw, next_=chain) -> Dict[str, Any]:
                return await mw(req, next_)

            chain = layer

        return await chain(request)

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a single request through the middleware + route handler."""
        method = request.get("method", "GET")
        path = request.get("path", "/")
        key = f"{method}:{path}"

        route = self._route_map.get(key)
        if not route:
            return {"status_code": 404, "body": {"error": f"Route {method} {path} not found"}}

        handler = route["handler"]
        request["route_info"] = route

        try:
            return await self._apply_middleware_chain(request, handler)
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}
        except RateLimitExceededError as exc:
            return {
                "status_code": 429,
                "body": {"error": str(exc)},
                "headers": {"Retry-After": "60"},
            }
        except ValueError as exc:
            return {"status_code": 400, "body": {"error": str(exc)}}
        except Exception:
            logger.exception("Unhandled error processing %s %s", method, path)
            return {"status_code": 500, "body": {"error": "Internal server error"}}

    async def shutdown(self) -> None:
        """Clean up services and middleware."""
        logger.info("Shutting down application...")
        self._services.clear()
        self._routes.clear()
        self._route_map.clear()
        self._middleware.clear()
        logger.info("Application shutdown complete.")


async def main() -> None:
    """Entry point: bootstrap the app and demo a sample request."""
    app = Application()
    await app.startup()

    sample_request = {
        "method": "POST",
        "path": "/api/v1/auth/register",
        "headers": {"Content-Type": "application/json"},
        "body": {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        },
        "client_ip": "127.0.0.1",
    }

    response = await app.handle_request(sample_request)
    logger.info("Sample response: %s", response)

    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
