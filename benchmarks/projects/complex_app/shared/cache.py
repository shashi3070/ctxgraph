from __future__ import annotations

import time
from typing import Any, Dict, Optional

from complex_app.shared.config import get_config


class Cache:
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self._store

    def clear(self) -> None:
        self._store.clear()


class TTLCache(Cache):
    def __init__(self, default_ttl: int = 300) -> None:
        super().__init__()
        self._default_ttl = default_ttl
        self._expires: Dict[str, float] = {}

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        super().set(key, value)
        expiry = ttl if ttl is not None else self._default_ttl
        self._expires[key] = time.time() + expiry

    def get(self, key: str) -> Optional[Any]:
        if key in self._expires and time.time() > self._expires[key]:
            self.delete(key)
            return None
        return super().get(key)

    def delete(self, key: str) -> None:
        super().delete(key)
        self._expires.pop(key, None)


_cache_instance: Optional[Cache] = None


def get_cache() -> Cache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = Cache()
    return _cache_instance
