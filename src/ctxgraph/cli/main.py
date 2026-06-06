from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ctxgraph.capsule.renderer import render_capsule, render_project_overview
from ctxgraph.capsule.savings import compute_savings, render_savings_table
from ctxgraph.clients.models import ModelMode, get_mode_config
from ctxgraph.config.settings import Settings, create_default_config
from ctxgraph.graph.builder import build_graph, get_storage
from ctxgraph.graph.query import search_relevant_nodes
from ctxgraph.history import append_entry, get_entries, get_stats
from ctxgraph.skills import discover_skills, get_builtin_skills, load_skill

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
    provider: Optional[str] = typer.Option(
        None, "--provider", help="LLM provider (ollama, claude, openai)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="LLM model name"
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
    savings: bool = typer.Option(
        False, "--savings", help="Show token savings table"
    ),
    skill: Optional[str] = typer.Option(
        None, "--skill", "-s", help="Skill name to activate"
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

    skill_text = load_skill(path, skill) if skill else None

    if overview:
        result = render_project_overview(storage)
    else:
        result = render_capsule(
            storage,
            query,
            max_nodes=max_nodes or mode_cfg["max_nodes"],
            skill_context=skill_text,
        )

    console.print(result)

    if savings or skill_text:
        _savings = compute_savings(path, result)
        savings_output = render_savings_table(_savings)
        console.print(savings_output)


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
        None, "--output", "-o", help="Save HTML/SVG to file"
    ),
    open_browser: bool = typer.Option(
        True, "--open/--no-open", help="Open in browser automatically"
    ),
    svg: bool = typer.Option(
        False, "--svg", help="Generate static SVG instead of interactive HTML"
    ),
):
    """Visualize the dependency graph in a browser."""
    from ctxgraph.view.visualizer import render_view, render_svg

    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    storage = get_storage(path)
    if storage is None:
        console.print(
            "[red]No graph found. Run [bold]ctx build[/bold] first.[/red]"
        )
        raise typer.Exit(1)

    if svg:
        content = render_svg(storage)
        suffix = ".svg"
    else:
        content = render_view(storage)
        suffix = ".html"

    if output:
        out_path = Path(output)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"Saved to [bold]{out_path}[/bold]")
    else:
        filename = f"graph{suffix}"
        out_path = path / ".ctxgraph" / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"Saved to [bold]{out_path}[/bold]")

    if open_browser and not svg:
        import webbrowser

        webbrowser.open(f"file://{out_path.absolute()}")
        console.print("Opened in browser.")


@app.command()
def serve(
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
    port: Optional[int] = typer.Option(
        None, "--port", "-p", help="Port for SSE mode (default: stdio mode)"
    ),
):
    """Start MCP server for dynamic graph queries (MCP protocol)."""
    from ctxgraph.mcp.server import run_server

    if port:
        console.print(f"[yellow]SSE mode on port {port} - not yet supported, falling back to stdio[/yellow]")
    run_server(repo_path)


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


@app.command()
def init(
    repo_path: Optional[str] = typer.Argument(
        None, help="Path to repository (default: current directory)"
    ),
):
    """Scaffold .ctxgraph directory with config and default skills."""
    from ctxgraph.config.init import init_project

    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    result = init_project(path)
    console.print(f"[green]Initialized .ctxgraph in: {result.parent}[/green]")


