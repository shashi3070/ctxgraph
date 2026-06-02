from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


class ConfigValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass
class FieldSchema:
    name: str
    field_type: type
    required: bool = False
    default: Any = None
    validator: Optional[Callable] = None
    description: str = ""
    choices: Optional[list] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def validate(self, value: Any) -> Optional[str]:
        if value is None and not self.required:
            return None
        if value is None and self.required:
            return f"Field '{self.name}' is required"
        if not isinstance(value, self.field_type):
            return f"Field '{self.name}' should be {self.field_type.__name__}, got {type(value).__name__}"
        if self.choices and value not in self.choices:
            return f"Field '{self.name}' must be one of {self.choices}, got '{value}'"
        if self.min_value is not None and isinstance(value, (int, float)) and value < self.min_value:
            return f"Field '{self.name}' must be >= {self.min_value}"
        if self.max_value is not None and isinstance(value, (int, float)) and value > self.max_value:
            return f"Field '{self.name}' must be <= {self.max_value}"
        if self.validator:
            error = self.validator(value)
            if error:
                return f"Field '{self.name}': {error}"
        return None


class ConfigSchema:
    def __init__(self, fields: list[FieldSchema]):
        self._fields = fields
        self._field_map = {f.name: f for f in fields}

    def validate(self, data: dict) -> list[str]:
        errors = []
        for field in self._fields:
            value = data.get(field.name)
            error = field.validate(value)
            if error:
                errors.append(error)
        for key in data:
            if key not in self._field_map:
                errors.append(f"Unknown field: '{key}'")
        return errors

    def get_defaults(self) -> dict:
        return {f.name: f.default for f in self._fields if f.default is not None}

    def coerce(self, data: dict) -> dict:
        result = {}
        for field in self._fields:
            val = data.get(field.name, field.default)
            if val is not None and not isinstance(val, field.field_type):
                try:
                    val = field.field_type(val)
                except (ValueError, TypeError):
                    pass
            result[field.name] = val
        return result
