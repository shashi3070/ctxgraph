"""Benchmark tests comparing JSON vs DSL token efficiency and with/without ctxgraph."""

import json
import tempfile
from pathlib import Path

import pytest

from ctxgraph.capsule.renderer import render_capsule
from ctxgraph.graph.builder import build_graph
from ctxgraph.graph.storage import Storage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "complex_project"


@pytest.fixture
def built_storage():
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "test.db"
    stats = build_graph(FIXTURES_DIR, db_path=db_path)
    storage = Storage(db_path)
    storage.connect()
    yield storage, stats
    storage.close()
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestTokenEfficiency:
    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def to_json_capsule(self, storage: Storage, nodes, edges) -> str:
        data = {"nodes": [], "edges": []}
        for n in nodes:
            data["nodes"].append({
                "id": n.id, "type": n.type, "name": n.name,
                "path": n.path, "summary": n.summary,
            })
        for s, t, r in edges[:20]:
            data["edges"].append({"source": s, "target": t, "relation": r})
        return json.dumps(data, indent=2)

    def test_json_vs_dsl_token_count(self, built_storage):
        storage, stats = built_storage
        from ctxgraph.graph.query import generate_context_subgraph

        queries = ["token validation", "auth login", "user management", "config", "api routes"]
        ratios = []

        for query in queries:
            dsl = render_capsule(storage, query, max_nodes=15)
            nodes, edges = generate_context_subgraph(storage, query, max_nodes=15)
            jsn = self.to_json_capsule(storage, nodes, edges)

            dsl_tokens = self.count_tokens(dsl)
            json_tokens = self.count_tokens(jsn)

            ratio = json_tokens / max(dsl_tokens, 1)
            ratios.append(ratio)

            print(f"\n  Query: {query}")
            print(f"    DSL tokens:  {dsl_tokens}")
            print(f"    JSON tokens: {json_tokens}")
            print(f"    Ratio:       {ratio:.1f}x")

        avg_ratio = sum(ratios) / len(ratios)
        print(f"\n  Average token ratio (JSON/DSL): {avg_ratio:.1f}x")
        assert avg_ratio > 1.5, f"DSL should be significantly more token-efficient than JSON (avg ratio: {avg_ratio:.1f}x)"

    def test_capsule_vs_full_file_reading(self, built_storage):
        """Show token savings of capsule vs reading all files."""
        storage, stats = built_storage
        all_nodes = storage.get_all_nodes()
        file_nodes = [n for n in all_nodes if n.type == "file"]

        total_file_tokens = 0
        for fn in file_nodes:
            file_path = FIXTURES_DIR / (fn.path or "")
            if file_path.exists():
                try:
                    total_file_tokens += self.count_tokens(
                        file_path.read_text(encoding="utf-8", errors="replace")
                    )
                except Exception:
                    pass

        capsule = render_capsule(storage, "application", max_nodes=20)
        capsule_tokens = self.count_tokens(capsule)
        savings_pct = (1 - capsule_tokens / max(total_file_tokens, 1)) * 100

        print(f"\n  Total file tokens:    {total_file_tokens}")
        print(f"  Capsule tokens:       {capsule_tokens}")
        print(f"  Token savings:        {savings_pct:.1f}%")
        assert savings_pct > 50, f"Capsule should save >50% tokens over full file reading (saved: {savings_pct:.1f}%)"


class TestWithWithoutCtxgraph:
    """Simulate what Claude sees with and without ctxgraph context."""

    SAMPLE_TASK = (
        "I need to fix a JWT token validation bug. "
        "The tokens are expiring too early and users are getting logged out unexpectedly. "
        "The JWT handling is done in the auth module."
    )

    def test_without_ctxgraph(self):
        """What Claude would get without ctxgraph — just the raw task."""
        tokens = len(self.SAMPLE_TASK.split())
        print(f"\n  Without ctxgraph - tokens: {tokens}")
        print(f"  Context provided: nothing (blind)")

    def test_with_ctxgraph(self, built_storage):
        """What Claude gets with ctxgraph capsule."""
        storage, _ = built_storage
        capsule = render_capsule(storage, "JWT token validation expiry auth", max_nodes=15)
        full = f"[CONTEXT]\n{capsule}\n[/CONTEXT]\n\n{self.SAMPLE_TASK}"
        tokens = len(full.split())
        print(f"\n  With ctxgraph - tokens: {tokens}")
        print(f"  Context provided: structured dependency graph + summaries")

    def test_comparison(self, built_storage):
        storage, _ = built_storage
        capsule = render_capsule(storage, "JWT token validation expiry auth", max_nodes=15)
        with_ctx = len(f"[CONTEXT]\n{capsule}\n[/CONTEXT]\n\n{self.SAMPLE_TASK}".split())
        without = len(self.SAMPLE_TASK.split())
        overhead_pct = ((with_ctx - without) / max(without, 1)) * 100
        print(f"\n  Overhead of adding ctxgraph context: {overhead_pct:.1f}%")
        print(f"  (+{with_ctx - without} tokens for structured code knowledge)")
        assert overhead_pct < 200, f"Context overhead should be reasonable (was: {overhead_pct:.1f}%)"