@app.command()
def ask(
    query: str = typer.Argument(..., help="Question about the codebase"),
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
    skill: Optional[str] = typer.Option(
        None, "--skill", "-s", help="Skill name to activate"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", help="LLM provider (ollama, claude, openai)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="LLM model name"
    ),
    graph: bool = typer.Option(
        False, "--graph", "-g", help="Show graph search results"
    ),
):
    """Ask a question about the codebase using the LLM."""
    import json as _json
    import urllib.request

    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    settings = Settings(path)

    if provider:
        settings._data["ai"]["provider"] = provider
    if model:
        settings._data["ai"]["model"] = model

    storage = get_storage(path)
    if storage is None:
        console.print(
            "[red]No graph found. Run [bold]ctx build[/bold] first.[/red]"
        )
        raise typer.Exit(1)

    mode_cfg = get_mode_config(ModelMode.from_str(settings.context_mode))
    skill_text = load_skill(path, skill) if skill else None

    capsule_text = render_capsule(
        storage,
        query,
        max_nodes=mode_cfg["max_nodes"],
        skill_context=skill_text,
    )

    if graph:
        results = search_relevant_nodes(
            storage, query, max_nodes=mode_cfg["max_nodes"], max_depth=mode_cfg["max_depth"],
        )
        if results:
            gtable = Table(title=f"Graph Results: {query}")
            gtable.add_column("Type", style="cyan")
            gtable.add_column("Name", style="green")
            gtable.add_column("Path", style="blue")
            gtable.add_column("Relevance", style="yellow")
            type_tag = {"file": "F", "class": "C", "function": "M", "module": "M"}
            for node, score in results:
                gtable.add_row(type_tag.get(node.type, "?"), node.name, node.path or "-", str(score))
            console.print(gtable)

    savings_data = compute_savings(path, capsule_text)
    console.print(render_savings_table(savings_data))

    provider_name = provider or settings.provider
    model_name = model or settings.model
    endpoint = settings.endpoint
    provider_cfg = settings.get_provider_config()

    system_msg = "You are an expert software engineer. Answer the user's question based on the provided context capsule."
    if skill_text:
        system_msg += f"\n\n{skill_text}"

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"Context Capsule:\n{capsule_text}\n\nQuestion: {query}"},
    ]

    body = _json.dumps({
        "model": model_name,
        "messages": messages,
        "stream": False,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
    }).encode("utf-8")

    chat_url = settings.get_chat_url()
    headers = {"Content-Type": "application/json"}
    api_key = settings.api_key
    if api_key:
        akh = provider_cfg.get("api_key_header", "Authorization")
        headers[akh] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(chat_url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        console.print(f"[red]LLM request failed: {e}[/red]")
        raise typer.Exit(1)

    answer = data.get("message", {}).get("content", "") or data.get("response", "")
    console.print(f"\n[bold cyan]Answer:[/bold cyan]\n{answer}")

    append_entry(path, {
        "query": query,
        "skill": skill,
        "provider": provider_name,
        "model": model_name,
        "raw_tokens": savings_data["raw_tokens"],
        "capsule_tokens": savings_data["capsule_tokens"],
        "json_tokens": savings_data["json_tokens"],
        "savings_pct": savings_data["savings_pct"],
        "answer_length": len(answer),
    })


@app.command()
def history(
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
    tail: int = typer.Option(
        10, "--tail", "-n", help="Number of recent entries"
    ),
    query_filter: Optional[str] = typer.Option(
        None, "--filter", "-f", help="Filter by query text"
    ),
    stats: bool = typer.Option(
        False, "--stats", help="Show aggregate statistics"
    ),
):
    """Show query history."""
    path = Path(repo_path).resolve() if repo_path else Path.cwd()

    if stats:
        s = get_stats(path)
        if s["total_queries"] == 0:
            console.print("[yellow]No history found.[/yellow]")
            return
        table = Table(title="Query History Stats")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Queries", str(s["total_queries"]))
        table.add_row("Total Raw Tokens", f"{s['total_raw_tokens']:,}")
        table.add_row("Total Tokens Saved", f"{s['total_tokens_saved']:,}")
        table.add_row("Avg Savings", f"{s['avg_savings_pct']}%")
        for prov, count in s.get("providers", {}).items():
            table.add_row(f"  Provider: {prov}", str(count))
        console.print(table)
        return

    entries = get_entries(path, tail=tail, query_filter=query_filter)
    if not entries:
        console.print("[yellow]No history found.[/yellow]")
        return

    table = Table(title=f"Query History (last {len(entries)})")
    table.add_column("Time", style="dim")
    table.add_column("Query", style="green")
    table.add_column("Savings", style="yellow")
    table.add_column("Provider", style="cyan")
    table.add_column("Skill", style="magenta")

    for e in reversed(entries):
        ts = e.get("ts", "").split("T")[0] if e.get("ts") else ""
        q = e.get("query", "")[:50]
        savings = f"{e.get('savings_pct', 0)}%"
        prov = e.get("provider", "-")
        sk = e.get("skill", "-") or "-"
        table.add_row(ts, q, savings, prov, sk)

    console.print(table)


@app.command()
def skill(
    action: str = typer.Argument(
        "list", help="Action: list, show, use"
    ),
    skill_name: Optional[str] = typer.Argument(
        None, help="Skill name"
    ),
    repo_path: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository path"
    ),
):
    """Manage skills."""
    path = Path(repo_path).resolve() if repo_path else Path.cwd()

    if action == "list":
        user_skills = discover_skills(path)
        builtin_skills = get_builtin_skills()

        table = Table(title="Available Skills")
        table.add_column("Source", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Preview", style="white")

        for name, content in builtin_skills.items():
            preview = content[:80].replace("\n", " ")
            table.add_row("builtin", name, preview)

        for name, content in user_skills.items():
            preview = content[:80].replace("\n", " ")
            table.add_row("user", name, preview)

        if not builtin_skills and not user_skills:
            console.print("[yellow]No skills found. Run [bold]ctx init[/bold] to add defaults.[/yellow]")
            return

        console.print(table)

    elif action == "show":
        if not skill_name:
            console.print("[red]Usage: ctx skill show <name>[/red]")
            raise typer.Exit(1)

        content = load_skill(path, skill_name)
        if content is None:
            builtin = get_builtin_skills()
            content = builtin.get(skill_name)

        if content is None:
            console.print(f"[red]Skill '{skill_name}' not found.[/red]")
            raise typer.Exit(1)

        console.print(f"[bold cyan]Skill: {skill_name}[/bold cyan]\n")
        console.print(content)

    else:
        console.print(f"[red]Unknown action: {action}. Use: list, show[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
