"""Redis client wrapper."""
from src.core.exceptions import ConnectionError


class RedisClient:
    def __init__(self, url="redis://localhost:6379"):
        self.url = url
        self._connected = False

    def connect(self):
        self._connected = True

    def get(self, key):
        if not self._connected:
            raise ConnectionError("Redis not connected")
        return None

    def set(self, key, value, ttl=None):
        if not self._connected:
            raise ConnectionError("Redis not connected")
        return True

    def delete(self, key):
        if not self._connected:
            raise ConnectionError("Redis not connected")
        return True
