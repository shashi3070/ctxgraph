from __future__ import annotations

from collections import defaultdict
from typing import Optional

from ctxgraph.graph.models import Node
from ctxgraph.graph.storage import Storage


def render_capsule(
    storage: Storage,
    query: str,
    max_nodes: int = 15,
    include_deps: bool = True,
) -> str:
    from ctxgraph.graph.query import generate_context_subgraph

    nodes, edges = generate_context_subgraph(storage, query, max_nodes)
    if not nodes:
        return _empty_capsule(query)

    return _build_dsl(nodes, edges, storage, query)


def render_project_overview(
    storage: Storage,
    max_files: int = 30,
) -> str:
    all_nodes = storage.get_all_nodes()
    file_nodes = [n for n in all_nodes if n.type == "file"][:max_files]

    lines = ["[CTX]Project Overview", ""]
    for node in file_nodes:
        summary = node.summary or ""
        lines.append(f"[F]{node.path or node.name}")
        if summary:
            lines.append(f"  D:{summary}")

        children = [
            n for n in all_nodes
            if n.parent_id == node.id and n.type in ("class", "function")
        ]
        if children:
            names = [c.name for c in children[:8]]
            lines.append(f"  S:{', '.join(names)}")

    lines.append("")
    return "\n".join(lines)


def _build_dsl(
    nodes: list[Node],
    edges: list[tuple[str, str, str]],
    storage: Storage,
    query: str,
) -> str:
    lines = [f"[CTX]{query}", ""]

    type_order = {"file": 0, "module": 1, "class": 2, "function": 3}
    nodes_sorted = sorted(nodes, key=lambda n: type_order.get(n.type, 9))

    file_nodes = [n for n in nodes_sorted if n.type == "file"]
    symbol_nodes = [n for n in nodes_sorted if n.type != "file"]

    deps_by_file: dict[str, list[str]] = defaultdict(list)
    calls_by_file: dict[str, list[str]] = defaultdict(list)
    for src, tgt, rel in edges:
        src_file = _find_file_for(src, nodes)
        if rel == "imports":
            deps_by_file[src].append(tgt)
        elif rel == "calls":
            calls_by_file[src].append(tgt)

    seen_files = set()
    for node in file_nodes:
        if node.path in seen_files:
            continue
        seen_files.add(node.path or node.name)
        _render_file_node(lines, node, deps_by_file, storage)

    seen_symbols = set()
    for node in symbol_nodes:
        if node.id in seen_symbols:
            continue
        seen_symbols.add(node.id)
        _render_symbol_node(lines, node)

    dep_lines = _render_dependency_edges(edges, nodes)
    lines.extend(dep_lines)

    return "\n".join(lines)


def _render_file_node(
    lines: list[str],
    node: Node,
    deps_by_file: dict[str, list[str]],
    storage: Optional[Storage] = None,
):
    path = node.path or node.name
    lines.append(f"[F]{path}")

    if node.summary:
        lines.append(f"  D:{node.summary}")

    if storage:
        children = [
            n
            for n in storage.get_all_nodes()
            if n.parent_id == node.id and n.type in ("class", "function")
        ]
        if children:
            symbol_names = [c.name for c in children[:10]]
            lines.append(f"  S:{', '.join(symbol_names)}")

    lines.append("")


def _render_symbol_node(lines: list[str], node: Node):
    type_tag = {"class": "[C]", "function": "[M]"}
    tag = type_tag.get(node.type, "[S]")
    name = node.name

    if node.parent_id and "::" not in node.parent_id:
        parent_short = node.parent_id.split(":")[-1] if ":" in node.parent_id else node.parent_id
        name = f"{parent_short}.{node.name}"

    lines.append(f"{tag}{name}")
    if node.summary:
        lines.append(f"  D:{node.summary}")
    lines.append("")


def _render_dependency_edges(
    edges: list[tuple[str, str, str]],
    nodes: list[Node],
) -> list[str]:
    node_map = {n.id: n for n in nodes}
    dep_lines = []

    import_edges = [(s, t) for s, t, r in edges if r == "imports"]
    if import_edges:
        dep_lines.append("[DEP]")
        for src, tgt in import_edges[:10]:
            src_name = _short_name(src, node_map)
            tgt_name = _short_name(tgt, node_map)
            if src_name and tgt_name:
                dep_lines.append(f"  {src_name} -> {tgt_name}")

    call_edges = [(s, t) for s, t, r in edges if r == "calls"]
    if call_edges:
        dep_lines.append("[CAL]")
        for src, tgt in call_edges[:10]:
            src_name = _short_name(src, node_map)
            tgt_name = _short_name(tgt, node_map)
            if src_name and tgt_name:
                dep_lines.append(f"  {src_name} -> {tgt_name}")

    return dep_lines


def _short_name(node_id: str, node_map: dict[str, Node]) -> Optional[str]:
    if node_id in node_map:
        n = node_map[node_id]
        if n.type == "file":
            return n.path or n.name
        return f"{n.path}:{n.name}" if n.path else n.name
    return node_id.split(":")[-1] if ":" in node_id else node_id


def _find_file_for(node_id: str, nodes: list[Node]) -> str:
    for n in nodes:
        if n.id == node_id or (n.parent_id and n.parent_id == node_id):
            return n.path or n.name
    return node_id


def _empty_capsule(query: str) -> str:
    return (
        f"[CTX]{query}\n\n"
        "[INFO]No relevant context found in the graph.\n"
        "[INFO]Run `ctx build` first to generate the knowledge graph.\n"
    )
