"""Integration tests with the sample complex project."""

import tempfile
from pathlib import Path

import pytest

from ctxgraph.graph.builder import build_graph
from ctxgraph.graph.query import search_relevant_nodes
from ctxgraph.capsule.renderer import render_capsule
from ctxgraph.graph.storage import Storage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "complex_project"


@pytest.fixture
def built_db():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        stats = build_graph(FIXTURES_DIR, db_path=db_path)
        yield str(db_path), stats


@pytest.fixture
def storage(built_db):
    db_path, _ = built_db
    s = Storage(db_path)
    s.connect()
    yield s
    s.close()


class TestIntegration:
    def test_build_on_complex_project(self, built_db):
        db_path, stats = built_db
        assert stats["files_analyzed"] >= 10
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0
        assert stats["errors"] == 0

    def test_search_after_build(self, storage):
        results = search_relevant_nodes(storage, "auth")
        names = {n.name for n, _ in results}
        assert "AuthService" in names or any("auth" in (n.path or "") for n, _ in results)

    def test_capsule_after_build(self, storage):
        capsule = render_capsule(storage, "token validation")
        assert "[CTX]" in capsule
        assert len(capsule) > 50

    def test_view_html_generation(self, storage):
        from ctxgraph.view.visualizer import render_view

        html = render_view(storage)
        assert "<!DOCTYPE html>" in html
        assert "d3" in html.lower() or "D3" in html
        assert "GRAPH_DATA" not in html

    def test_multiple_queries(self, storage):
        queries = ["auth", "config", "redis", "admin", "token"]
        for q in queries:
            results = search_relevant_nodes(storage, q, max_nodes=5)
            assert len(results) > 0, f"No results for query: {q}"

    def test_capsule_contains_relevant_content(self, storage):
        capsule = render_capsule(storage, "redis connection")
        assert "[CTX]" in capsule
        assert "redis" in capsule.lower() or "Redis" in capsule
