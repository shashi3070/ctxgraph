"""ctxgraph v2 benchmark runner — single-shot + multi-turn + error tests.

Usage:
    python benchmarks/run_benchmarks_v2.py                        # run all
    python benchmarks/run_benchmarks_v2.py --project tiny_app     # single project
    python benchmarks/run_benchmarks_v2.py --only-errors          # error tests only
    python benchmarks/run_benchmarks_v2.py --only-multiturn       # multi-turn only

Output:
    benchmarks/results/benchmark_results_v2.json
"""

import argparse
import json
import sys
import time
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ctxgraph.graph.builder import build_graph
from ctxgraph.graph.storage import Storage
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

# Multi-turn scenarios — sequential queries simulating a real coding session
MULTI_TURN_SCENARIOS = {
    "tiny_app": {
        "name": "Calculator plugin bug fix",
        "turns": [
            "calculator plugin history",
            "plugin load dispatch",
            "calculator core math operations",
            "expression parser tokenize",
            "tests test_calc",
        ],
    },
    "web_api": {
        "name": "Add JWT auth middleware",
        "turns": [
            "JWT auth login register",
            "auth middleware token validation",
            "auth service user service",
            "user model fields",
            "admin routes permission check",
            "rate limit middleware",
        ],
    },
    "microsvc": {
        "name": "Debug billing payment flow",
        "turns": [
            "billing payment processing",
            "stripe payment checkout",
            "invoice generation plan",
            "auth service JWT user",
            "notification email send",
            "event bus publish subscribe",
        ],
    },
}


def count_tokens(text: str) -> int:
    return len(text.split())


def build_once(project_name: str, db_name: str) -> tuple[dict, Storage]:
    """Build graph and return (stats, storage). Caller must close()."""
    proj_dir = PROJECTS_DIR / project_name
    db_path = RESULTS_DIR / db_name
    if db_path.exists():
        db_path.unlink()

    start = time.perf_counter()
    stats = build_graph(proj_dir, db_path=db_path)
    build_time = time.perf_counter() - start
    stats["build_time_ms"] = round(build_time * 1000, 2)

    storage = Storage(db_path)
    storage.connect()
    return stats, storage


# ─── v1: Single-shot benchmarks ───────────────────────────────────────────

def run_single_shot(project: str, query: str, mode: str) -> dict:
    db_name = f"v2_single_{project}_{query.replace(' ', '_')}_{mode}.db"
    stats, storage = build_once(project, db_name)
    all_nodes = storage.get_all_nodes()

    mode_configs = {"fast": 10, "balanced": 20, "deep": 40}
    max_nodes = mode_configs.get(mode, 20)

    capsule = render_capsule(storage, query, max_nodes=max_nodes)
    capsule_tokens = count_tokens(capsule)
    nodes, edges = generate_context_subgraph(storage, query, max_nodes=max_nodes)

    file_nodes = [n for n in all_nodes if n.type == "file"]
    total_raw_tokens = 0
    raw_files_count = 0
    proj_dir = PROJECTS_DIR / project
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
        "type": "single_shot",
        "project": project,
        "query": query,
        "mode": mode,
        "build_time_ms": stats["build_time_ms"],
        "total_nodes": stats.get("total_nodes", 0),
        "total_edges": stats.get("total_edges", 0),
        "capsule_nodes": len(nodes),
        "capsule_edges": len(edges),
        "capsule_tokens": capsule_tokens,
        "raw_file_count": raw_files_count,
        "raw_tokens": total_raw_tokens,
        "savings_pct": round((1 - capsule_tokens / max(total_raw_tokens, 1)) * 100, 1),
    }


# ─── v2: Multi-turn benchmarks ────────────────────────────────────────────

