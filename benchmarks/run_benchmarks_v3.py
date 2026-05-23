"""ctxgraph v3 benchmark — 25 single-shot + 25 multi-turn (5-10 turns each).

Usage:
    python benchmarks/run_benchmarks_v3.py                      # run all
    python benchmarks/run_benchmarks_v3.py --single-only        # 25 single-shot only
    python benchmarks/run_benchmarks_v3.py --multiturn-only     # 25 multi-turn only
    python benchmarks/run_benchmarks_v3.py --project tiny_app   # single project

Output: benchmarks/results/benchmark_results_v3.json
"""

import argparse
import json
import sys
import time
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ctxgraph.graph.builder import build_graph
from ctxgraph.graph.storage import Storage
from ctxgraph.capsule.renderer import render_capsule
from ctxgraph.graph.query import generate_context_subgraph

PROJECTS_DIR = REPO_ROOT / "benchmarks" / "projects"
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def count_tokens(text: str) -> int:
    return len(text.split())


def build_once(project_name: str, db_name: str) -> tuple[dict, Storage]:
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


def get_raw_tokens(project: str) -> tuple[int, int]:
    proj_dir = PROJECTS_DIR / project
    total = 0
    count = 0
    for fp in proj_dir.rglob("*.py"):
        if fp.is_file():
            try:
                total += count_tokens(fp.read_text(encoding="utf-8", errors="replace"))
                count += 1
            except Exception:
                pass
    return total, count


# ─── 25 SINGLE-SHOT QUERIES ────────────────────────────────────────────────

SINGLE_SHOT_QUERIES = {
    "tiny_app": [
        "calculator add subtract multiply",
        "expression parser tokenize",
        "plugin system history logging",
        "math operations core functions",
        "main entry point CLI",
        "error handling division",
        "test calculator functions",
        "import dependencies",
    ],
    "web_api": [
        "user management CRUD",
        "JWT auth login register",
        "rate limit middleware",
        "blog posts publish",
        "admin routes permission",
        "password hashing auth service",
        "middleware pipeline",
        "user model fields",
        "post service pagination",
    ],
    "microsvc": [
        "auth service JWT OAuth",
        "billing payment stripe",
        "notification email push",
        "circuit breaker pattern",
        "service registry discovery",
        "event bus pub sub",
        "distributed tracing",
        "retry backoff timeout",
    ],
}

# ─── 25 MULTI-TURN SCENARIOS (5-10 turns each) ─────────────────────────────

