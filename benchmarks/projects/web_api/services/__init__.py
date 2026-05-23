from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseService(ABC):
    """Abstract base class for all business-logic services."""

    @abstractmethod
    async def initialize(self) -> None:
        """Perform any async setup (e.g., seed data, connect to DB)."""
        ...

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Return a health-status dictionary for this service."""
        ...


__all__ = ["BaseService"]
