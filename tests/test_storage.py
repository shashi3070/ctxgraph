import tempfile
from pathlib import Path

import pytest

from ctxgraph.graph.models import Edge, Graph, Node
from ctxgraph.graph.storage import Storage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        s = Storage(db_path)
        s.connect()
        yield s
        s.close()


class TestStorage:
    def test_save_and_get_node(self, storage):
        node = Node(
            id="file:test.py",
            type="file",
            name="test.py",
            path="src/test.py",
            summary="A test file",
            importance=0.8,
            size_bytes=100,
        )
        storage.save_node(node)
        loaded = storage.get_node("file:test.py")
        assert loaded is not None
        assert loaded.id == node.id
        assert loaded.name == node.name
        assert loaded.path == node.path
        assert loaded.summary == node.summary
        assert loaded.importance == node.importance

    def test_get_nonexistent_node(self, storage):
        assert storage.get_node("nonexistent") is None

    def test_save_edge(self, storage):
        edge = Edge(source_id="a", target_id="b", relation="imports", weight=1.5)
        storage.save_edge(edge)
        edges = storage.get_edges_for_nodes({"a", "b"})
        assert len(edges) >= 1
        assert edges[0].source_id == "a"
        assert edges[0].target_id == "b"
        assert edges[0].relation == "imports"

    def test_save_graph(self, storage):
        g = Graph()
        g.add_node(Node(id="a", type="file", name="a.py"))
        g.add_node(Node(id="b", type="file", name="b.py"))
        g.add_edge(Edge(source_id="a", target_id="b", relation="imports"))
        storage.save_graph(g)

        assert storage.get_node("a") is not None
        assert storage.get_node("b") is not None
        edges = storage.get_edges_for_nodes({"a", "b"})
        assert len(edges) == 1

    def test_search_nodes(self, storage):
        storage.save_node(Node(id="file:auth.py", type="file", name="auth.py", summary="User authentication module"))
        storage.save_node(Node(id="class:JWTValidator", type="class", name="JWTValidator", summary="Validates JWT tokens"))
        storage.save_node(Node(id="file:test.py", type="file", name="test.py", summary="Test cases"))

        results = storage.search_nodes("jwt")
        assert len(results) >= 1
        assert any("jwt" in r.name.lower() or "JWT" in (r.summary or "") for r in results)

        results = storage.search_nodes("auth")
        assert len(results) >= 1

        results = storage.search_nodes("nonexistent_xyz")
        assert len(results) == 0

    def test_stats(self, storage):
        storage.save_node(Node(id="a", type="file", name="a.py"))
        storage.save_node(Node(id="b", type="class", name="B"))
        storage.save_node(Node(id="c", type="function", name="c"))
        storage.save_edge(Edge(source_id="a", target_id="b", relation="defines"))

        stats = storage.stats()
        assert stats["nodes"] == 3
        assert stats["edges"] == 1
        assert stats["types"]["file"] == 1
        assert stats["types"]["class"] == 1

    def test_metadata(self, storage):
        storage.save_metadata("build_time", "12345")
        assert storage.get_metadata("build_time") == "12345"
        assert storage.get_metadata("nonexistent") is None

    def test_get_all_nodes(self, storage):
        storage.save_node(Node(id="a", type="file", name="a.py"))
        storage.save_node(Node(id="b", type="class", name="B"))
        nodes = storage.get_all_nodes()
        assert len(nodes) == 2
