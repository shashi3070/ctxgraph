import json
import tempfile
from pathlib import Path

import pytest
from dataflow.config.settings import PipelineConfig, ConfigLoader
from dataflow.config.schema import ConfigSchema, FieldSchema, ConfigValidationError


class TestPipelineConfig:
    def test_default_values(self):
        config = PipelineConfig()
        assert config.name == "default_pipeline"
        assert config.max_stages == 50
        assert config.retry_count == 3
        assert config.error_policy == "fail_fast"

    def test_from_dict(self):
        config = PipelineConfig.from_dict({"name": "my_pipe", "max_stages": 10, "log_level": "DEBUG"})
        assert config.name == "my_pipe"
        assert config.max_stages == 10
        assert config.log_level == "DEBUG"

    def test_to_dict(self):
        config = PipelineConfig(name="test")
        d = config.to_dict()
        assert d["name"] == "test"
        assert d["retry_count"] == 3


class TestConfigLoader:
    def test_load_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"name": "json_pipe", "max_stages": 5}))
            loader = ConfigLoader()
            config = loader.load(path)
            assert config.name == "json_pipe"
            assert config.max_stages == 5

    def test_load_file_not_found(self):
        loader = ConfigLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(Path("/nonexistent/config.json"))


class TestConfigSchema:
    def test_validation_passes(self):
        schema = ConfigSchema([
            FieldSchema("name", str, required=True),
            FieldSchema("max_stages", int, default=50, min_value=1, max_value=100),
        ])
        errors = schema.validate({"name": "test", "max_stages": 10})
        assert len(errors) == 0

    def test_validation_fails_required(self):
        schema = ConfigSchema([
            FieldSchema("name", str, required=True),
        ])
        errors = schema.validate({})
        assert any("required" in e for e in errors)

    def test_validation_fails_type(self):
        schema = ConfigSchema([
            FieldSchema("max_stages", int, required=True),
        ])
        errors = schema.validate({"max_stages": "not_int"})
        assert any("should be" in e for e in errors)

    def test_validation_fails_unknown_field(self):
        schema = ConfigSchema([])
        errors = schema.validate({"unknown_key": 123})
        assert any("Unknown" in e for e in errors)

    def test_coerce_values(self):
        schema = ConfigSchema([
            FieldSchema("count", int, default=0),
        ])
        result = schema.coerce({"count": "42"})
        assert result["count"] == 42

    def test_choices_validation(self):
        schema = ConfigSchema([
            FieldSchema("mode", str, choices=["fast", "balanced", "deep"]),
        ])
        errors = schema.validate({"mode": "invalid"})
        assert any("must be one of" in e for e in errors)
        errors = schema.validate({"mode": "fast"})
        assert len(errors) == 0
