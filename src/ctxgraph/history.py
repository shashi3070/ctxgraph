from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def _history_path(repo_path: Path) -> Path:
    return repo_path / ".ctxgraph" / "history.jsonl"


def append_entry(repo_path: Path, entry: dict):
    path = _history_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry["ts"] = datetime.utcnow().isoformat()
    with open(str(path), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def get_entries(
    repo_path: Path,
    tail: int = 10,
    query_filter: Optional[str] = None,
) -> list[dict]:
    path = _history_path(repo_path)
    if not path.exists():
        return []

    entries = []
    with open(str(path), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if query_filter and query_filter.lower() not in entry.get("query", "").lower():
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    return entries[-tail:] if tail else entries


def get_stats(repo_path: Path) -> dict:
    entries = get_entries(repo_path, tail=None)
    total = len(entries)
    if total == 0:
        return {"total_queries": 0, "total_tokens_saved": 0, "avg_savings_pct": 0.0}

    total_saved = sum(e.get("savings_pct", 0) * e.get("raw_tokens", 0) / 100 for e in entries if e.get("raw_tokens"))
    total_raw = sum(e.get("raw_tokens", 0) for e in entries)
    avg_savings = (sum(e.get("savings_pct", 0) for e in entries if e.get("savings_pct")) / max(sum(1 for e in entries if e.get("savings_pct")), 1))

    providers = {}
    for e in entries:
        p = e.get("provider", "unknown")
        providers[p] = providers.get(p, 0) + 1

    return {
        "total_queries": total,
        "total_tokens_saved": int(total_saved),
        "total_raw_tokens": total_raw,
        "avg_savings_pct": round(avg_savings, 1),
        "providers": providers,
    }
