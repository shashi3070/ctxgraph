import pytest
from ctxgraph.clients.models import ModelMode, get_mode_config


class TestModelMode:
    def test_from_str_valid(self):
        assert ModelMode.from_str("fast") == ModelMode.FAST
        assert ModelMode.from_str("balanced") == ModelMode.BALANCED
        assert ModelMode.from_str("deep") == ModelMode.DEEP

    def test_from_str_case_insensitive(self):
        assert ModelMode.from_str("FAST") == ModelMode.FAST
        assert ModelMode.from_str("Balanced") == ModelMode.BALANCED

    def test_from_str_default(self):
        assert ModelMode.from_str("invalid") == ModelMode.BALANCED

    def test_fast_config(self):
        cfg = get_mode_config(ModelMode.FAST)
        assert cfg["max_nodes"] == 10
        assert cfg["max_depth"] == 1

    def test_balanced_config(self):
        cfg = get_mode_config(ModelMode.BALANCED)
        assert cfg["max_nodes"] == 20
        assert cfg["max_depth"] == 2

    def test_deep_config(self):
        cfg = get_mode_config(ModelMode.DEEP)
        assert cfg["max_nodes"] == 40
        assert cfg["max_depth"] == 3
