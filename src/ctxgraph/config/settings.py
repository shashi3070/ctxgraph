from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG = {
    "graph": {
        "exclude": [],
        "follow_symlinks": False,
        "max_file_size_mb": 5,
    },
    "ai": {
        "provider": "ollama",
        "model": "qwen2.5-coder:7b",
        "endpoint": "http://localhost:11434",
        "api_key": None,
        "temperature": 0.1,
        "max_tokens": 4096,
    },
    "context": {
        "mode": "balanced",
        "max_nodes": 20,
        "max_depth": 2,
        "max_tokens": 4000,
    },
}

PROVIDER_CONFIGS = {
    "ollama": {
        "endpoint_default": "http://localhost:11434",
        "api_key_required": False,
        "models": ["qwen2.5-coder:7b", "llama3.2", "llama3.1", "mistral", "codellama", "deepseek-coder"],
        "chat_endpoint": "/api/chat",
        "generate_endpoint": "/api/generate",
    },
    "claude": {
        "endpoint_default": "https://api.anthropic.com/v1",
        "api_key_required": True,
        "models": ["claude-sonnet-4-20250514", "claude-haiku-3-5-20241022"],
        "chat_endpoint": "/messages",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "endpoint_default": "https://api.openai.com/v1",
        "api_key_required": True,
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
        "chat_endpoint": "/chat/completions",
        "api_key_env": "OPENAI_API_KEY",
    },
    "custom": {
        "endpoint_default": None,
        "api_key_required": False,
        "models": [],
        "chat_endpoint": "/v1/chat/completions",
        "api_key_env": None,
    },
}


class Settings:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve() if repo_path else Path.cwd()
        self._data = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        config_paths = [
            self.repo_path / ".ctxgraph" / "config.toml",
            self.repo_path / ".ctxgraph" / "config.json",
            self.repo_path / "ctxgraph.toml",
            self.repo_path / "ctxgraph.json",
        ]

        for path in config_paths:
            if path.exists():
                self._load_file(path)
                break

        self._apply_env_overrides()

    def _load_file(self, path: Path):
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            parsed = json.loads(text)
            self._deep_merge(self._data, parsed)
        elif path.suffix == ".toml":
            parsed = self._parse_toml(text)
            self._deep_merge(self._data, parsed)

    def _apply_env_overrides(self):
        provider = self._data["ai"]["provider"]
        pconfig = PROVIDER_CONFIGS.get(provider, {})

        api_key_env = pconfig.get("api_key_env")
        if api_key_env:
            env_key = os.environ.get(api_key_env)
            if env_key:
                self._data["ai"]["api_key"] = env_key

        env_endpoint = os.environ.get("CTXGRAPH_ENDPOINT")
        if env_endpoint:
            self._data["ai"]["endpoint"] = env_endpoint

        env_model = os.environ.get("CTXGRAPH_MODEL")
        if env_model:
            self._data["ai"]["model"] = env_model

        env_provider = os.environ.get("CTXGRAPH_PROVIDER")
        if env_provider:
            self._data["ai"]["provider"] = env_provider

    @property
    def provider(self) -> str:
        return self._data["ai"]["provider"]

    @property
    def model(self) -> str:
        return self._data["ai"]["model"]

    @property
    def endpoint(self) -> str:
        return self._data["ai"]["endpoint"]

    @property
    def api_key(self) -> Optional[str]:
        return self._data["ai"].get("api_key")

    @property
    def temperature(self) -> float:
        return self._data["ai"].get("temperature", 0.1)

    @property
    def max_tokens(self) -> int:
        return self._data["ai"].get("max_tokens", 4096)

    @property
    def exclude_patterns(self) -> list[str]:
        return self._data["graph"].get("exclude", [])

    @property
    def context_mode(self) -> str:
        return self._data["context"].get("mode", "balanced")

    @property
    def max_nodes(self) -> int:
        return self._data["context"].get("max_nodes", 20)

    @property
    def max_depth(self) -> int:
        return self._data["context"].get("max_depth", 2)

    def get_provider_config(self) -> dict:
        return PROVIDER_CONFIGS.get(self.provider, PROVIDER_CONFIGS["custom"])

    def get_chat_url(self) -> str:
        pconfig = self.get_provider_config()
        endpoint = self.endpoint.rstrip("/")
        return f"{endpoint}{pconfig.get('chat_endpoint', '/v1/chat/completions')}"

    def to_dict(self) -> dict:
        return dict(self._data)

    @staticmethod
    def _parse_toml(text: str) -> dict:
        result = {}
        current_section = result

        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section_name = line[1:-1].strip()
                current_section = result.setdefault(section_name, {})
            elif "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                value = value.strip('"').strip("'")
                current_section[key] = value

        return result

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Settings._deep_merge(base[key], value)
            else:
                base[key] = value


def create_default_config(repo_path: Path):
    config_dir = repo_path / ".ctxgraph"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"
    if config_path.exists():
        return

    config_path.write_text(
        """# ctxgraph configuration
# https://github.com/anomalyco/ctxgraph

[graph]
# Additional exclude patterns (gitignore is used automatically)
exclude = []

[ai]
# Provider: ollama, claude, openai, or custom
provider = "ollama"
# Model name
model = "qwen2.5-coder:7b"
# API endpoint
endpoint = "http://localhost:11434"
# API key (or set env var: ANTHROPIC_API_KEY, OPENAI_API_KEY)
api_key = ""

[context]
# Mode: fast, balanced, deep
mode = "balanced"
# Max nodes to include in context capsule
max_nodes = 20
# Max BFS depth for dependency traversal
max_depth = 2
""",
        encoding="utf-8",
    )
    return config_path
