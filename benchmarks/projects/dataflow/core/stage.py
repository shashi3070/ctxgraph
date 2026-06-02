from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from dataflow.core.context import PipelineContext


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PipelineStage(ABC):
    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description or ""
        self._status: StageStatus = StageStatus.PENDING

    @property
    def status(self) -> StageStatus:
        return self._status

    @abstractmethod
    def process(self, context: PipelineContext) -> Any:
        ...

    def execute(self, context: PipelineContext) -> Any:
        self._status = StageStatus.RUNNING
        try:
            result = self.process(context)
            self._status = StageStatus.COMPLETED
            return result
        except Exception:
            self._status = StageStatus.FAILED
            raise

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "status": self._status.value,
            "description": self.description,
        }


class ConditionalStage(PipelineStage):
    def __init__(self, name: str, condition_func, description: Optional[str] = None):
        super().__init__(name, description)
        self._condition = condition_func
        self._if_branch: Optional[PipelineStage] = None
        self._else_branch: Optional[PipelineStage] = None

    def add_branch(self, if_stage: PipelineStage, else_stage: Optional[PipelineStage] = None) -> ConditionalStage:
        self._if_branch = if_stage
        self._else_branch = else_stage
        return self

    def process(self, context: PipelineContext) -> Any:
        if self._condition(context):
            if self._if_branch:
                return self._if_branch.execute(context)
        else:
            if self._else_branch:
                return self._else_branch.execute(context)
        return context.data


class LoopStage(PipelineStage):
    def __init__(self, name: str, inner_stage: PipelineStage, max_iterations: int = 100, description: Optional[str] = None):
        super().__init__(name, description)
        self._inner = inner_stage
        self._max_iterations = max_iterations
        self._iteration_count = 0

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    def process(self, context: PipelineContext) -> Any:
        result = context.data
        for i in range(self._max_iterations):
            self._iteration_count = i + 1
            iter_ctx = context.copy()
            iter_ctx.set_metadata("iteration", i)
            result = self._inner.execute(iter_ctx)
            if result is None:
                break
            context.update(result)
        return result
