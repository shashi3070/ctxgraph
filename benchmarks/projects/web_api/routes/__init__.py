from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseRouter(ABC):
    """Abstract base class for route groups.

    Each subclass defines a set of related HTTP endpoints and returns
    route definitions via *register_routes*.
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._routes: List[Dict[str, Any]] = []

    @abstractmethod
    def register_routes(self) -> List[Dict[str, Any]]:
        """Return a list of route dictionaries.

        Each dictionary should contain at minimum:
            - method  (str): HTTP method
            - path    (str): URL path (prefixed automatically)
            - handler (callable): async handler(request) -> response
            - auth_required (bool): whether auth is enforced
        """
        ...

    def get_routes(self) -> List[Dict[str, Any]]:
        """Return (and cache) the route definitions."""
        if not self._routes:
            self._routes = self.register_routes()
        return self._routes


__all__ = ["BaseRouter"]
