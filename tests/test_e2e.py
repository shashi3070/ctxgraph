import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def project():
    """Create a temporary project with a simple .py file for graph building."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text(
            "from __future__ import annotations\n\ndef greet(name: str) -> str:\n    return f'Hello, {name}'\n\nclass Greeter:\n    def __init__(self, prefix: str = 'Hi'):\n        self.prefix = prefix\n\n    def greet(self, name: str) -> str:\n        return f'{self.prefix}, {name}'\n"
        )
        yield root


class TestE2EInit:
    def test_init_scaffolds_directory(self, project):
        from ctxgraph.config.init import init_project

        result = init_project(project)
        assert (project / ".ctxgraph").exists()
        assert (project / ".ctxgraph" / "config.toml").exists()
        assert (project / ".ctxgraph" / "skills").exists()
        assert (project / ".ctxgraph" / "history.jsonl").exists()

    def test_init_creates_default_skills(self, project):
        from ctxgraph.config.init import init_project

        init_project(project)
        skills = list((project / ".ctxgraph" / "skills").iterdir())
        assert len(skills) > 0
        names = [f.name for f in skills]
        assert any("project-style" in n for n in names)
        assert any("field-guide" in n for n in names)

    def test_init_idempotent(self, project):
        from ctxgraph.config.init import init_project

        init_project(project)
        init_project(project)
        assert (project / ".ctxgraph" / "config.toml").exists()


class TestE2ESkills:
    def test_discover_skills(self, project):
        from ctxgraph.config.init import init_project
        from ctxgraph.skills import discover_skills

        init_project(project)
        skills = discover_skills(project)
        assert len(skills) >= 2
        assert "project-style" in skills
        assert "field-guide" in skills

    def test_load_skill(self, project):
        from ctxgraph.config.init import init_project
        from ctxgraph.skills import load_skill

        init_project(project)
        content = load_skill(project, "project-style")
        assert content is not None
        assert "naming" in content.lower() or "rules" in content

    def test_load_nonexistent_skill(self, project):
        from ctxgraph.skills import load_skill

        assert load_skill(project, "nonexistent") is None

    def test_builtin_skills(self):
        from ctxgraph.skills import get_builtin_skills

        skills = get_builtin_skills()
        assert len(skills) >= 2
        assert "project-style" in skills
        assert "field-guide" in skills

    def test_skill_context_prepend(self):
        from ctxgraph.capsule.renderer import _prepend_skill_context

        dsl = "[CTX]test query\n[F]src/main.py"
        skill_text = "## Test Skill\n\nrule: always use type hints"
        result = _prepend_skill_context(dsl, skill_text)
        assert "## Project Knowledge" in result
        assert skill_text in result
        assert dsl in result


class TestE2EHistory:
    def test_append_and_read(self, project):
        from ctxgraph.history import append_entry, get_entries

        append_entry(project, {"query": "test query", "provider": "ollama"})
        entries = get_entries(project, tail=10)
        assert len(entries) == 1
        assert entries[0]["query"] == "test query"

    def test_entries_have_timestamp(self, project):
        from ctxgraph.history import append_entry, get_entries

        append_entry(project, {"query": "ts test"})
        entry = get_entries(project, tail=1)[0]
        assert "ts" in entry

    def test_multiple_entries(self, project):
        from ctxgraph.history import append_entry, get_entries

        for i in range(5):
            append_entry(project, {"query": f"q{i}", "provider": "ollama"})
        entries = get_entries(project, tail=10)
        assert len(entries) == 5

    def test_tail_limit(self, project):
        from ctxgraph.history import append_entry, get_entries

        for i in range(10):
            append_entry(project, {"query": f"q{i}"})
        entries = get_entries(project, tail=3)
        assert len(entries) == 3

    def test_empty_history(self, project):
        from ctxgraph.history import get_entries

        assert get_entries(project) == []

    def test_history_filter(self, project):
        from ctxgraph.history import append_entry, get_entries

        append_entry(project, {"query": "authentication"})
        append_entry(project, {"query": "database schema"})
        append_entry(project, {"query": "auth middleware"})
        matches = get_entries(project, tail=10, query_filter="auth")
        assert len(matches) == 2
        assert all("auth" in e["query"].lower() for e in matches)

    def test_history_stats_empty(self, project):
        from ctxgraph.history import get_stats

        stats = get_stats(project)
        assert stats["total_queries"] == 0

    def test_history_stats(self, project):
        from ctxgraph.history import append_entry, get_stats

        for i in range(3):
            append_entry(project, {"query": f"q{i}", "provider": "ollama", "savings_pct": 90.0, "raw_tokens": 10000, "capsule_tokens": 1000})
        stats = get_stats(project)
        assert stats["total_queries"] == 3
        assert stats["total_tokens_saved"] > 0
        assert stats["avg_savings_pct"] > 0

    def test_history_stats_with_missing_fields(self, project):
        from ctxgraph.history import append_entry, get_stats

        append_entry(project, {"query": "test"})
        stats = get_stats(project)
        assert stats["total_queries"] == 1
        assert stats["total_tokens_saved"] == 0

    def test_jsonl_format(self, project):
        from ctxgraph.history import append_entry

        append_entry(project, {"query": "format test", "provider": "ollama"})
        lines = (project / ".ctxgraph" / "history.jsonl").read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["query"] == "format test"


class TestE2ESavings:
    def test_compute_savings_returns_dict(self, project):
        from ctxgraph.capsule.savings import compute_savings

        result = compute_savings(project, "[CTX]test capsule")
        assert isinstance(result, dict)
        assert "raw_tokens" in result
        assert "capsule_tokens" in result
        assert "json_tokens" in result
        assert "savings_pct" in result
        assert "dsl_vs_json" in result

    def test_savings_capsule_smaller_than_raw(self, project):
        from ctxgraph.capsule.savings import compute_savings

        result = compute_savings(project, "[CTX]small capsule")
        assert result["capsule_tokens"] < result["raw_tokens"]
        assert result["savings_pct"] > 0

    def test_savings_empty_project(self, project):
        from ctxgraph.capsule.savings import _collect_project_py_files

        content = _collect_project_py_files(project)
        assert len(content) > 0

    def test_render_savings_table(self, project):
        from ctxgraph.capsule.savings import compute_savings, render_savings_table

        savings = compute_savings(project, "[CTX]test")
        output = render_savings_table(savings)
        assert "Token Savings" in output
        assert "tokens" in output
        assert "%" in output

    def test_savings_dsl_vs_json(self, project):
        from ctxgraph.capsule.savings import compute_savings

        result = compute_savings(project, "[CTX]test capsule content " * 10)
        assert result["dsl_vs_json"] >= 0

    def test_savings_no_py_files(self):
        from ctxgraph.capsule.savings import compute_savings

        with tempfile.TemporaryDirectory() as tmp:
            result = compute_savings(Path(tmp), "[CTX]test")
            assert result["savings_pct"] == 0.0