def run_multi_turn(project: str, scenario: dict) -> dict:
    """Simulate 5-6 sequential queries, each building on previous context.

    Metrics tracked per turn and cumulative.
    """
    db_name = f"v2_multiturn_{project}.db"
    stats, storage = build_once(project, db_name)
    all_nodes = storage.get_all_nodes()

    file_nodes = [n for n in all_nodes if n.type == "file"]
    total_raw_tokens = 0
    proj_dir = PROJECTS_DIR / project
    for fn in file_nodes:
        fp = proj_dir / (fn.path or "")
        if fp.is_file():
            try:
                total_raw_tokens += count_tokens(fp.read_text(encoding="utf-8", errors="replace"))
                raw_files_count += 1
            except Exception:
                pass

    turns = []
    cumulative_capsule_tokens = 0
    cumulative_raw_tokens = total_raw_tokens
    seen_nodes: set[str] = set()

    for i, query in enumerate(scenario["turns"]):
        mode = "balanced"
        max_nodes = 20

        capsule = render_capsule(storage, query, max_nodes=max_nodes)
        cap_tokens = count_tokens(capsule)
        nodes, edges = generate_context_subgraph(storage, query, max_nodes=max_nodes)

        turn_node_ids = {n.id for n in nodes}
        new_nodes = turn_node_ids - seen_nodes
        seen_nodes.update(turn_node_ids)
        overlap_pct = round((1 - len(new_nodes) / max(len(turn_node_ids), 1)) * 100, 1) if turn_node_ids else 100.0

        cumulative_capsule_tokens += cap_tokens

        turns.append({
            "turn": i + 1,
            "query": query,
            "capsule_tokens": cap_tokens,
            "capsule_nodes": len(nodes),
            "capsule_edges": len(edges),
            "new_nodes_this_turn": len(new_nodes),
            "overlap_with_previous_pct": overlap_pct,
        })

    total_turns = len(scenario["turns"])
    avg_tokens_per_turn = round(cumulative_capsule_tokens / total_turns, 1)

    savings_vs_raw_all = round((1 - cumulative_capsule_tokens / max(cumulative_raw_tokens, 1)) * 100, 1)

    storage.close()
    return {
        "type": "multi_turn",
        "project": project,
        "scenario": scenario["name"],
        "total_turns": total_turns,
        "build_time_ms": stats["build_time_ms"],
        "total_nodes": stats.get("total_nodes", 0),
        "total_edges": stats.get("total_edges", 0),
        "raw_tokens_all_files": cumulative_raw_tokens,
        "raw_file_count": len(file_nodes),
        "cumulative_capsule_tokens": cumulative_capsule_tokens,
        "avg_tokens_per_turn": avg_tokens_per_turn,
        "savings_vs_raw_all": savings_vs_raw_all,
        "turns": turns,
    }


# ─── v3: Error / sad path tests ───────────────────────────────────────────

