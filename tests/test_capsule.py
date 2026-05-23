import tempfile
from pathlib import Path

import pytest

from ctxgraph.graph.models import Edge, Node
from ctxgraph.graph.storage import Storage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        s = Storage(db_path)
        s.connect()

        s.save_node(Node(id="file:auth.py", type="file", name="auth.py", path="src/auth.py", summary="Authentication module", importance=0.8))
        s.save_node(Node(id="file:jwt.py", type="file", name="jwt.py", path="src/jwt.py", summary="JWT token handling", importance=0.7))
        s.save_node(Node(id="class:auth.py::JWTValidator", type="class", name="JWTValidator", path="src/auth.py", summary="Validates JWT tokens", importance=0.6))
        s.save_node(Node(id="func:jwt.py::validate_token", type="function", name="validate_token", path="src/jwt.py", summary="Validates token signature", importance=0.6))

        s.save_edge(Edge(source_id="file:auth.py", target_id="file:jwt.py", relation="imports"))
        s.save_edge(Edge(source_id="file:auth.py", target_id="class:auth.py::JWTValidator", relation="defines"))
        s.save_edge(Edge(source_id="file:jwt.py", target_id="func:jwt.py::validate_token", relation="defines"))

        yield s
        s.close()


class TestCapsule:
    def test_render_capsule(self, storage):
        from ctxgraph.capsule.renderer import render_capsule

        result = render_capsule(storage, "jwt")
        assert "[CTX]" in result
        assert "[F]" in result or "[C]" in result or "[INFO]" in result
        assert len(result) > 0

    def test_capsule_contains_query(self, storage):
        from ctxgraph.capsule.renderer import render_capsule

        result = render_capsule(storage, "jwt validation")
        assert "jwt validation" in result.lower()

    def test_render_empty_capsule(self, storage):
        from ctxgraph.capsule.renderer import render_capsule

        result = render_capsule(storage, "xyznonexistent")
        assert "no relevant context" in result.lower()

    def test_render_project_overview(self, storage):
        from ctxgraph.capsule.renderer import render_project_overview

        result = render_project_overview(storage)
        assert "[CTX]" in result
        assert "[F]" in result
