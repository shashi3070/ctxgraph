import time
import asyncio
import logging
from typing import Any, Dict, Optional, Tuple
from collections import defaultdict
from . import BaseMiddleware


logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter.

    Maintains a per-key token bucket that refills at a configurable rate.
    Thread-safe via an asyncio lock for use in async contexts.
    """

    def __init__(self, capacity: int, refill_rate: float, refill_interval: float = 1.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self._tokens: Dict[str, float] = defaultdict(lambda: float(capacity))
        self._last_refill: Dict[str, float] = defaultdict(time.monotonic)
        self._lock = asyncio.Lock()

    async def consume(self, key: str, tokens: float = 1.0) -> Tuple[bool, int]:
        """Try to consume *tokens* from the bucket for *key*.

        Returns (allowed, remaining_tokens).
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill[key]
            refill_amount = elapsed * self.refill_rate
            self._tokens[key] = min(self.capacity, self._tokens[key] + refill_amount)
            self._last_refill[key] = now

            if self._tokens[key] >= tokens:
                self._tokens[key] -= tokens
                return True, int(self._tokens[key])
            return False, int(self._tokens[key])

    async def get_remaining(self, key: str) -> int:
        """Return the current token count for *key* without consuming."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill[key]
            refill_amount = elapsed * self.refill_rate
            self._tokens[key] = min(self.capacity, self._tokens[key] + refill_amount)
            self._last_refill[key] = now
            return int(self._tokens[key])


class RateLimitMiddleware(BaseMiddleware):
    """Middleware that enforces a token-bucket rate limit per client IP."""

    def __init__(
        self,
        capacity: int = 100,
        refill_rate: float = 10.0,
        options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(options)
        self._bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate)
        self._exclude_paths = set(options.get("exclude_paths", []) if options else [])

    def _get_client_key(self, request: Dict[str, Any]) -> str:
        headers = request.get("headers", {})
        forwarded = headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.get("client_ip", "127.0.0.1")

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        path = request.get("path", "/")
        if path in self._exclude_paths:
            return request

        client_key = self._get_client_key(request)
        allowed, remaining = await self._bucket.consume(client_key)

        request["_rate_limit_remaining"] = remaining
        request["_rate_limit_key"] = client_key

        if not allowed:
            logger.warning("Rate limit exceeded for %s on %s", client_key, path)
            retry_after = 60.0 / self._bucket.refill_rate
            raise RateLimitExceededError(
                f"Rate limit exceeded. Try again in {retry_after:.1f} seconds.",
                remaining=remaining,
            )

        return request

    async def process_response(
        self, request: Dict[str, Any], response: Dict[str, Any]
    ) -> Dict[str, Any]:
        remaining = request.get("_rate_limit_remaining", 0)
        response.setdefault("headers", {})["X-RateLimit-Remaining"] = str(remaining)
        return response


class RateLimitExceededError(Exception):
    """Raised when a client exceeds the allowed rate limit."""

    def __init__(self, message: str, remaining: int = 0):
        super().__init__(message)
        self.remaining = remaining
