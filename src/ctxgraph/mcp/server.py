"""
Phase 2: MCP (Model Context Protocol) Server

This server implements the MCP protocol to allow Claude Desktop
and other MCP-compatible clients to query the knowledge graph
directly through tools instead of static context capsules.

Protocol: https://modelcontextprotocol.io

Usage:
    ctx serve                                       # Auto-detect from cwd (stdio mode)
    ctx serve --repo /path/to/project                # Explicit project root
    ctx serve --port 8080                            # SSE mode (not yet supported)

Claude Desktop config (with --repo):
{
    "mcpServers": {
        "ctxgraph": {
            "command": "ctx",
            "args": ["serve", "--repo", "C:\\path\\to\\project"]
        }
    }
}

Or via CTXGRAPH_REPO_PATH env var:
{
    "mcpServers": {
        "ctxgraph": {
            "command": "ctx",
            "args": ["serve"],
            "env": {"CTXGRAPH_REPO_PATH": "C:\\path\\to\\project"}
        }
    }
}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions

    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from ctxgraph.capsule.renderer import render_capsule, render_project_overview
from ctxgraph.clients.models import ModelMode, get_mode_config
from ctxgraph.graph.builder import get_storage
from ctxgraph.graph.query import search_relevant_nodes


def _find_repo_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / ".ctxgraph").is_dir():
            return parent
    return start


def _resolve_repo_path(repo_path: Optional[str] = None) -> Path:
    if repo_path:
        return Path(repo_path).resolve()
    env_path = os.environ.get("CTXGRAPH_REPO_PATH")
    if env_path:
        return Path(env_path).resolve()
    return _find_repo_root(Path.cwd())


def create_server(repo_path: Optional[str] = None) -> Optional[Any]:
    if not HAS_MCP:
        return None

    path = _resolve_repo_path(repo_path)
    db_path = path / ".ctxgraph" / "graph.db"
    print(f"[ctxgraph] Repo root: {path}", file=sys.stderr)
    print(f"[ctxgraph] Graph DB: {db_path}", file=sys.stderr)
    storage = get_storage(path)

    server = Server("ctxgraph")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="search_graph",
                description="Search the codebase knowledge graph for relevant files, classes, and functions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query describing what you're looking for",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 15,
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="get_context_capsule",
                description="Generate a token-efficient context capsule for a specific task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The task description for context generation",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["fast", "balanced", "deep"],
                            "description": "Detail level: fast (minimal), balanced, deep (comprehensive)",
                            "default": "balanced",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="get_file_dependencies",
                description="Get the dependency graph for a specific file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to repo root)",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            types.Tool(
                name="get_project_overview",
                description="Get a high-level overview of the entire codebase structure",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="read_file",
                description="Read the full contents of a source file from the repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to repo root)",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            types.Tool(
                name="search_files",
                description="Search for files in the repository matching a glob pattern",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g. '**/*.py', 'src/**/*service*', '**/*test*')",
                        },
                    },
                    "required": ["pattern"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent]:
        nonlocal storage
        if storage is None:
            storage = get_storage(path)

        if storage is None:
            return [types.TextContent(
                type="text",
                text=f"No graph found at: {path / '.ctxgraph' / 'graph.db'}\n\n"
                     f"Run `ctx build` in your project root first.\n"
                     f"Or set the CTXGRAPH_REPO_PATH environment variable to your project root.\n"
                     f"Or pass --repo to ctx serve, e.g. `ctx serve --repo /path/to/project`.",
            )]

        if name == "search_graph":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 15)
            results = search_relevant_nodes(storage, query, max_nodes=max_results)
            lines = [f"Search results for: {query}", ""]
            for node, score in results:
                lines.append(f"  [{node.type}] {node.name} ({node.path}) - score: {score}")
                if node.summary:
                    lines.append(f"    {node.summary}")
            return [types.TextContent(type="text", text="\n".join(lines))]

        elif name == "get_context_capsule":
            query = arguments.get("query", "")
            mode_str = arguments.get("mode", "balanced")
            mode = ModelMode.from_str(mode_str)
            cfg = get_mode_config(mode)
            capsule = render_capsule(storage, query, max_nodes=cfg["max_nodes"])
            return [types.TextContent(type="text", text=capsule)]

        elif name == "get_file_dependencies":
            file_path = arguments.get("file_path", "")
            node_id = f"file:{file_path}"
            node = storage.get_node(node_id)
            if not node:
                return [types.TextContent(
                    type="text",
                    text=f"File not found in graph: {file_path}",
                )]
            edges = storage.get_edges_for_nodes({node_id})
            lines = [f"Dependencies for: {file_path}", ""]
            for e in edges:
                target = storage.get_node(e.target_id)
                source = storage.get_node(e.source_id)
                if target and source:
                    lines.append(f"  {source.name} --{e.relation}--> {target.name}")
            return [types.TextContent(type="text", text="\n".join(lines))]

        elif name == "get_project_overview":
            overview = render_project_overview(storage)
            return [types.TextContent(type="text", text=overview)]

        elif name == "read_file":
            file_path = arguments.get("file_path", "")
            full_path = (path / file_path).resolve()
            if not str(full_path).startswith(str(path.resolve())):
                return [types.TextContent(
                    type="text",
                    text=f"Access denied: {file_path} is outside the repository root.",
                )]
            if not full_path.exists():
                return [types.TextContent(
                    type="text",
                    text=f"File not found: {file_path}",
                )]
            if not full_path.is_file():
                return [types.TextContent(
                    type="text",
                    text=f"Not a file: {file_path}",
                )]
            content = full_path.read_text(encoding="utf-8", errors="replace")
            lines = content.count("\n") + 1
            tokens = max(1, len(content) // 4)
            content += f"\n---\nLine count: {lines} | Tokens: ~{tokens}"
            return [types.TextContent(type="text", text=content)]

        elif name == "search_files":
            pattern = arguments.get("pattern", "")
            matches = sorted(path.rglob(pattern))
            matches = [m for m in matches if m.is_file()]
            if not matches:
                return [types.TextContent(
                    type="text",
                    text=f"No files found matching: {pattern}",
                )]
            lines = [f"Files matching '{pattern}':", ""]
            for m in matches[:100]:
                lines.append(f"  {m.relative_to(path).as_posix()}")
            if len(matches) > 100:
                lines.append(f"  ... and {len(matches) - 100} more")
            return [types.TextContent(type="text", text="\n".join(lines))]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


def run_server(repo_path: Optional[str] = None, port: Optional[int] = None):
    if not HAS_MCP:
        print(
            "MCP support requires additional dependencies.\n"
            "Install with: pip install ctxgraph[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_server(repo_path)
    if server is None:
        print("Failed to create MCP server", file=sys.stderr)
        sys.exit(1)

    from mcp.server.stdio import stdio_server

    import anyio

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ctxgraph",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    anyio.run(_run)
