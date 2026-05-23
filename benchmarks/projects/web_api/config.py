import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Settings:
    """Application configuration sourced from environment variables with sensible defaults."""

    app_name: str = "WebAPI"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")

    jwt_secret: str = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
    jwt_refresh_expiration_days: int = int(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", "7"))

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./web_api.db")

    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    allowed_methods: List[str] = field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH"]
    )

    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    admin_default_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_default_username: str = os.getenv("ADMIN_USERNAME", "admin")


settings = Settings()
