from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class Processor(ABC):
    def __init__(self, name: str, config: Optional[dict] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        ...

    def validate_config(self) -> list[str]:
        return []

    def close(self) -> None:
        pass


class ProcessorRegistry:
    _processors: dict[str, type[Processor]] = {}

    @classmethod
    def register(cls, name: str, processor_cls: type[Processor]) -> None:
        cls._processors[name] = processor_cls

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._processors.pop(name, None)

    @classmethod
    def get(cls, name: str) -> Optional[type[Processor]]:
        return cls._processors.get(name)

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._processors.keys())

    @classmethod
    def create(cls, name: str, instance_name: str, config: Optional[dict] = None) -> Processor:
        processor_cls = cls.get(name)
        if processor_cls is None:
            raise ValueError(f"Unknown processor: {name}")
        return processor_cls(instance_name, config)

    @classmethod
    def discover_plugins(cls, package: str = "dataflow.plugins") -> int:
        import importlib
        import pkgutil
        count = 0
        plugin_pkg = importlib.import_module(package)
        for importer, modname, ispkg in pkgutil.iter_modules(plugin_pkg.__path__):
            importlib.import_module(f"{package}.{modname}")
            count += 1
        return count
