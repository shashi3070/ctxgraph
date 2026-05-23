import os
import tempfile
from pathlib import Path

import pytest

from ctxgraph.config.settings import PROVIDER_CONFIGS, Settings, create_default_config


class TestSettings:
    def test_default_values(self):
        s = Settings()
        assert s.provider == "ollama"
        assert s.model == "qwen2.5-coder:7b"
        assert s.endpoint == "http://localhost:11434"
        assert s.context_mode == "balanced"

    def test_toml_config_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / ".ctxgraph"
            config_dir.mkdir()
            config_path = config_dir / "config.toml"
            config_path.write_text(
                '[ai]\nprovider = "claude"\nmodel = "claude-sonnet-4-20250514"\n'
            )
            s = Settings(Path(tmp))
            assert s.provider == "claude"
            assert s.model == "claude-sonnet-4-20250514"

    def test_json_config_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / ".ctxgraph"
            config_dir.mkdir()
            config_path = config_dir / "config.json"
            config_path.write_text(
                '{"ai": {"provider": "openai", "model": "gpt-4o"}}'
            )
            s = Settings(Path(tmp))
            assert s.provider == "openai"
            assert s.model == "gpt-4o"

    def test_env_overrides(self):
        old_provider = os.environ.get("CTXGRAPH_PROVIDER")
        old_model = os.environ.get("CTXGRAPH_MODEL")
        os.environ["CTXGRAPH_PROVIDER"] = "openai"
        os.environ["CTXGRAPH_MODEL"] = "gpt-4o-mini"
        try:
            s = Settings()
            assert s.provider == "openai"
            assert s.model == "gpt-4o-mini"
        finally:
            if old_provider:
                os.environ["CTXGRAPH_PROVIDER"] = old_provider
            else:
                del os.environ["CTXGRAPH_PROVIDER"]
            if old_model:
                os.environ["CTXGRAPH_MODEL"] = old_model
            else:
                del os.environ["CTXGRAPH_MODEL"]

    def test_provider_configs(self):
        assert "ollama" in PROVIDER_CONFIGS
        assert "claude" in PROVIDER_CONFIGS
        assert "openai" in PROVIDER_CONFIGS
        assert "custom" in PROVIDER_CONFIGS
        assert PROVIDER_CONFIGS["ollama"]["api_key_required"] is False
        assert PROVIDER_CONFIGS["claude"]["api_key_required"] is True

    def test_create_default_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            config_path = create_default_config(path)
            assert config_path.exists()
            content = config_path.read_text()
            assert "[ai]" in content
            assert "provider = " in content

    def test_exclude_patterns(self):
        config_path = Path(tmp_path) if "tmp_path" in dir() else Path(".")
        s = Settings()
        assert isinstance(s.exclude_patterns, list)

    def test_get_chat_url_ollama(self):
        s = Settings()
        url = s.get_chat_url()
        assert "ollama" in url or "localhost:11434" in url or "/api/chat" in url