MULTI_TURN_SCENARIOS = {
    "tiny_app": [
        {
            "name": "Fix divide-by-zero in calculator",
            "turns": [
                "calculator divide math error",
                "core division function",
                "error handling try except",
                "plugin error logging",
                "test division edge cases",
            ],
        },
        {
            "name": "Add new square root plugin",
            "turns": [
                "plugin system load dispatch",
                "calculator core math operations",
                "plugin base class interface",
                "history plugin example",
                "test plugin registration",
                "main entry CLI args",
            ],
        },
        {
            "name": "Fix expression parser bug",
            "turns": [
                "expression parser tokenize",
                "parser token types regex",
                "parse error handling",
                "calculator evaluate expression",
                "test parser expressions",
            ],
        },
        {
            "name": "Refactor calculator error handling",
            "turns": [
                "error handling calculator",
                "core math exceptions",
                "parser validation errors",
                "plugin error callback",
                "main CLI error messages",
                "test error cases",
            ],
        },
        {
            "name": "Add power function to calculator",
            "turns": [
                "calculator core functions",
                "add power exponent",
                "expression parser power operator",
                "test power edge cases",
                "plugin history log power",
            ],
        },
        {
            "name": "Improve CLI help and usage",
            "turns": [
                "main CLI argument parse",
                "CLI help text format",
                "calculator operation list",
                "plugin list command",
                "test CLI integration",
            ],
        },
        {
            "name": "Add memory store plugin",
            "turns": [
                "plugin system history",
                "plugin base class API",
                "memory storage variables",
                "calculator use memory",
                "test memory plugin",
                "CLI memory commands",
            ],
        },
        {
            "name": "Secure calculator input validation",
            "turns": [
                "expression parser tokenize",
                "input validation sanitize",
                "parser error handling",
                "calculator safe eval",
                "test invalid input",
                "main CLI input loop",
            ],
        },
    ],
    "web_api": [
        {
            "name": "Add JWT refresh token flow",
            "turns": [
                "auth service JWT token",
                "JWT create decode verify",
                "auth middleware validate",
                "user session management",
                "login register routes",
                "refresh token endpoint",
                "test auth refresh flow",
            ],
        },
        {
            "name": "Fix rate limiter bucket refill",
            "turns": [
                "rate limit middleware",
                "token bucket algorithm",
                "rate limit config settings",
                "middleware pipeline order",
                "test rate limiting",
                "rate limit headers response",
            ],
        },
        {
            "name": "Add user role permissions",
            "turns": [
                "user model fields role",
                "user service create update",
                "auth middleware role check",
                "admin routes permission guard",
                "user routes role filter",
                "test role based access",
                "migration add role field",
            ],
        },
        {
            "name": "Optimize blog post pagination",
            "turns": [
                "post service list query",
                "post model fields sort",
                "post routes pagination",
                "user service author posts",
                "test post pagination",
                "admin routes all posts",
            ],
        },
        {
            "name": "Implement password reset flow",
            "turns": [
                "auth service password hash",
                "user service find by email",
                "reset token generate verify",
                "auth routes reset password",
                "email notification service",
                "test password reset",
                "rate limit reset attempts",
            ],
        },
        {
            "name": "Build admin analytics dashboard",
            "turns": [
                "admin routes dashboard",
                "user service stats count",
                "post service analytics",
                "auth service login history",
                "middleware admin only",
                "test admin analytics",
            ],
        },
        {
            "name": "Add API versioning support",
            "turns": [
                "routes version prefix",
                "middleware accept header",
                "config api version",
                "user routes backward compat",
                "post routes version check",
                "test versioned endpoints",
            ],
        },
        {
            "name": "Implement request body validation",
            "turns": [
                "user model validation",
                "post model fields required",
                "services input sanitize",
                "routes error response",
                "middleware validation",
                "test invalid request body",
            ],
        },
        {
            "name": "Add audit logging middleware",
            "turns": [
                "middleware logging request",
                "auth service user context",
                "audit log model storage",
                "middleware pipeline order",
                "admin routes audit trail",
                "test audit entries",
                "config audit enabled",
            ],
        },
    ],
    "microsvc": [
        {
            "name": "Add OAuth2 GitHub provider",
            "turns": [
                "auth OAuth service",
                "auth JWT token create",
                "oauth authorize callback",
                "user model external id",
                "auth server routes",
                "test OAuth flow",
                "config OAuth settings",
                "shared logger debug",
            ],
        },
        {
            "name": "Fix billing invoice rounding",
            "turns": [
                "billing invoice generate",
                "billing payment process",
                "billing plans pricing",
                "invoice model fields",
                "billing server routes",
                "test invoice rounding",
                "shared events invoice created",
            ],
        },
        {
            "name": "Add SMS notification provider (Twilio)",
            "turns": [
                "notification SMS send",
                "notification provider base",
                "notification email SMTP",
                "notification templates",
                "notification server routes",
                "test SMS notification",
            ],
        },
        {
            "name": "Tune circuit breaker thresholds",
            "turns": [
                "circuit breaker pattern",
                "circuit breaker state open closed",
                "shared retry backoff",
                "shared metrics counter",
                "shared events circuit trip",
                "test circuit breaker",
                "config circuit thresholds",
            ],
        },
        {
            "name": "Add health check to service discovery",
            "turns": [
                "gateway service discovery",
                "discovery register heartbeat",
                "gateway router health",
                "shared retry health check",
                "gateway middleware timeout",
                "test discovery health",
            ],
        },
        {
            "name": "Implement event bus retry mechanism",
            "turns": [
                "shared events pub sub",
                "shared retry exponential backoff",
                "shared logger structured",
                "billing events invoice created",
                "notification events user registered",
                "test event retry",
                "config retry max attempts",
                "shared metrics event count",
            ],
        },
        {
            "name": "Add distributed tracing headers",
            "turns": [
                "shared tracing trace id",
                "gateway middleware propagate",
                "auth server tracing",
                "billing server tracing",
                "shared logger trace context",
                "test tracing propagation",
                "shared metrics trace duration",
            ],
        },
        {
            "name": "Build metrics endpoint for Prometheus",
            "turns": [
                "shared metrics counter gauge",
                "gateway metrics requests",
                "auth metrics login count",
                "billing metrics revenue",
                "shared metrics endpoint",
                "test metrics output",
                "config metrics enabled",
                "notification metrics sent",
            ],
        },
    ],
}

