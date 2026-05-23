"""Configuration loader with environment variable support."""
import os
from src.core.validators import validate_port, validate_url


def load_config(path=None):
    config = {
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8080")),
        "jwt_secret": os.getenv("JWT_SECRET", "dev-secret"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "database_url": os.getenv("DATABASE_URL", "sqlite:///dev.db"),
        "rate_limit": int(os.getenv("RATE_LIMIT", "100")),
    }

    validate_port(config["port"])
    validate_url(config["redis_url"])

    return config
