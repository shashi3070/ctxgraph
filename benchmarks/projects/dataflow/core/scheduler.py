from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from dataflow.core.context import PipelineContext
from dataflow.core.stage import PipelineStage


class Scheduler(ABC):
    @abstractmethod
    def execute(self, stages: list[PipelineStage], context: PipelineContext) -> Any:
        ...


class SequentialScheduler(Scheduler):
    def execute(self, stages: list[PipelineStage], context: PipelineContext) -> Any:
        result = context.data
        for stage in stages:
            result = stage.execute(context)
            context.update(result)
        return result


class ParallelScheduler(Scheduler):
    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers

    def execute(self, stages: list[PipelineStage], context: PipelineContext) -> Any:
        if not stages:
            return context.data

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {}
            for stage in stages:
                stage_ctx = context.copy()
                future = executor.submit(stage.execute, stage_ctx)
                futures[future] = stage

            results = []
            for future in as_completed(futures):
                stage = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    context.add_error(stage.name, f"Parallel execution failed: {exc}")
                    raise

        return results[-1] if results else context.data


class DagScheduler(Scheduler):
    def __init__(self, dependency_map: dict[str, list[str]], max_workers: int = 4):
        self._dependency_map = dependency_map
        self._max_workers = max_workers

    def execute(self, stages: list[PipelineStage], context: PipelineContext) -> Any:
        stage_map = {s.name: s for s in stages}
        executed: set[str] = set()

        while len(executed) < len(stages):
            ready = [
                s for s in stages
                if s.name not in executed
                and all(dep in executed for dep in self._dependency_map.get(s.name, []))
            ]
            if not ready:
                raise RuntimeError("Circular dependency detected or no ready stages")

            for stage in ready:
                result = stage.execute(context)
                context.update(result)
                executed.add(stage.name)

        return context.data