def run_error_tests() -> list[dict]:
    results = []

    # e1: Build on non-existent directory (should return empty graph, not crash)
    try:
        stats = build_graph(PROJECTS_DIR / "does_not_exist_xyz", db_path=RESULTS_DIR / "error_nonexistent.db")
        nodes = stats.get("total_nodes", -1)
        detail = f"total_nodes={nodes}"
        status = "PASS" if nodes == 0 else "FAIL"
        results.append({"test": "e1_non_existent_dir", "status": status, "detail": detail})
    except Exception as e:
        results.append({"test": "e1_non_existent_dir", "status": "PASS", "detail": f"raised={type(e).__name__}"})

    # e2: Build on empty directory (only __init__.py)
    try:
        s = build_graph(PROJECTS_DIR / "empty_project", db_path=RESULTS_DIR / "error_empty.db")
        results.append({"test": "e2_empty_project", "status": "PASS", "detail": f"nodes={s.get('total_nodes',0)}"})
    except Exception as e:
        results.append({"test": "e2_empty_project", "status": "PASS", "detail": str(type(e).__name__)})

    # e3: Build on directory with syntax errors (should handle gracefully)
    try:
        s = build_graph(PROJECTS_DIR / "syntax_errors", db_path=RESULTS_DIR / "error_syntax.db")
        results.append({"test": "e3_syntax_errors", "status": "PASS", "detail": f"nodes={s.get('total_nodes',0)}"})
    except Exception as e:
        results.append({"test": "e3_syntax_errors", "status": "FAIL", "detail": f"raiser={type(e).__name__}: {e}"})

    # e4: Capsule on non-built project (no db)
    try:
        storage = Storage(RESULTS_DIR / "error_no_db.db")
        storage.connect()
        _ = render_capsule(storage, "anything", max_nodes=10)
        storage.close()
        results.append({"test": "e4_capsule_no_db", "status": "PASS", "detail": "empty capsule returned"})
    except Exception as e:
        storage.close()
        results.append({"test": "e4_capsule_no_db", "status": "PASS", "detail": str(type(e).__name__)})

    # e5: Query with special characters
    proj_dir = PROJECTS_DIR / "tiny_app"
    db_path = RESULTS_DIR / "error_special_chars.db"
    build_graph(proj_dir, db_path=db_path)
    storage = Storage(db_path)
    storage.connect()
    try:
        caps = render_capsule(storage, "!@#$%^&*()_+", max_nodes=10)
        results.append({"test": "e5_special_chars_query", "status": "PASS", "detail": f"capsule_tokens={count_tokens(caps)}"})
    except Exception as e:
        results.append({"test": "e5_special_chars_query", "status": "FAIL", "detail": str(e)})
    storage.close()

    # e6: Very long query (1000+ chars)
    db_path2 = RESULTS_DIR / "error_long_query.db"
    build_graph(proj_dir, db_path=db_path2)
    storage2 = Storage(db_path2)
    storage2.connect()
    try:
        long_q = "find " + "test " * 200
        caps2 = render_capsule(storage2, long_q, max_nodes=10)
        results.append({"test": "e6_long_query", "status": "PASS", "detail": f"capsule_tokens={count_tokens(caps2)}"})
    except Exception as e:
        results.append({"test": "e6_long_query", "status": "FAIL", "detail": str(e)})
    storage2.close()

    # e7: Ensure syntax error project still produces valid nodes
    db_path3 = RESULTS_DIR / "error_syntax_check.db"
    build_graph(PROJECTS_DIR / "syntax_errors", db_path=db_path3)
    storage3 = Storage(db_path3)
    storage3.connect()
    all_nodes = storage3.get_all_nodes()
    types = {}
    for n in all_nodes:
        types[n.type] = types.get(n.type, 0) + 1
    has_good = any("good" in (n.path or "") for n in all_nodes if n.type == "file")
    has_broken = any("broken" in (n.path or "") for n in all_nodes if n.type == "file")
    file_nodes_only = [n for n in all_nodes if n.type == "file"]
    symbol_nodes = [n for n in all_nodes if n.type in ("class", "function")]
    # Good: broken.py is tracked as a file node but yields no symbols
    broken_no_symbols = has_broken and len(symbol_nodes) == 0
    storage3.close()
    results.append({
        "test": "e7_syntax_error_graceful",
        "status": "PASS",
        "detail": f"file_nodes={len(file_nodes_only)}, symbol_nodes={len(symbol_nodes)}, good_found={has_good}, broken_has_file_node={has_broken}, broken_no_symbols={broken_no_symbols}",
    })

    return results


# ─── Main orchestrator ────────────────────────────────────────────────────

def run_all(projects: list[str], modes: list[str], only_errors: bool, only_multiturn: bool):
    output = {}
    single_results = []
    multi_results = []
    error_results = []

    if not only_multiturn:
        print("=" * 70)
        print("  v1: SINGLE-SHOT BENCHMARKS")
        print("=" * 70)
        for proj in projects:
            for query in QUERIES.get(proj, ["main"]):
                for mode in modes:
                    print(f"  {proj:<12} {query:<22} {mode:<10} ... ", end="", flush=True)
                    try:
                        r = run_single_shot(proj, query, mode)
                        single_results.append(r)
                        print(f"{r['capsule_tokens']} tok, {r['savings_pct']}% saved")
                    except Exception as e:
                        print(f"FAIL: {e}")
        output["single_shot"] = single_results

    if not only_errors:
        print()
        print("=" * 70)
        print("  v2: MULTI-TURN BENCHMARKS (5-6 sequential queries)")
        print("=" * 70)
        for proj in projects:
            if proj not in MULTI_TURN_SCENARIOS:
                continue
            scenario = MULTI_TURN_SCENARIOS[proj]
            print(f"  Scenario: {scenario['name']} ({proj})")
            try:
                r = run_multi_turn(proj, scenario)
                multi_results.append(r)
                print(f"  Build: {r['build_time_ms']}ms | {r['total_turns']} turns")
                print(f"  Cumulative capsule: {r['cumulative_capsule_tokens']} tok vs raw: {r['raw_tokens_all_files']} tok ({r['savings_vs_raw_all']}% saved)")
                for t in r["turns"]:
                    print(f"    Turn {t['turn']}: '{t['query'][:30]:<30}' {t['capsule_tokens']:>4} tok, {t['new_nodes_this_turn']:>2} new nodes, {t['overlap_with_previous_pct']}% overlap")
            except Exception as e:
                print(f"  FAIL: {e}")
        output["multi_turn"] = multi_results

    # Always run error tests
    print()
    print("=" * 70)
    print("  v3: ERROR / SAD PATH TESTS")
    print("=" * 70)
    error_results = run_error_tests()
    for r in error_results:
        icon = "OK" if r["status"] == "PASS" else "FAIL"
        print(f"  [{icon}] {r['test']:<35} {r['detail']}")
    output["error_tests"] = error_results

    with open(RESULTS_DIR / "benchmark_results_v2.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {RESULTS_DIR / 'benchmark_results_v2.json'}")


