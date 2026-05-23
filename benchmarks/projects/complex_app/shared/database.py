from __future__ import annotations

import contextlib
from typing import Any, Dict, List, Optional

from complex_app.shared.config import get_config


class Database:
    def __init__(self) -> None:
        self._connected = False
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def connect(self) -> None:
        config = get_config()
        _ = config.database_url
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._store.clear()

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
        if not self._connected:
            raise RuntimeError("Database is not connected")

    def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Database is not connected")
        return None

    def fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Database is not connected")
        return []


class Transaction:
    def __init__(self, db: Database) -> None:
        self._db = db

    def __enter__(self) -> Database:
        return self._db

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        pass


_db_instance: Optional[Database] = None


def get_database() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
