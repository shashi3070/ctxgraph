from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ctxgraph.clients.models import ModelMode, get_mode_config
from ctxgraph.graph.builder import get_storage

try:
    from ctxgraph.capsule.renderer import render_capsule, render_project_overview

    HAS_CAPSULE = True
except ImportError:
    HAS_CAPSULE = False


def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: ccg [--mode fast|balanced|deep] <query>")
        print("       ccg --overview")
        print("       ccg --chat <query>")
        sys.exit(1)

    mode = ModelMode.BALANCED
    is_overview = False
    is_chat = False
    query_parts = []

    for arg in args:
        if arg == "--overview" or arg == "-o":
            is_overview = True
        elif arg == "--chat" or arg == "-c":
            is_chat = True
        elif arg.startswith("--mode="):
            mode = ModelMode.from_str(arg.split("=", 1)[1])
        elif arg == "--mode" or arg == "-m":
            continue
        else:
            query_parts.append(arg)

    if not is_overview and not query_parts:
        print("No query provided.")
        sys.exit(1)

    query = " ".join(query_parts)
    mode_cfg = get_mode_config(mode)

    repo_path = Path.cwd()
    capsule_text = ""
    storage = None

    try:
        storage = get_storage(repo_path)
    except Exception:
        storage = None

    if storage:
        if is_overview:
            capsule_text = render_project_overview(storage)
        else:
            capsule_text = render_capsule(
                storage,
                query,
                max_nodes=mode_cfg["max_nodes"],
            )
    else:
        capsule_text = (
            "[INFO]No ctxgraph data found. "
            "Run `ctx build` for enriched context."
        )

    mode_hint = {
        ModelMode.FAST: "Use fast, concise reasoning. Prioritize direct answers.",
        ModelMode.BALANCED: "",
        ModelMode.DEEP: "Take your time. Analyze deeply before responding.",
    }.get(mode, "")

    augmented_prompt = (
        f"[CONTEXT]\n{capsule_text}\n[/CONTEXT]\n\n"
        f"TASK: {query}\n\n"
        f"{mode_hint}\n" if mode_hint else ""
    )

    claude_cmd = _find_claude()
    if not claude_cmd:
        print(
            "[red]Claude CLI not found. Install it or ensure it's in PATH.[/red]",
            file=sys.stderr,
        )
        sys.exit(1)

    if is_chat:
        context_file = repo_path / ".ctxgraph" / "context.md"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_file.write_text(capsule_text, encoding="utf-8")

        system_msg = (
            f"Project context is loaded from {context_file}.\n"
            f"Read it first, then help the user.\n"
            f"{mode_hint}"
        )

        proc = subprocess.Popen(
            [claude_cmd, "-p", system_msg],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        proc.wait()
    else:
        proc = subprocess.run(
            [claude_cmd, "-p", augmented_prompt],
            capture_output=False,
        )
        sys.exit(proc.returncode)


def _find_claude() -> str | None:
    claude_names = ["claude", "claude.exe"]
    for name in claude_names:
        try:
            result = subprocess.run(
                ["where", name] if sys.platform == "win32" else ["which", name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return name
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return None


if __name__ == "__main__":
    main()
