from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Config:
    debug: bool = False
    environment: str = "development"
    database_url: str = "sqlite:///app.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "default-secret-key"
    api_keys: Dict[str, str] = field(default_factory=dict)


_config_instance: Optional[Config] = None


def load_config() -> Config:
    return Config(
        debug=os.getenv("APP_DEBUG", "false").lower() == "true",
        environment=os.getenv("APP_ENVIRONMENT", "development"),
        database_url=os.getenv("APP_DATABASE_URL", "sqlite:///app.db"),
        redis_url=os.getenv("APP_REDIS_URL", "redis://localhost:6379/0"),
        secret_key=os.getenv("APP_SECRET_KEY", "default-secret-key"),
        api_keys={},
    )


def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance
