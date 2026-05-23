from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ctxgraph.capsule.renderer import render_capsule, render_project_overview
from ctxgraph.clients.models import ModelMode, get_mode_config
from ctxgraph.graph.builder import build_graph, get_storage
from ctxgraph.graph.query import search_relevant_nodes

app = typer.Typer(name="ctx", help="Context graph engine for AI coding assistants")
console = Console()


@app.callback()
def callback():
    pass


@app.command()
def build(
    repo_path: Optional[str] = typer.Argument(
        None, help="Path to repository (default: current directory)"
    ),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path (synonym for positional)"
    ),
    exclude: Optional[list[str]] = typer.Option(
        None, "--exclude", "-e", help="Additional exclude patterns"
    ),
    db_path: Optional[str] = typer.Option(
        None, "--db", "-d", help="Custom database path"
    ),
):
    """Build the knowledge graph for a repository."""
    effective = repo or repo_path
    path = Path(effective).resolve() if effective else Path.cwd()

    if not (path / ".ctxgraph").exists():
        (path / ".ctxgraph").mkdir(parents=True, exist_ok=True)

    with console.status(f"Analyzing {path}..."):
        stats = build_graph(path, db_path, exclude)

    table = Table(title="Graph Build Complete")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Files Analyzed", str(stats["files_analyzed"]))
    table.add_row("Files Skipped", str(stats.get("files_skipped", 0)))
    table.add_row("Errors", str(stats.get("errors", 0)))
    table.add_row("Total Nodes", str(stats.get("total_nodes", 0)))
    table.add_row("Total Edges", str(stats.get("total_edges", 0)))
    table.add_row("Time", f"{stats.get('elapsed_seconds', 0)}s")

    console.print(table)
    console.print(f"\nGraph stored in: [bold]{path / '.ctxgraph' / 'graph.db'}[/bold]")


@app.command()
def capsule(
    query: str = typer.Argument(..., help="Task description"),
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
    max_nodes: Optional[int] = typer.Option(
        None, "--max-nodes", "-n", help="Maximum nodes in capsule"
    ),
    mode: str = typer.Option(
        "balanced", "--mode", "-m", help="Model mode: fast, balanced, deep"
    ),
    overview: bool = typer.Option(
        False, "--overview", "-o", help="Generate project overview instead"
    ),
):
    """Generate a context capsule for Claude."""
    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    model_mode = ModelMode.from_str(mode)
    mode_cfg = get_mode_config(model_mode)

    storage = get_storage(path)
    if storage is None:
        console.print(
            "[red]No graph found. Run [bold]ctx build[/bold] first.[/red]"
        )
        raise typer.Exit(1)

    if overview:
        result = render_project_overview(storage)
    else:
        result = render_capsule(
            storage,
            query,
            max_nodes=max_nodes or mode_cfg["max_nodes"],
        )

    console.print(result)


@app.command()
def query(
    query: str = typer.Argument(..., help="Search query"),
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
    mode: str = typer.Option(
        "balanced", "--mode", "-m", help="Model mode: fast, balanced, deep"
    ),
):
    """Search the knowledge graph."""
    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    model_mode = ModelMode.from_str(mode)
    mode_cfg = get_mode_config(model_mode)

    storage = get_storage(path)
    if storage is None:
        console.print(
            "[red]No graph found. Run [bold]ctx build[/bold] first.[/red]"
        )
        raise typer.Exit(1)

    results = search_relevant_nodes(
        storage,
        query,
        max_nodes=mode_cfg["max_nodes"],
        max_depth=mode_cfg["max_depth"],
    )

    if not results:
        console.print("[yellow]No matches found.[/yellow]")
        return

    table = Table(title=f"Search Results: {query}")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Path", style="blue")
    table.add_column("Relevance", style="yellow")

    for node, score in results:
        type_tag = {"file": "F", "class": "C", "function": "M", "module": "M"}
        table.add_row(
            type_tag.get(node.type, "?"),
            node.name,
            node.path or "-",
            str(score),
        )

    console.print(table)


@app.command()
def view(
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port for server"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save HTML to file"
    ),
    open_browser: bool = typer.Option(
        True, "--open/--no-open", help="Open in browser automatically"
    ),
):
    """Visualize the dependency graph in a browser."""
    from ctxgraph.view.visualizer import render_view

    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    storage = get_storage(path)
    if storage is None:
        console.print(
            "[red]No graph found. Run [bold]ctx build[/bold] first.[/red]"
        )
        raise typer.Exit(1)

    html = render_view(storage)

    if output:
        out_path = Path(output)
        out_path.write_text(html, encoding="utf-8")
        console.print(f"Saved to [bold]{out_path}[/bold]")
    else:
        out_path = path / ".ctxgraph" / "graph.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        console.print(f"Saved to [bold]{out_path}[/bold]")

    if open_browser:
        import webbrowser

        webbrowser.open(f"file://{out_path.absolute()}")
        console.print("Opened in browser.")


@app.command()
def info(
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
):
    """Show graph statistics."""
    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    storage = get_storage(path)
    if storage is None:
        console.print(
            "[red]No graph found. Run [bold]ctx build[/bold] first.[/red]"
        )
        raise typer.Exit(1)

    stats = storage.stats()
    build_time = storage.get_metadata("build_time")

    table = Table(title="Graph Info")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Nodes", str(stats["nodes"]))
    table.add_row("Total Edges", str(stats["edges"]))

    plural_map = {"file": "files", "class": "classes", "function": "functions", "module": "modules"}
    for t, cnt in stats.get("types", {}).items():
        label = plural_map.get(t, t + "s")
        table.add_row(f"  {label}", str(cnt))

    if build_time:
        table.add_row("Last Build", build_time)

    console.print(table)


if __name__ == "__main__":
    app()
