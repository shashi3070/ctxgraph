from __future__ import annotations

from typing import Any, Optional


class PipelineError(Exception):
    def __init__(self, message: str, pipeline_name: Optional[str] = None, stage_name: Optional[str] = None):
        self.pipeline_name = pipeline_name
        self.stage_name = stage_name
        super().__init__(message)


class StageError(PipelineError):
    def __init__(self, message: str, stage_name: str, pipeline_name: Optional[str] = None, context: Optional[dict] = None):
        self.context = context or {}
        super().__init__(message, pipeline_name, stage_name)


class ProcessorError(PipelineError):
    def __init__(self, message: str, processor_name: str, data: Any = None):
        self.processor_name = processor_name
        self.data = data
        super().__init__(message)


class ConfigError(PipelineError):
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(message)


class ConnectionError(PipelineError):
    def __init__(self, message: str, host: str, port: Optional[int] = None):
        self.host = host
        self.port = port
        super().__init__(message)


class TimeoutError(PipelineError):
    def __init__(self, message: str, timeout_seconds: float, component: str = "unknown"):
        self.timeout_seconds = timeout_seconds
        self.component = component
        super().__init__(message)


class DataFormatError(PipelineError):
    def __init__(self, message: str, expected_format: str, actual_format: str):
        self.expected_format = expected_format
        self.actual_format = actual_format
        super().__init__(message)


class ValidationError(PipelineError):
    def __init__(self, message: str, field_errors: Optional[list[str]] = None):
        self.field_errors = field_errors or []
        super().__init__(message)


class RetryExhaustedError(PipelineError):
    def __init__(self, message: str, attempts: int, last_error: Optional[Exception] = None):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(message)
