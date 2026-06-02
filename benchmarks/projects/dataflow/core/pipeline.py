from __future__ import annotations

from typing import Any, Optional

from dataflow.core.context import PipelineContext
from dataflow.core.stage import PipelineStage, StageStatus
from dataflow.core.scheduler import Scheduler, SequentialScheduler
from dataflow.events.bus import EventBus
from dataflow.events.types import PipelineEvent
from dataflow.metrics.collector import MetricsCollector


class Pipeline:
    def __init__(
        self,
        name: str,
        stages: list[PipelineStage],
        scheduler: Optional[Scheduler] = None,
        event_bus: Optional[EventBus] = None,
        metrics: Optional[MetricsCollector] = None,
    ):
        self.name = name
        self._stages = stages
        self._scheduler = scheduler or SequentialScheduler()
        self._event_bus = event_bus or EventBus()
        self._metrics = metrics or MetricsCollector()
        self._context: Optional[PipelineContext] = None
        self._status: StageStatus = StageStatus.PENDING

    @property
    def status(self) -> StageStatus:
        return self._status

    @property
    def stages(self) -> list[PipelineStage]:
        return list(self._stages)

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    def add_stage(self, stage: PipelineStage) -> Pipeline:
        self._stages.append(stage)
        return self

    def remove_stage(self, stage: PipelineStage) -> Pipeline:
        self._stages.remove(stage)
        return self

    def insert_stage_after(self, target: PipelineStage, new_stage: PipelineStage) -> Pipeline:
        idx = self._stages.index(target)
        self._stages.insert(idx + 1, new_stage)
        return self

    def insert_stage_before(self, target: PipelineStage, new_stage: PipelineStage) -> Pipeline:
        idx = self._stages.index(target)
        self._stages.insert(idx, new_stage)
        return self

    def run(self, data: Any = None) -> Any:
        self._status = StageStatus.RUNNING
        self._context = PipelineContext(data)
        self._event_bus.emit(PipelineEvent(self.name, "started", {"status": "begin"}))
        try:
            result = self._scheduler.execute(self._stages, self._context)
            self._status = StageStatus.COMPLETED
            self._metrics.record_success(self.name)
            self._event_bus.emit(PipelineEvent(self.name, "completed", {"result": "success"}))
            return result
        except Exception as exc:
            self._status = StageStatus.FAILED
            self._metrics.record_failure(self.name)
            self._event_bus.emit(PipelineEvent(self.name, "failed", {"error": str(exc)}))
            raise

    def get_stage_by_name(self, name: str) -> Optional[PipelineStage]:
        for stage in self._stages:
            if stage.name == name:
                return stage
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self._status.value,
            "stages": [s.to_dict() for s in self._stages],
            "metrics": self._metrics.to_dict(),
        }


class PipelineBuilder:
    def __init__(self, name: str = "default"):
        self._name = name
        self._stages: list[PipelineStage] = []
        self._scheduler: Optional[Scheduler] = None
        self._event_bus: Optional[EventBus] = None
        self._metrics: Optional[MetricsCollector] = None

    def with_stage(self, stage: PipelineStage) -> PipelineBuilder:
        self._stages.append(stage)
        return self

    def with_scheduler(self, scheduler: Scheduler) -> PipelineBuilder:
        self._scheduler = scheduler
        return self

    def with_event_bus(self, bus: EventBus) -> PipelineBuilder:
        self._event_bus = bus
        return self

    def with_metrics(self, metrics: MetricsCollector) -> PipelineBuilder:
        self._metrics = metrics
        return self

    def build(self) -> Pipeline:
        return Pipeline(
            name=self._name,
            stages=self._stages,
            scheduler=self._scheduler,
            event_bus=self._event_bus,
            metrics=self._metrics,
        )
