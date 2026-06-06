from __future__ import annotations

from pathlib import Path

from ctxgraph.config.settings import create_default_config
from ctxgraph.skills import get_builtin_skills


def init_project(repo_path: Path) -> Path:
    cfg_dir = repo_path / ".ctxgraph"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    create_default_config(repo_path)

    skills_dir = cfg_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    builtins = get_builtin_skills()
    for name, content in builtins.items():
        skill_path = skills_dir / f"{name}.toml"
        if not skill_path.exists():
            skill_path.write_text(content, encoding="utf-8")

    (cfg_dir / "history.jsonl").touch(exist_ok=True)

    return cfg_dir
