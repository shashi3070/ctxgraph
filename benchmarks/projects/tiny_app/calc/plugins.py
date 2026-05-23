"""Plugin system for the calculator with example plugins."""

from __future__ import annotations

from typing import Any, Callable, Dict, List


def record_call(method: Callable) -> Callable:
    """Decorator that logs every call to the wrapped method."""
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = method(self, *args, **kwargs)
        if hasattr(self, "_call_log"):
            self._call_log.append((method.__name__, args, kwargs, result))
        return result
    return wrapper


class Plugin:
    """Base class for all calculator plugins."""

    name: str = "base"

    def on_before_calculate(self, expr: str) -> str:
        """Hook called before a calculation is performed.

        Args:
            expr: The raw expression string.

        Returns:
            The (possibly modified) expression string.
        """
        return expr

    def on_after_calculate(self, expr: str, result: float) -> None:
        """Hook called after a calculation completes.

        Args:
            expr: The original expression string.
            result: The computed result.
        """

    def on_error(self, expr: str, error: Exception) -> None:
        """Hook called when a calculation raises an exception.

        Args:
            expr: The original expression string.
            error: The exception that was raised.
        """


class PluginRegistry:
    """Registry that manages active plugins and dispatches hooks."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance. Replaces any plugin with the same name."""
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        """Remove a plugin by name."""
        self._plugins.pop(name, None)

    def get_plugins(self) -> List[Plugin]:
        """Return all registered plugin instances."""
        return list(self._plugins.values())

    def run_before(self, expr: str) -> str:
        for p in self._plugins.values():
            expr = p.on_before_calculate(expr)
        return expr

    def run_after(self, expr: str, result: float) -> None:
        for p in self._plugins.values():
            p.on_after_calculate(expr, result)

    def run_error(self, expr: str, error: Exception) -> None:
        for p in self._plugins.values():
            p.on_error(expr, error)


class HistoryPlugin(Plugin):
    """Plugin that stores a history of calculations."""

    name = "history"

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    @record_call
    def on_after_calculate(self, expr: str, result: float) -> None:
        self.history.append({"expression": expr, "result": result})

    def clear(self) -> None:
        """Clear all history entries."""
        self.history.clear()

    def last(self, n: int = 1) -> List[Dict[str, Any]]:
        """Return the last *n* history entries."""
        return self.history[-n:]


class LoggingPlugin(Plugin):
    """Plugin that prints calculation events to stdout."""

    name = "logging"

    def __init__(self, prefix: str = "[CALC]") -> None:
        self.prefix = prefix

    def on_before_calculate(self, expr: str) -> str:
        print(f"{self.prefix} evaluating: {expr}")
        return expr

    def on_after_calculate(self, expr: str, result: float) -> None:
        print(f"{self.prefix} result: {result}")

    def on_error(self, expr: str, error: Exception) -> None:
        print(f"{self.prefix} error ({expr}): {error}")
