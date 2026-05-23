from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable


class BaseMiddleware(ABC):
    """Abstract base class for all middleware components.

    Implements the Chain of Responsibility pattern for processing
    HTTP requests and responses through a pipeline.
    """

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        self.options = options or {}

    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming request before it reaches the route handler.

        Args:
            request: The raw request dictionary with method, path, headers, body, etc.

        Returns:
            The (possibly modified) request dictionary.

        Raises:
            PermissionError: If the request is not authorized.
            RateLimitExceededError: If rate limit is exceeded.
        """
        ...

    @abstractmethod
    async def process_response(
        self, request: Dict[str, Any], response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process an outgoing response after the route handler completes.

        Args:
            request: The original request dictionary.
            response: The response dictionary with status_code, body, headers.

        Returns:
            The (possibly modified) response dictionary.
        """
        ...

    async def __call__(
        self, request: Dict[str, Any], handler: Callable
    ) -> Dict[str, Any]:
        """Invoke the middleware pipeline by processing the request,
        calling the next handler, and processing the response."""
        processed_request = await self.process_request(request)
        response = await handler(processed_request)
        return await self.process_response(processed_request, response)


__all__ = ["BaseMiddleware"]
