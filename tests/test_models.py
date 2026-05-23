import pytest
from ctxgraph.graph.models import Edge, Graph, Node


class TestNode:
    def test_create_node(self):
        node = Node(id="file:test.py", type="file", name="test.py", path="src/test.py")
        assert node.id == "file:test.py"
        assert node.type == "file"
        assert node.name == "test.py"
        assert node.path == "src/test.py"
        assert node.importance == 0.5

    def test_node_hash_and_eq(self):
        a = Node(id="x", type="file", name="x")
        b = Node(id="x", type="file", name="x")
        c = Node(id="y", type="file", name="y")
        assert a == b
        assert a != c
        assert hash(a) == hash(b)


class TestEdge:
    def test_create_edge(self):
        e = Edge(source_id="a", target_id="b", relation="imports")
        assert e.source_id == "a"
        assert e.target_id == "b"
        assert e.relation == "imports"
        assert e.weight == 1.0

    def test_edge_hash_and_eq(self):
        a = Edge(source_id="x", target_id="y", relation="imports")
        b = Edge(source_id="x", target_id="y", relation="imports")
        c = Edge(source_id="x", target_id="z", relation="imports")
        assert a == b
        assert a != c


class TestGraph:
    def test_add_node(self):
        g = Graph()
        n = Node(id="f1", type="file", name="a.py")
        g.add_node(n)
        assert g.get_node("f1") == n

    def test_add_edge(self):
        g = Graph()
        g.add_node(Node(id="a", type="file", name="a.py"))
        g.add_node(Node(id="b", type="file", name="b.py"))
        e = Edge(source_id="a", target_id="b", relation="imports")
        g.add_edge(e)
        assert len(g.edges) == 1
        assert g.get_edges_from("a") == [e]
        assert g.get_edges_to("b") == [e]

    def test_get_neighbors(self):
        g = Graph()
        for nid in ["a", "b", "c"]:
            g.add_node(Node(id=nid, type="file", name=f"{nid}.py"))
        g.add_edge(Edge(source_id="a", target_id="b", relation="imports"))
        g.add_edge(Edge(source_id="a", target_id="c", relation="imports"))
        neighbors = g.get_neighbors("a")
        assert "b" in neighbors
        assert "c" in neighbors
        assert "a" not in neighbors

    def test_merge(self):
        g1 = Graph()
        g1.add_node(Node(id="a", type="file", name="a.py"))
        g1.add_edge(Edge(source_id="a", target_id="b", relation="imports"))

        g2 = Graph()
        g2.add_node(Node(id="b", type="file", name="b.py"))
        g2.add_edge(Edge(source_id="b", target_id="c", relation="imports"))

        g1.merge(g2)
        assert "b" in g1.nodes
        assert len(g1.edges) == 2

    def test_no_duplicate_edges_on_merge(self):
        g1 = Graph()
        g1.add_node(Node(id="a", type="file", name="a.py"))
        g1.add_node(Node(id="b", type="file", name="b.py"))
        g1.add_edge(Edge(source_id="a", target_id="b", relation="imports"))

        g2 = Graph()
        g2.add_node(Node(id="a", type="file", name="a.py"))
        g2.add_node(Node(id="b", type="file", name="b.py"))
        g2.add_edge(Edge(source_id="a", target_id="b", relation="imports"))

        g1.merge(g2)
        assert len(g1.edges) == 1
