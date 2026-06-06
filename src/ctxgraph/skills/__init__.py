from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

SKILLS_DIRNAME = "skills"
BUILTIN_SKILLS_DIR = Path(__file__).parent


def discover_skills(repo_path: Path) -> dict[str, str]:
    skills_dir = repo_path / ".ctxgraph" / SKILLS_DIRNAME
    if not skills_dir.exists():
        return {}

    skills = {}
    for fname in sorted(os.listdir(str(skills_dir))):
        if fname.endswith((".toml", ".md", ".txt")):
            fpath = skills_dir / fname
            content = fpath.read_text(encoding="utf-8").strip()
            name = fname.rsplit(".", 1)[0]
            skills[name] = content
    return skills


def load_skill(repo_path: Path, name: str) -> Optional[str]:
    skills = discover_skills(repo_path)
    return skills.get(name)


def get_builtin_skills() -> dict[str, str]:
    skills = {}
    for fname in sorted(os.listdir(str(BUILTIN_SKILLS_DIR))):
        if fname.endswith((".toml", ".md", ".txt")) and fname != "__init__.py":
            content = (BUILTIN_SKILLS_DIR / fname).read_text(encoding="utf-8").strip()
            name = fname.rsplit(".", 1)[0]
            skills[name] = content
    return skills
