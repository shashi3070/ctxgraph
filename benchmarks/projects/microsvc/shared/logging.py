"""Structured logging utilities for microservices."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
import inspect
import json
import sys


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


LOG_LEVEL_ORDER = {
    LogLevel.DEBUG: 10,
    LogLevel.INFO: 20,
    LogLevel.WARNING: 30,
    LogLevel.ERROR: 40,
    LogLevel.CRITICAL: 50,
}


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    logger: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    extra: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "timestamp": self.timestamp.isoformat() + "Z",
            "level": self.level.value,
            "service": self.service,
            "message": self.message,
            "logger": self.logger,
        }
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.span_id:
            result["span_id"] = self.span_id
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        if self.extra:
            result.update(self.extra)
        return result


class LogFormatter(ABC):
    @abstractmethod
    def format(self, entry: LogEntry) -> str:
        pass


class JSONFormatter(LogFormatter):
    def format(self, entry: LogEntry) -> str:
        return json.dumps(entry.to_dict(), default=str)


class ConsoleFormatter(LogFormatter):
    COLORS = {
        LogLevel.DEBUG: "\033[36m",
        LogLevel.INFO: "\033[32m",
        LogLevel.WARNING: "\033[33m",
        LogLevel.ERROR: "\033[31m",
        LogLevel.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, entry: LogEntry) -> str:
        color = self.COLORS.get(entry.level, "")
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        msg = f"{color}[{entry.level}] {ts} {entry.service}: {entry.message}{self.RESET}"
        if entry.extra:
            extra_str = " ".join(f"{k}={v}" for k, v in entry.extra.items())
            msg += f" | {extra_str}"
        return msg


class Logger:
    def __init__(
        self,
        name: str,
        service: str,
        level: LogLevel = LogLevel.INFO,
        formatter: LogFormatter = None
    ):
        self.name = name
        self.service = service
        self.level = level
        self.formatter = formatter or ConsoleFormatter()
        self._trace_context_getter: Optional[Callable[[], Dict[str, str]]] = None

    def set_trace_context_getter(self, getter: Callable[[], Dict[str, str]]) -> None:
        self._trace_context_getter = getter

    def _get_trace_context(self) -> Dict[str, Optional[str]]:
        if self._trace_context_getter:
            return self._trace_context_getter()
        return {"trace_id": None, "span_id": None}

    def _should_log(self, level: LogLevel) -> bool:
        return LOG_LEVEL_ORDER[level] >= LOG_LEVEL_ORDER[self.level]

    def _log(
        self,
        level: LogLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> None:
        if not self._should_log(level):
            return

        trace_ctx = self._get_trace_context()
        extra_with_exc = extra or {}
        if exc_info:
            extra_with_exc["exception"] = str(exc_info)
            import traceback
            extra_with_exc["traceback"] = traceback.format_exc()

        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            service=self.service,
            message=message,
            logger=self.name,
            trace_id=trace_ctx.get("trace_id"),
            span_id=trace_ctx.get("span_id"),
            extra=extra_with_exc if extra_with_exc else None
        )
        print(self.formatter.format(entry), file=sys.stderr)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._log(LogLevel.DEBUG, message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._log(LogLevel.INFO, message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._log(LogLevel.WARNING, message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None) -> None:
        self._log(LogLevel.ERROR, message, extra, exc_info)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None) -> None:
        self._log(LogLevel.CRITICAL, message, extra, exc_info)


_loggers: Dict[str, Logger] = {}
_default_service = "microsvc"


def get_logger(name: Optional[str] = None, service: Optional[str] = None) -> Logger:
    if name is None:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", "unknown")
        else:
            name = "unknown"

    key = f"{service or _default_service}:{name}"
    if key not in _loggers:
        _loggers[key] = Logger(name, service or _default_service)
    return _loggers[key]


def structured_log(level: LogLevel, message: str, **kwargs: Any) -> None:
    logger = get_logger()
    logger._log(level, message, kwargs)