# Validate counts
assert sum(len(v) for v in SINGLE_SHOT_QUERIES.values()) == 25, f"Expected 25 single-shot, got {sum(len(v) for v in SINGLE_SHOT_QUERIES.values())}"
assert sum(len(v) for v in MULTI_TURN_SCENARIOS.values()) == 25, f"Expected 25 multi-turn, got {sum(len(v) for v in MULTI_TURN_SCENARIOS.values())}"


# ─── SINGLE-SHOT RUNNER ────────────────────────────────────────────────────

def run_single_shot(project: str, query: str, mode: str = "balanced") -> dict:
    db_name = f"v3_single_{project}_{query.replace(' ', '_')[:30]}_{mode}.db"
    stats, storage = build_once(project, db_name)
    all_nodes = storage.get_all_nodes()
    mode_configs = {"fast": 5, "balanced": 10, "deep": 20}
    max_nodes = mode_configs.get(mode, 10)

    capsule = render_capsule(storage, query, max_nodes=max_nodes)
    capsule_tokens = count_tokens(capsule)
    nodes, edges = generate_context_subgraph(storage, query, max_nodes=max_nodes)

    raw_total, raw_count = get_raw_tokens(project)
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
        "raw_tokens": raw_total,
        "raw_file_count": raw_count,
        "savings_pct": round((1 - capsule_tokens / max(raw_total, 1)) * 100, 1),
    }


# ─── MULTI-TURN RUNNER ─────────────────────────────────────────────────────

def run_multi_turn(project: str, scenario: dict) -> dict:
    db_name = f"v3_multiturn_{project}_{scenario['name'].replace(' ', '_')[:30]}.db"
    stats, storage = build_once(project, db_name)
    raw_total, raw_count = get_raw_tokens(project)

    turns = []
    cumulative_capsule_tokens = 0
    seen_nodes: set[str] = set()

    for i, query in enumerate(scenario["turns"]):
        mode = "balanced"
        max_nodes = 10

        capsule = render_capsule(storage, query, max_nodes=max_nodes)
        cap_tokens = count_tokens(capsule)
        nodes, edges = generate_context_subgraph(storage, query, max_nodes=max_nodes)

        turn_node_ids = {n.id for n in nodes}
        new_nodes = turn_node_ids - seen_nodes
        overlap_pct = round((1 - len(new_nodes) / max(len(turn_node_ids), 1)) * 100, 1) if turn_node_ids else 100.0
        seen_nodes.update(turn_node_ids)

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
    savings_vs_raw = round((1 - cumulative_capsule_tokens / max(raw_total, 1)) * 100, 1)
    unique_nodes_total = len(seen_nodes)
    node_coverage_pct = round(unique_nodes_total / max(stats.get("total_nodes", 1), 1) * 100, 1)

    storage.close()
    return {
        "type": "multi_turn",
        "project": project,
        "scenario": scenario["name"],
        "total_turns": total_turns,
        "build_time_ms": stats["build_time_ms"],
        "total_nodes_in_graph": stats.get("total_nodes", 0),
        "total_edges_in_graph": stats.get("total_edges", 0),
        "raw_tokens_all_files": raw_total,
        "raw_file_count": raw_count,
        "cumulative_capsule_tokens": cumulative_capsule_tokens,
        "avg_tokens_per_turn": avg_tokens_per_turn,
        "savings_vs_raw_pct": savings_vs_raw,
        "unique_nodes_visited": unique_nodes_total,
        "graph_coverage_pct": node_coverage_pct,
        "turns": turns,
    }


# ─── MAIN ───────────────────────────────────────────────────────────────────

def run_all(only_single: bool, only_multiturn: bool, project_filter: str | None):
    output = {"single_shot": [], "multi_turn": []}

    for proj in ["tiny_app", "web_api", "microsvc"]:
        if project_filter and proj != project_filter:
            continue

        raw_total, raw_count = get_raw_tokens(proj)
        print(f"\n{'='*60}")
        print(f"  {proj} ({raw_count} files, {raw_total} raw tokens)")
        print(f"{'='*60}")

        # Single-shot
        if not only_multiturn:
            print(f"  --- 25 single-shot queries ---")
            for query in SINGLE_SHOT_QUERIES[proj]:
                print(f"    {query:<40} ... ", end="", flush=True)
                try:
                    r = run_single_shot(proj, query)
                    output["single_shot"].append(r)
                    print(f"{r['capsule_tokens']:>4} tok, {r['savings_pct']}% saved")
                except Exception as e:
                    print(f"FAIL: {e}")

        # Multi-turn
        if not only_single:
            print(f"  --- {len(MULTI_TURN_SCENARIOS[proj])} multi-turn scenarios ---")
            for scenario in MULTI_TURN_SCENARIOS[proj]:
                print(f"    {scenario['name'][:40]:<40} ... ", end="", flush=True)
                try:
                    r = run_multi_turn(proj, scenario)
                    output["multi_turn"].append(r)
                    print(f"{r['total_turns']} turns, {r['cumulative_capsule_tokens']:>4} tot tok, {r['savings_vs_raw_pct']}% saved, {r['graph_coverage_pct']}% graph covered")
                except Exception as e:
                    print(f"FAIL: {e}")

    with open(RESULTS_DIR / "benchmark_results_v3.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {RESULTS_DIR / 'benchmark_results_v3.json'}")
    return output


