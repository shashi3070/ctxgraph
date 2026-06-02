from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional

from dataflow.core.context import PipelineContext
from dataflow.core.stage import PipelineStage


class StageExecutor(ABC):
    @abstractmethod
    def execute_stage(self, stage: PipelineStage, context: PipelineContext) -> Any:
        ...


class SyncStageExecutor(StageExecutor):
    def execute_stage(self, stage: PipelineStage, context: PipelineContext) -> Any:
        return stage.execute(context)


class AsyncStageExecutor(StageExecutor):
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self._loop = loop or asyncio.new_event_loop()

    def execute_stage(self, stage: PipelineStage, context: PipelineContext) -> Any:
        async def _run():
            return stage.execute(context)
        return self._loop.run_until_complete(_run())

    def close(self):
        self._loop.close()


class RetryExecutor(StageExecutor):
    def __init__(self, inner: StageExecutor, max_retries: int = 3, delay: float = 1.0):
        self._inner = inner
        self._max_retries = max_retries
        self._delay = delay

    def execute_stage(self, stage: PipelineStage, context: PipelineContext) -> Any:
        import time
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                return self._inner.execute_stage(stage, context)
            except Exception as exc:
                last_exc = exc
                context.add_error(stage.name, f"Attempt {attempt + 1} failed", exc)
                if attempt < self._max_retries - 1:
                    time.sleep(self._delay * (attempt + 1))
        raise last_exc  # type: ignore


class TimeoutExecutor(StageExecutor):
    def __init__(self, inner: StageExecutor, timeout: float = 30.0):
        self._inner = inner
        self._timeout = timeout

    def execute_stage(self, stage: PipelineStage, context: PipelineContext) -> Any:
        import signal

        def _handler(signum, frame):
            raise TimeoutError(f"Stage '{stage.name}' timed out after {self._timeout}s")

        signal.signal(signal.SIGALRM, _handler)
        signal.alarm(int(self._timeout))
        try:
            return self._inner.execute_stage(stage, context)
        finally:
            signal.alarm(0)
