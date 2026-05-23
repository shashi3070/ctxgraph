from __future__ import annotations

from enum import Enum
from typing import Optional


class ModelMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"

    @classmethod
    def from_str(cls, value: str) -> "ModelMode":
        value = value.lower().strip()
        for mode in cls:
            if mode.value == value:
                return mode
        return cls.BALANCED


MODE_CONFIG = {
    ModelMode.FAST: {
        "description": "Quick responses, minimal analysis (Sonnet-class)",
        "max_nodes": 10,
        "max_depth": 1,
        "summary_length": 100,
    },
    ModelMode.BALANCED: {
        "description": "Balanced speed and depth (default)",
        "max_nodes": 20,
        "max_depth": 2,
        "summary_length": 200,
    },
    ModelMode.DEEP: {
        "description": "Deep analysis, full context (Opus-class)",
        "max_nodes": 40,
        "max_depth": 3,
        "summary_length": 500,
    },
}


def get_mode_config(mode: ModelMode) -> dict:
    return MODE_CONFIG[mode]