def print_summary(output: dict):
    ss = output.get("single_shot", [])
    mt = output.get("multi_turn", [])

    print(f"\n{'='*70}")
    print(f"  BENCHMARK v3 SUMMARY")
    print(f"{'='*70}")

    if ss:
        print(f"\n  SINGLE-SHOT (25 cases)")
        print(f"  {'Project':<12} {'Query':<38} {'Tok':<6} {'Saved%':<8}")
        print(f"  {'-'*12} {'-'*38} {'-'*6} {'-'*8}")
        for r in ss:
            print(f"  {r['project']:<12} {r['query'][:36]:<38} {r['capsule_tokens']:<6} {r['savings_pct']:<7}%")
        avg_ss = round(sum(r["savings_pct"] for r in ss) / len(ss), 1)
        avg_tok = round(sum(r["capsule_tokens"] for r in ss) / len(ss), 1)
        print(f"  {'-'*64}")
        print(f"  Average: {avg_tok} tok/case, {avg_ss}% savings across {len(ss)} queries")
        print(f"  {'-'*64}")

    if mt:
        print(f"\n  MULTI-TURN (25 scenarios, 5-10 turns each)")
        print(f"  {'Project':<12} {'Scenario':<35} {'Turns':<6} {'TotTok':<8} {'AvgTok':<8} {'Saved%':<8} {'Cover%':<8}")
        print(f"  {'-'*12} {'-'*35} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
        for r in mt:
            print(f"  {r['project']:<12} {r['scenario'][:33]:<35} {r['total_turns']:<6} {r['cumulative_capsule_tokens']:<8} {r['avg_tokens_per_turn']:<8} {r['savings_vs_raw_pct']:<7}% {r['graph_coverage_pct']:<7}%")
        avg_mt_savings = round(sum(r["savings_vs_raw_pct"] for r in mt) / len(mt), 1)
        avg_mt_tok = round(sum(r["avg_tokens_per_turn"] for r in mt) / len(mt), 1)
        avg_mt_total = round(sum(r["cumulative_capsule_tokens"] for r in mt) / len(mt), 1)
        avg_mt_coverage = round(sum(r["graph_coverage_pct"] for r in mt) / len(mt), 1)
        avg_turns = round(sum(r["total_turns"] for r in mt) / len(mt), 1)
        total_capsule_all = sum(r["cumulative_capsule_tokens"] for r in mt)
        total_raw_all = sum(r["raw_tokens_all_files"] for r in mt)
        overall_savings = round((1 - total_capsule_all / max(total_raw_all, 1)) * 100, 1)
        print(f"  {'-'*90}")
        print(f"  Average ({len(mt)} scenarios, {avg_turns} turns/ea): {avg_mt_total} tot tok, {avg_mt_tok} tok/turn, {avg_mt_savings}% saved, {avg_mt_coverage}% graph covered")
        print(f"  Overall: {total_capsule_all} capsule tokens vs {total_raw_all} raw tokens = {overall_savings}% savings")
        print(f"  {'-'*90}")

    total_cases = len(ss) + len(mt)
    print(f"\n  Total test cases: {total_cases} ({len(ss)} single + {len(mt)} multi-turn)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ctxgraph v3 benchmark — 50 cases")
    parser.add_argument("--single-only", action="store_true", help="25 single-shot only")
    parser.add_argument("--multiturn-only", action="store_true", help="25 multi-turn only")
    parser.add_argument("--project", help="Run only this project")
    args = parser.parse_args()

    output = run_all(
        only_single=args.single_only,
        only_multiturn=args.multiturn_only,
        project_filter=args.project,
    )
    print_summary(output)
