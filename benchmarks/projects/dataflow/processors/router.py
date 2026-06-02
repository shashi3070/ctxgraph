from __future__ import annotations

import itertools
from typing import Any, Callable, Optional

from dataflow.processors.base import Processor


class RouterProcessor(Processor):
    def __init__(self, name: str, routes: dict[str, Processor], config: Optional[dict] = None):
        super().__init__(name, config)
        self._routes = routes

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        route_key = self.resolve_route(data, context or {})
        processor = self._routes.get(route_key)
        if processor:
            return processor.process(data, context)
        return data

    def resolve_route(self, data: Any, context: dict) -> str:
        raise NotImplementedError


class ConditionalRouter(RouterProcessor):
    def __init__(self, name: str, routes: dict[str, Processor], condition_fn: Callable, config: Optional[dict] = None):
        super().__init__(name, routes, config)
        self._condition_fn = condition_fn

    def resolve_route(self, data: Any, context: dict) -> str:
        return str(self._condition_fn(data, context))


class RoundRobinRouter(RouterProcessor):
    def __init__(self, name: str, routes: dict[str, Processor], config: Optional[dict] = None):
        super().__init__(name, routes, config)
        self._counter = itertools.cycle(range(len(routes)))

    def resolve_route(self, data: Any, context: dict) -> str:
        idx = next(self._counter)
        return list(self._routes.keys())[idx]
