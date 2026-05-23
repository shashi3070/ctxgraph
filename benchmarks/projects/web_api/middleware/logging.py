import time
import logging
from typing import Any, Dict, Optional
from . import BaseMiddleware


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware that logs every request with HTTP method, path, status code,
    and elapsed time. Optionally logs request/response bodies in debug mode."""

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        super().__init__(options)
        self._log_request_body = self.options.get("log_request_body", False)
        self._log_response_body = self.options.get("log_response_body", False)

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        request["_start_time"] = time.monotonic()
        method = request.get("method", "GET")
        path = request.get("path", "/")
        query = request.get("query_string", "")

        log_line = f"Incoming {method} {path}"
        if query:
            log_line += f"?{query}"
        if self._log_request_body and request.get("body"):
            log_line += f" | body: {request['body']}"

        logger.info(log_line)
        return request

    async def process_response(
        self, request: Dict[str, Any], response: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_time = request.pop("_start_time", None)
        elapsed = time.monotonic() - start_time if start_time else 0.0
        elapsed_ms = round(elapsed * 1000, 2)

        method = request.get("method", "GET")
        path = request.get("path", "/")
        status = response.get("status_code", 200)

        log_line = f"{method} {path} -> {status} [{elapsed_ms}ms]"
        if self._log_response_body and response.get("body"):
            log_line += f" | body: {response['body']}"

        if status >= 500:
            logger.error(log_line)
        elif status >= 400:
            logger.warning(log_line)
        else:
            logger.info(log_line)

        response.setdefault("headers", {})["X-Response-Time-Ms"] = str(elapsed_ms)
        return response
