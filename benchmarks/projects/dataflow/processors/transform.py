from __future__ import annotations

from typing import Any, Callable, Optional

from dataflow.processors.base import Processor


class TransformProcessor(Processor):
    def __init__(self, name: str, transform_fn: Optional[Callable] = None, config: Optional[dict] = None):
        super().__init__(name, config)
        self._transform_fn = transform_fn

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if self._transform_fn:
            return self._transform_fn(data, context or {})
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in self.config.get("exclude_keys", [])}
        return data

    def chain(self, next_processor: Processor) -> ChainedProcessor:
        return ChainedProcessor(f"{self.name}_chain", [self, next_processor])


class MapProcessor(Processor):
    def __init__(self, name: str, mapping_fn: Callable, config: Optional[dict] = None):
        super().__init__(name, config)
        self._mapping_fn = mapping_fn

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if isinstance(data, list):
            return [self._mapping_fn(item, context or {}) for item in data]
        return self._mapping_fn(data, context or {})


class FilterProcessor(Processor):
    def __init__(self, name: str, predicate: Callable, config: Optional[dict] = None):
        super().__init__(name, config)
        self._predicate = predicate

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if isinstance(data, list):
            return [item for item in data if self._predicate(item, context or {})]
        return data if self._predicate(data, context or {}) else None


class FlatMapProcessor(Processor):
    def __init__(self, name: str, flat_fn: Callable, config: Optional[dict] = None):
        super().__init__(name, config)
        self._flat_fn = flat_fn

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        items = data if isinstance(data, list) else [data]
        result = []
        for item in items:
            mapped = self._flat_fn(item, context or {})
            if isinstance(mapped, list):
                result.extend(mapped)
            else:
                result.append(mapped)
        return result


class ChainedProcessor(Processor):
    def __init__(self, name: str, processors: list[Processor], config: Optional[dict] = None):
        super().__init__(name, config)
        self._processors = processors

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        result = data
        for processor in self._processors:
            result = processor.process(result, context)
        return result

    def add(self, processor: Processor) -> ChainedProcessor:
        self._processors.append(processor)
        return self
