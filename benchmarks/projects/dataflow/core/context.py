from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PipelineContext:
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    pipeline_name: Optional[str] = None

    def update(self, data: Any) -> None:
        self.data = data

    def add_error(self, stage_name: str, message: str, exc: Optional[Exception] = None) -> None:
        self.errors.append({
            "stage": stage_name,
            "message": message,
            "exception": str(exc) if exc else None,
            "timestamp": time.time(),
        })

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def copy(self) -> PipelineContext:
        import copy
        return PipelineContext(
            data=copy.deepcopy(self.data),
            metadata=dict(self.metadata),
            errors=list(self.errors),
            created_at=self.created_at,
            pipeline_name=self.pipeline_name,
        )
