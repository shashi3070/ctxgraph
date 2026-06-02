from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dataflow.config.schema import ConfigSchema, ConfigValidationError


@dataclass
class PipelineConfig:
    name: str = "default_pipeline"
    max_stages: int = 50
    timeout_seconds: float = 300.0
    retry_count: int = 3
    retry_delay: float = 1.0
    parallel_execution: bool = False
    max_workers: int = 4
    enable_metrics: bool = True
    enable_events: bool = True
    log_level: str = "INFO"
    error_policy: str = "fail_fast"
    checkpoint_enabled: bool = False
    checkpoint_dir: Optional[str] = None
    plugins: list[str] = field(default_factory=list)
    env_overrides: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @classmethod
    def from_dict(cls, data: dict) -> PipelineConfig:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class ConfigLoader:
    def __init__(self, schema: Optional[ConfigSchema] = None):
        self._schema = schema

    def load(self, path: Path) -> PipelineConfig:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(text)
        elif path.suffix == ".yaml":
            import yaml
            data = yaml.safe_load(text)
        elif path.suffix == ".toml":
            import tomllib
            data = tomllib.loads(text)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
        return self._validate_and_create(data)

    def load_from_env(self, prefix: str = "DATAFLOW_") -> PipelineConfig:
        data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                data[config_key] = value
        return self._validate_and_create(data)

    def _validate_and_create(self, data: dict) -> PipelineConfig:
        if self._schema:
            errors = self._schema.validate(data)
            if errors:
                raise ConfigValidationError(errors)
        return PipelineConfig.from_dict(data)


class YamlConfigLoader(ConfigLoader):
    def load(self, path: Path) -> PipelineConfig:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        import yaml
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return self._validate_and_create(data)
