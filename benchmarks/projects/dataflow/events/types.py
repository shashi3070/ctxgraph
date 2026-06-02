from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Event:
    source: str
    type: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "type": self.type,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class PipelineEvent(Event):
    def __init__(self, pipeline_name: str, event_type: str, data: Optional[dict] = None):
        import time
        super().__init__(
            source=f"pipeline:{pipeline_name}",
            type=event_type,
            timestamp=time.time(),
            data=data or {},
        )
        self.pipeline_name = pipeline_name


class StageEvent(Event):
    def __init__(self, stage_name: str, pipeline_name: str, event_type: str, data: Optional[dict] = None):
        import time
        super().__init__(
            source=f"stage:{stage_name}",
            type=event_type,
            timestamp=time.time(),
            data=data or {},
        )
        self.stage_name = stage_name
        self.pipeline_name = pipeline_name


class ProcessorEvent(Event):
    def __init__(self, processor_name: str, event_type: str, data: Optional[dict] = None):
        import time
        super().__init__(
            source=f"processor:{processor_name}",
            type=event_type,
            timestamp=time.time(),
            data=data or {},
        )
        self.processor_name = processor_name


class ErrorEvent(Event):
    def __init__(self, source: str, error_type: str, message: str, exception: Optional[Exception] = None):
        import time
        super().__init__(
            source=source,
            type="error",
            timestamp=time.time(),
            data={
                "error_type": error_type,
                "message": message,
                "exception": str(exception) if exception else None,
            },
        )


class MetricEvent(Event):
    def __init__(self, metric_name: str, value: float, tags: Optional[dict] = None):
        import time
        super().__init__(
            source="metrics",
            type="metric",
            timestamp=time.time(),
            data={
                "metric_name": metric_name,
                "value": value,
                "tags": tags or {},
            },
        )


class LifecycleEvent(Event):
    def __init__(self, component: str, state: str, data: Optional[dict] = None):
        import time
        super().__init__(
            source=f"lifecycle:{component}",
            type=state,
            timestamp=time.time(),
            data=data or {},
        )
