from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.live import Live

_console = Console()

def _chats_dir(repo_path: Path) -> Path:
    return repo_path / ".ctxgraph" / "chats"


def _session_path(repo_path: Path, session_id: str) -> Path:
    return _chats_dir(repo_path) / f"{session_id}.jsonl"


def _rough_token_count(text: str) -> int:
    return max(1, len(text) // 4)


def list_sessions(repo_path: Path) -> list[dict]:
    d = _chats_dir(repo_path)
    if not d.exists():
        return []
    sessions = []
    for f in sorted(d.iterdir()):
        if f.suffix == ".jsonl":
            lines = f.read_text(encoding="utf-8").strip().split("\n")
            first = json.loads(lines[0]) if lines else {}
            last = json.loads(lines[-1]) if lines else {}
            token_count = sum(_rough_token_count(line) for line in lines)
            sessions.append({
                "id": f.stem,
                "created": first.get("ts", ""),
                "last_message": last.get("content", "")[:60] if last.get("role") == "user" else "",
                "turns": len(lines),
                "tokens": token_count,
            })
    sessions.sort(key=lambda s: s["created"], reverse=True)
    return sessions


def create_session(repo_path: Path) -> str:
    _chats_dir(repo_path).mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())[:8]
    return session_id


def load_session(repo_path: Path, session_id: str) -> list[dict]:
    p = _session_path(repo_path, session_id)
    if not p.exists():
        return []
    messages = []
    with open(str(p), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                messages.append(json.loads(line))
    return messages


def append_message(repo_path: Path, session_id: str, role: str, content: str, metadata: Optional[dict] = None):
    p = _session_path(repo_path, session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "role": role,
        "content": content,
        "ts": datetime.utcnow().isoformat(),
    }
    if metadata:
        entry["metadata"] = metadata
    with open(str(p), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def session_token_count(repo_path: Path, session_id: str) -> int:
    messages = load_session(repo_path, session_id)
    total = sum(_rough_token_count(m.get("content", "")) for m in messages)
    for m in messages:
        mc = m.get("metadata", {}) or {}
        total += mc.get("capsule_tokens", 0)
    return total


def compact_session(repo_path: Path, session_id: str) -> str:
    messages = load_session(repo_path, session_id)
    if len(messages) <= 2:
        return ""

    summary_parts = []
    for m in messages[:-2]:
        role = m.get("role", "?")
        content = m.get("content", "")
        if len(content) > 500:
            content = content[:500] + "..."
        summary_parts.append(f"[{role}]: {content}")

    summary = "\n".join(summary_parts)
    trimmed = messages[-2:]
    p = _session_path(repo_path, session_id)
    p.write_text("", encoding="utf-8")
    for m in trimmed:
        with open(str(p), "a", encoding="utf-8") as f:
            f.write(json.dumps(m, default=str) + "\n")
    append_message(repo_path, session_id, "system", f"[Compact summary of earlier conversation]\n{summary}")

    return summary


def get_active_session(repo_path: Path) -> Optional[str]:
    sessions = list_sessions(repo_path)
    if sessions:
        return sessions[0]["id"]
    return None


def delete_session(repo_path: Path, session_id: str) -> bool:
    p = _session_path(repo_path, session_id)
    if p.exists():
        p.unlink()
        return True
    return False


def _read_key() -> str:
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getch()
        if ch == b"\xe0":
            ch = msvcrt.getch()
            return {"H": "up", "P": "down", "M": "right", "K": "left"}.get(ch.decode(), "")
        if ch == b"\r":
            return "enter"
        if ch == b"\x1b":
            return "esc"
        try:
            return ch.decode()
        except Exception:
            return ""
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                sys.stdin.read(1)
                ch2 = sys.stdin.read(1)
                return {"A": "up", "B": "down", "C": "right", "D": "left"}.get(ch2, "")
            if ch == "\r":
                return "enter"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def interactive_session_picker(repo_path: Path) -> Optional[str]:
    sessions = list_sessions(repo_path)
    if not sessions:
        return None

    idx = 0
    table = Table(title="Chat Sessions  (↑/↓ select, Enter confirm, Esc cancel)", show_header=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("ID", style="cyan")
    table.add_column("Turns", style="yellow", justify="right")
    table.add_column("Tokens", style="magenta", justify="right")
    table.add_column("Last", style="white")

    def render_table(highlight: int) -> Table:
        from rich.markup import escape

        t = Table(title="Chat Sessions  (↑/↓ select, Enter confirm, Esc cancel)", show_header=True)
        t.add_column("#", style="dim", width=3)
        t.add_column("ID", style="cyan")
        t.add_column("Turns", style="yellow", justify="right")
        t.add_column("Tokens", style="magenta", justify="right")
        t.add_column("Last", style="white")
        for i, s in enumerate(sessions):
            row_style = "reverse" if i == highlight else None
            t.add_row(
                str(i + 1),
                escape(s["id"]),
                str(s["turns"]),
                str(s["tokens"]),
                escape(s["last_message"]),
                style=row_style,
            )
        return t

    with Live(render_table(idx), console=_console, refresh_per_second=20, screen=False) as live:
        while True:
            key = _read_key()
            if key == "up":
                idx = max(0, idx - 1)
                live.update(render_table(idx))
            elif key == "down":
                idx = min(len(sessions) - 1, idx + 1)
                live.update(render_table(idx))
            elif key == "enter":
                break
            elif key == "esc":
                return None
            elif key == "q":
                return None

    return sessions[idx]["id"]


def show_session_context(repo_path: Path, session_id: str, max_chars: int = 2000) -> str:
    messages = load_session(repo_path, session_id)
    parts = []
    total = 0
    for m in reversed(messages):
        content = m.get("content", "")
        if total + len(content) > max_chars:
            content = content[: max_chars - total] + "..."
        parts.append(f"[{m.get('role', '?')}]: {content}")
        total += len(content)
        if total >= max_chars:
            break
    return "\n\n".join(reversed(parts))
