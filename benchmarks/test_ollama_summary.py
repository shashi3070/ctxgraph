"""Test Ollama (qwen2.5-coder:7b) summarization performance.

Usage:
    python benchmarks/test_ollama_summary.py
"""

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ctxgraph.config.settings import Settings
from ctxgraph.config.providers import generate_summary, chat_completion

PROJECTS_DIR = REPO_ROOT / "benchmarks" / "projects"

SAMPLE_FILES = [
    ("web_api", "middleware/auth.py", "JWT authentication middleware"),
    ("web_api", "services/auth_service.py", "Auth service with JWT and session management"),
    ("web_api", "routes/users.py", "User management routes"),
    ("microsvc", "services/auth/jwt.py", "JWT token creation and validation"),
    ("microsvc", "shared/circuit_breaker.py", "Circuit breaker pattern implementation"),
]


def count_tokens(text: str) -> int:
    return len(text.split())


def test_ollama_summary():
    settings = Settings()
    print(f"Provider: {settings.provider}")
    print(f"Model:    {settings.model}")
    print(f"Endpoint: {settings.endpoint}")
    print()

    for proj, rel_path, description in SAMPLE_FILES:
        file_path = PROJECTS_DIR / proj / rel_path
        if not file_path.is_file():
            print(f"  SKIP {proj}/{rel_path}: not found")
            continue

        code = file_path.read_text(encoding="utf-8")
        code_tokens = count_tokens(code)

        start = time.perf_counter()
        summary = generate_summary(settings, code, context=description)
        elapsed = time.perf_counter() - start

        summary_tokens = count_tokens(summary) if summary else 0

        status = "OK" if summary else "FAIL"
        print(f"  [{status}] {proj}/{rel_path}")
        print(f"         Code: {code_tokens} tok, Summary: {summary_tokens} tok, Time: {elapsed:.1f}s")
        if summary:
            # Truncate long summaries for display
            display = summary[:120] + ("..." if len(summary) > 120 else "")
            print(f"         Summary: {display}")
        print()


def test_chat_ollama():
    settings = Settings()
    prompt = "Explain what a context graph is in 2-3 sentences for developers."

    start = time.perf_counter()
    response = chat_completion(settings,
        system_prompt="You are a helpful assistant.",
        user_prompt=prompt,
    )
    elapsed = time.perf_counter() - start

    if response:
        tokens = count_tokens(response)
        print(f"Chat test: {tokens} tokens in {elapsed:.1f}s")
        print(f"Response: {response[:200]}")
    else:
        print(f"Chat test FAILED after {elapsed:.1f}s")


if __name__ == "__main__":
    print("=" * 60)
    print("  Ollama LLM Summary Benchmark")
    print("=" * 60)
    print()
    test_ollama_summary()
    print("=" * 60)
    print("  Ollama Chat Test")
    print("=" * 60)
    print()
    test_chat_ollama()