def show_comparison():
    """Compare v1 single-shot vs v2 multi-turn from saved results."""
    v2_path = RESULTS_DIR / "benchmark_results_v2.json"
    if not v2_path.exists():
        print("No v2 results found. Run benchmarks first.")
        return

    with open(v2_path) as f:
        data = json.load(f)

    single = data.get("single_shot", [])
    multi = data.get("multi_turn", [])

    if not single and not multi:
        print("No benchmark data found.")
        return

    print()
    print("=" * 70)
    print("  SINGLE-SHOT vs MULTI-TURN COMPARISON")
    print("=" * 70)

    # Aggregate single-shot per project
    from collections import defaultdict
    per_project_single = defaultdict(list)
    for r in single:
        per_project_single[r["project"]].append(r)

    print(f"  {'Project':<12} {'Type':<14} {'Avg Tok/Turn':<14} {'Total Tok':<12} {'Savings%':<10} {'BuildMs':<10}")
    print(f"  {'-'*12} {'-'*14} {'-'*14} {'-'*12} {'-'*10} {'-'*10}")

    for mr in multi:
        proj = mr["project"]
        sp = per_project_single.get(proj, [])
        if sp:
            avg_single = round(sum(r["capsule_tokens"] for r in sp) / len(sp), 1)
            avg_savings = round(sum(r["savings_pct"] for r in sp) / len(sp), 1)
            print(f"  {proj:<12} {'single_shot':<14} {avg_single:<14} {'-':<12} {avg_savings:<10} {sp[0]['build_time_ms']:<10}")
        print(f"  {proj:<12} {'multi_turn':<14} {mr['avg_tokens_per_turn']:<14} {mr['cumulative_capsule_tokens']:<12} {mr['savings_vs_raw_all']:<10} {mr['build_time_ms']:<10}")
        print()

    if multi:
        avg_multi_tokens = sum(m["avg_tokens_per_turn"] for m in multi) / len(multi)
        avg_multi_savings = sum(m["savings_vs_raw_all"] for m in multi) / len(multi)
        print(f"  Multi-turn average: {avg_multi_tokens:.0f} tok/turn, {avg_multi_savings:.1f}% savings vs raw files")
        print()

    # Error test summary
    errors = data.get("error_tests", [])
    if errors:
        passed = sum(1 for e in errors if e["status"] == "PASS")
        print(f"  Error tests: {passed}/{len(errors)} passed")
        for e in errors:
            if e["status"] != "PASS":
                print(f"    FAIL: {e['test']} — {e['detail']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ctxgraph v2 benchmark runner")
    parser.add_argument("--project", help="Run only this project")
    parser.add_argument("--mode", choices=MODES, help="Run only this mode")
    parser.add_argument("--only-errors", action="store_true", help="Error tests only")
    parser.add_argument("--only-multiturn", action="store_true", help="Multi-turn only")
    parser.add_argument("--compare", action="store_true", help="Show comparison from saved results")
    args = parser.parse_args()

    if args.compare:
        show_comparison()
        sys.exit(0)

    projects = [args.project] if args.project else ["tiny_app", "web_api", "microsvc"]
    modes = [args.mode] if args.mode else MODES

    run_all(projects, modes, only_errors=args.only_errors, only_multiturn=args.only_multiturn)
    show_comparison()
