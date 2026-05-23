"""ctxgraph benchmark runner.

Usage:
    python benchmarks/run_benchmarks.py                          # run all
    python benchmarks/run_benchmarks.py --project tiny_app       # single project
    python benchmarks/run_benchmarks.py --project web_api --mode deep
    python benchmarks/run_benchmarks.py --ollama                 # also test LLM summaries

Output is written to benchmarks/results/ as JSON.
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ctxgraph.graph.builder import build_graph
from ctxgraph.graph.storage import Storage
from ctxgraph.graph.models import Graph
from ctxgraph.capsule.renderer import render_capsule
from ctxgraph.graph.query import generate_context_subgraph


PROJECTS_DIR = REPO_ROOT / "benchmarks" / "projects"
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

QUERIES = {
    "tiny_app":   ["calculator", "parse expression", "plugin history", "math operations"],
    "web_api":    ["user management", "JWT auth login", "rate limit", "blog posts", "admin routes"],
    "microsvc":   ["auth service", "payment billing", "notification email", "circuit breaker", "service discovery"],
}

MODES = ["fast", "balanced", "deep"]


def count_tokens(text: str) -> int:
    return len(text.split())


def build_and_capsule_tokens(project_name: str, query: str, mode: str = "balanced") -> dict:
    proj_dir = PROJECTS_DIR / project_name
    if not proj_dir.is_dir():
        raise FileNotFoundError(f"Project not found: {proj_dir}")

    db_path = RESULTS_DIR / f"{project_name}_{query.replace(' ', '_')}_{mode}.db"

    start = time.perf_counter()
    stats = build_graph(proj_dir, db_path=db_path)
    build_time = time.perf_counter() - start

    storage = Storage(db_path)
    storage.connect()

    all_nodes = storage.get_all_nodes()

    mode_configs = {"fast": 10, "balanced": 20, "deep": 40}
    max_nodes = mode_configs.get(mode, 20)

    capsule = render_capsule(storage, query, max_nodes=max_nodes)
    capsule_tokens = count_tokens(capsule)

    nodes, edges = generate_context_subgraph(storage, query, max_nodes=max_nodes)
    edge_count = len(edges)

    file_nodes = [n for n in all_nodes if n.type == "file"]
    total_raw_tokens = 0
    raw_files_count = 0
    for fn in file_nodes:
        fp = proj_dir / (fn.path or "")
        if fp.is_file():
            try:
                total_raw_tokens += count_tokens(fp.read_text(encoding="utf-8", errors="replace"))
                raw_files_count += 1
            except Exception:
                pass

    storage.close()

    return {
        "project": project_name,
        "query": query,
        "mode": mode,
        "build_time_ms": round(build_time * 1000, 2),
        "total_nodes": stats.get("total_nodes", 0),
        "total_edges": stats.get("total_edges", 0),
        "capsule_nodes": len(nodes),
        "capsule_edges": edge_count,
        "capsule_tokens": capsule_tokens,
        "raw_file_count": raw_files_count,
        "raw_tokens": total_raw_tokens,
        "savings_pct": round((1 - capsule_tokens / max(total_raw_tokens, 1)) * 100, 1),
        "capsule_chars": len(capsule),
    }


def run_json_vs_dsl(project_name: str, query: str) -> dict:
    import json as json_lib
    proj_dir = PROJECTS_DIR / project_name
    db_path = RESULTS_DIR / f"json_vs_dsl_{project_name}.db"

    build_graph(proj_dir, db_path=db_path)
    storage = Storage(db_path)
    storage.connect()

    nodes, edges = generate_context_subgraph(storage, query, max_nodes=20)
    dsl = render_capsule(storage, query, max_nodes=20)

    json_data = {
        "query": query,
        "nodes": [{"id": n.id, "type": n.type, "name": n.name, "path": n.path} for n in nodes],
        "edges": [{"source": s, "target": t, "relation": r} for s, t, r in edges[:30]],
    }
    json_str = json_lib.dumps(json_data, indent=2)

    dsl_tokens = count_tokens(dsl)
    json_tokens = count_tokens(json_str)
    ratio = round(json_tokens / max(dsl_tokens, 1), 1)

    storage.close()
    return {
        "project": project_name,
        "query": query,
        "dsl_tokens": dsl_tokens,
        "json_tokens": json_tokens,
        "ratio": f"{ratio}x",
        "dsl_chars": len(dsl),
        "json_chars": len(json_str),
    }


def run_all_benchmarks(projects: list[str], modes: list[str], with_ollama: bool = False):
    results = {}
    dsl_results = []

    for proj in projects:
        print(f"\n{'='*60}")
        print(f"  Project: {proj}")
        print(f"{'='*60}")

        for query in QUERIES.get(proj, ["main"]):
            for mode in modes:
                print(f"    query='{query}' mode={mode} ... ", end="", flush=True)
                try:
                    r = build_and_capsule_tokens(proj, query, mode)
                    results[f"{proj}/{query}/{mode}"] = r
                    print(f"OK ({r['capsule_tokens']} tok, {r['savings_pct']}% saved)")
                except Exception as e:
                    print(f"FAIL: {e}")

    print(f"\n{'='*60}")
    print("  JSON vs DSL comparison")
    print(f"{'='*60}")
    for proj in projects:
        for query in QUERIES.get(proj, ["main"])[:2]:
            print(f"    {proj} / '{query}' ... ", end="", flush=True)
            try:
                r = run_json_vs_dsl(proj, query)
                dsl_results.append(r)
                print(f"OK (DSL={r['dsl_tokens']} tok, JSON={r['json_tokens']} tok, ratio={r['ratio']})")
            except Exception as e:
                print(f"FAIL: {e}")

    with open(RESULTS_DIR / "benchmark_results.json", "w") as f:
        json.dump({"capsule": results, "json_vs_dsl": dsl_results}, f, indent=2)

    print(f"\nResults saved to {RESULTS_DIR / 'benchmark_results.json'}")
    return results, dsl_results


def print_summary(results: dict, dsl_results: list):
    print(f"\n{'='*70}")
    print(f"  BENCHMARK SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Project':<12} {'Query':<22} {'Mode':<10} {'CapsuleTok':<12} {'RawTok':<10} {'Saved%':<8} {'BuildMs':<10}")
    print(f"  {'-'*12} {'-'*22} {'-'*10} {'-'*12} {'-'*10} {'-'*8} {'-'*10}")

    for key, r in sorted(results.items()):
        print(f"  {r['project']:<12} {r['query'][:20]:<22} {r['mode']:<10} {r['capsule_tokens']:<12} {r['raw_tokens']:<10} {r['savings_pct']:<8} {r['build_time_ms']:<10}")

    print(f"\n  JSON vs DSL Token Efficiency:")
    print(f"  {'Project':<12} {'Query':<22} {'DSL Tok':<10} {'JSON Tok':<10} {'Ratio':<8}")
    print(f"  {'-'*12} {'-'*22} {'-'*10} {'-'*10} {'-'*8}")
    for r in dsl_results:
        print(f"  {r['project']:<12} {r['query'][:20]:<22} {r['dsl_tokens']:<10} {r['json_tokens']:<10} {r['ratio']:<8}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ctxgraph benchmark runner")
    parser.add_argument("--project", help="Run only this project (tiny_app, web_api, microsvc)")
    parser.add_argument("--mode", choices=MODES, help="Run only this mode (fast, balanced, deep)")
    parser.add_argument("--ollama", action="store_true", help="Test with Ollama provider")
    args = parser.parse_args()

    projects = [args.project] if args.project else ["tiny_app", "web_api", "microsvc"]
    modes = [args.mode] if args.mode else MODES

    results, dsl_res = run_all_benchmarks(projects, modes, with_ollama=args.ollama)
    print_summary(results, dsl_res)
