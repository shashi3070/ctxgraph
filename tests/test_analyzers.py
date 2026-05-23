import tempfile
from pathlib import Path

import pytest

from ctxgraph.analyzers.python.importer import analyze_imports
from ctxgraph.analyzers.python.semantic import enrich_node_summary
from ctxgraph.analyzers.python.symbols import analyze_symbols
from ctxgraph.graph.models import Node


def _write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestImporter:
    def test_simple_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "src" / "main.py", "import os\nimport sys")
            _write_file(root / "src" / "utils.py", "")

            graph = analyze_imports(root / "src" / "main.py", root / "src")
            file_nodes = [n for n in graph.nodes.values() if n.type == "file"]
            assert any(n.name == "main.py" for n in file_nodes)

    def test_from_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "app.py", "from auth import login, logout")
            _write_file(root / "auth.py", "def login(): pass\n")

            graph = analyze_imports(root / "app.py", root)
            assert len(graph.nodes) >= 1

    def test_syntax_error_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "broken.py", "this is not valid python @@@")
            graph = analyze_imports(root / "broken.py", root)
            assert graph is not None
            assert len(graph.edges) == 0

    def test_no_file_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "standalone.py", "x = 1")
            graph = analyze_imports(root / "standalone.py", root)
            assert graph is not None


class TestSymbols:
    def test_class_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(
                root / "models.py",
                "class User:\n    def __init__(self): pass\n    def save(self): pass\n",
            )
            graph = analyze_symbols(root / "models.py", root)
            classes = [n for n in graph.nodes.values() if n.type == "class"]
            assert len(classes) == 1
            assert classes[0].name == "User"

    def test_function_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(
                root / "utils.py",
                "def validate(data): pass\ndef transform(data): pass\n",
            )
            graph = analyze_symbols(root / "utils.py", root)
            funcs = [n for n in graph.nodes.values() if n.type == "function"]
            assert len(funcs) == 2
            names = {f.name for f in funcs}
            assert "validate" in names
            assert "transform" in names

    def test_async_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "async_utils.py", "async def fetch_data(): pass\n")
            graph = analyze_symbols(root / "async_utils.py", root)
            funcs = [n for n in graph.nodes.values() if n.type == "function"]
            assert len(funcs) == 1
            assert funcs[0].name == "fetch_data"

    def test_method_inside_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(
                root / "service.py",
                "class Service:\n    def run(self): pass\n    async def stop(self): pass\n",
            )
            graph = analyze_symbols(root / "service.py", root)
            funcs = [n for n in graph.nodes.values() if n.type == "function"]
            assert len(funcs) == 2

    def test_class_inheritance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(
                root / "shapes.py",
                "class Shape: pass\nclass Circle(Shape): pass\n",
            )
            graph = analyze_symbols(root / "shapes.py", root)
            assert len(graph.nodes) >= 2
            extends_edges = [e for e in graph.edges if e.relation == "extends"]
            assert len(extends_edges) >= 1


class TestSemantic:
    def test_docstring_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(
                root / "auth.py",
                '''"""Authentication module."""
class JWTValidator:
    """Validates JWT tokens for the auth system."""
    def validate(self):
        """Check if token is valid."""
        pass
''',
            )
            node = Node(
                id="class:auth.py::JWTValidator",
                type="class",
                name="JWTValidator",
                path="auth.py",
            )
            result = enrich_node_summary(node, root / "auth.py")
            assert "JWT" in result

    def test_file_summary_with_docstring(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(
                root / "config.py",
                '''"""Configuration loader for the application."""
import os
DEFAULT_PORT = 8080
''',
            )
            node = Node(id="file:config.py", type="file", name="config.py", path="config.py")
            result = enrich_node_summary(node, root / "config.py")
            assert "configuration" in result.lower()

    def test_file_summary_fallback_to_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(
                root / "util.py",
                "class Helper: pass\ndef format(): pass\n",
            )
            node = Node(id="file:util.py", type="file", name="util.py", path="util.py")
            result = enrich_node_summary(node, root / "util.py")
            assert "Helper" in result


class TestExclude:
    def test_exclude_patterns(self):
        from ctxgraph.exclude.patterns import should_exclude

        root = Path("/repo")
        assert should_exclude(root / "__pycache__" / "cache.py", root)
        assert should_exclude(root / "node_modules" / "lib.js", root)
        assert not should_exclude(root / "src" / "main.py", root)
        assert not should_exclude(root / "tests" / "test_main.py", root)
