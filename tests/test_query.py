import tempfile
from pathlib import Path

import pytest

from ctxgraph.graph.models import Edge, Node
from ctxgraph.graph.storage import Storage


@pytest.fixture
def populated_storage():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        s = Storage(db_path)
        s.connect()

        s.save_node(Node(id="file:auth.py", type="file", name="auth.py", path="src/auth.py", summary="Authentication module", importance=0.8))
        s.save_node(Node(id="file:jwt.py", type="file", name="jwt.py", path="src/jwt.py", summary="JWT token handling", importance=0.7))
        s.save_node(Node(id="file:db.py", type="file", name="db.py", path="src/db.py", summary="Database connection", importance=0.5))
        s.save_node(Node(id="class:auth.py::JWTValidator", type="class", name="JWTValidator", path="src/auth.py", summary="Validates JWT tokens", importance=0.6))
        s.save_node(Node(id="func:jwt.py::validate_token", type="function", name="validate_token", path="src/jwt.py", summary="Validates token signature", importance=0.6))
        s.save_node(Node(id="func:jwt.py::decode_token", type="function", name="decode_token", path="src/jwt.py", importance=0.5))
        s.save_node(Node(id="file:utils.py", type="file", name="utils.py", path="src/utils.py", summary="Utility functions", importance=0.3))

        s.save_edge(Edge(source_id="file:auth.py", target_id="file:jwt.py", relation="imports"))
        s.save_edge(Edge(source_id="file:auth.py", target_id="class:auth.py::JWTValidator", relation="defines"))
        s.save_edge(Edge(source_id="file:jwt.py", target_id="func:jwt.py::validate_token", relation="defines"))
        s.save_edge(Edge(source_id="file:jwt.py", target_id="func:jwt.py::decode_token", relation="defines"))
        s.save_edge(Edge(source_id="file:auth.py", target_id="file:db.py", relation="imports"))

        yield s
        s.close()


class TestQuery:
    def test_search_by_name(self, populated_storage):
        from ctxgraph.graph.query import search_relevant_nodes

        results = search_relevant_nodes(populated_storage, "jwt")
        assert len(results) >= 2
        names = {n.name for n, _ in results}
        assert "JWTValidator" in names

    def test_search_by_summary(self, populated_storage):
        from ctxgraph.graph.query import search_relevant_nodes

        results = search_relevant_nodes(populated_storage, "authentication")
        assert len(results) >= 1
        assert any("auth" in (n.path or "") for n, _ in results)

    def test_search_no_match(self, populated_storage):
        from ctxgraph.graph.query import search_relevant_nodes

        results = search_relevant_nodes(populated_storage, "xyznonexistent")
        assert len(results) == 0

    def test_context_subgraph(self, populated_storage):
        from ctxgraph.graph.query import generate_context_subgraph

        nodes, edges = generate_context_subgraph(populated_storage, "jwt")
        assert len(nodes) > 0
        assert len(edges) > 0

    def test_search_with_depth(self, populated_storage):
        from ctxgraph.graph.query import search_relevant_nodes

        shallow = search_relevant_nodes(populated_storage, "auth", max_depth=1)
        deep = search_relevant_nodes(populated_storage, "auth", max_depth=3)
        assert len(deep) >= len(shallow)
