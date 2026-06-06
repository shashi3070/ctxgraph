from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table


def _rough_token_count(text: str) -> int:
    return max(1, len(text) // 4)


def _collect_project_py_files(repo_path: Path) -> str:
    py_files = list(repo_path.rglob("*.py"))
    excluded_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", ".ctxgraph", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache"}
    content_parts = []
    for f in py_files:
        rel = f.relative_to(repo_path)
        if any(p.name in excluded_dirs or (str(p) in str(rel)) for p in f.parents):
            continue
        try:
            text = f.read_text(encoding="utf-8")
            content_parts.append(f"# {rel}\n{text}")
        except Exception:
            continue
    return "\n\n".join(content_parts)


def _capsule_dsl_token_estimate(capsule_text: str) -> int:
    return _rough_token_count(capsule_text)


def _json_token_estimate(capsule_text: str) -> int:
    import json
    return _rough_token_count(json.dumps(capsule_text))


def compute_savings(repo_path: Path, capsule_text: str) -> dict:
    raw_source = _collect_project_py_files(repo_path)
    raw_tokens = _rough_token_count(raw_source) if raw_source else 0
    capsule_tokens = _capsule_dsl_token_estimate(capsule_text)
    json_tokens = _json_token_estimate(capsule_text)

    if raw_tokens > 0:
        savings_pct = round((1 - capsule_tokens / raw_tokens) * 100, 1)
    else:
        savings_pct = 0.0

    if json_tokens > 0:
        dsl_vs_json_pct = round((1 - capsule_tokens / json_tokens) * 100, 1)
        dsl_as_pct_of_json = round(capsule_tokens / json_tokens * 100, 1)
    else:
        dsl_vs_json_pct = 0.0
        dsl_as_pct_of_json = 0.0

    return {
        "raw_tokens": raw_tokens,
        "capsule_tokens": capsule_tokens,
        "json_tokens": json_tokens,
        "savings_pct": savings_pct,
        "dsl_vs_json_pct": dsl_vs_json_pct,
        "dsl_as_pct_of_json": dsl_as_pct_of_json,
    }


def render_savings_table(savings: dict) -> str:
    saved = savings['raw_tokens'] - savings['capsule_tokens']
    ratio = f"{savings['savings_pct']}%"
    bar_len = 20
    filled = int(savings['savings_pct'] / 100 * bar_len) if savings['savings_pct'] > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    table = Table(title=f"Token Savings  {bar}  {ratio}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Raw .py files", f"{savings['raw_tokens']:>10,} tokens")
    table.add_row("Capsule DSL", f"{savings['capsule_tokens']:>10,} tokens")
    table.add_row("JSON equivalent", f"{savings['json_tokens']:>10,} tokens")
    table.add_row("", "")
    table.add_row("Tokens saved", f"{saved:>10,}")
    table.add_row("Savings vs raw", f"{savings['savings_pct']:>9}%")
    dsl_ratio = f"DSL is {savings['dsl_as_pct_of_json']}% of JSON"
    if abs(savings['dsl_vs_json_pct']) < 10:
        table.add_row("DSL vs JSON", f"{dsl_ratio:>20}")
    else:
        table.add_row("DSL vs JSON", f"{savings['dsl_vs_json_pct']:>9}% more efficient")

    console = Console()
    with console.capture() as capture:
        console.print(table)
    return capture.get()
