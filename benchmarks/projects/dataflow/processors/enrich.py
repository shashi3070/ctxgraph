from __future__ import annotations

from typing import Any, Callable, Optional

from dataflow.processors.base import Processor


class EnrichProcessor(Processor):
    def __init__(self, name: str, enrich_fn: Callable, config: Optional[dict] = None):
        super().__init__(name, config)
        self._enrich_fn = enrich_fn

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        return self._enrich_fn(data, context or {})


class LookupEnricher(Processor):
    def __init__(self, name: str, lookup_data: dict, key_field: str = "id", target_field: str = "enriched", config: Optional[dict] = None):
        super().__init__(name, config)
        self._lookup = lookup_data
        self._key_field = key_field
        self._target_field = target_field

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if isinstance(data, list):
            for item in data:
                self._enrich_item(item)
        else:
            self._enrich_item(data)
        return data

    def _enrich_item(self, item: dict) -> None:
        if not isinstance(item, dict):
            return
        key = item.get(self._key_field)
        if key is not None and key in self._lookup:
            item[self._target_field] = self._lookup[key]


class CacheEnricher(EnrichProcessor):
    def __init__(self, name: str, cache_size: int = 100, config: Optional[dict] = None):
        super().__init__(name, lambda d, c: d, config)
        self._cache: dict = {}
        self._cache_size = cache_size

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if isinstance(data, dict) and "id" in data:
            data_id = data["id"]
            if data_id in self._cache:
                return self._cache[data_id]
            result = super().process(data, context)
            if len(self._cache) < self._cache_size:
                self._cache[data_id] = result
            return result
        return super().process(data, context)
