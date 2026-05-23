"""Run v3 benchmarks (50 cases) with Ollama LLM enrichment and compare vs base.

Phase 1: Build graph + enrich all file nodes via Ollama
Phase 2: Run all 50 test cases on enriched graph
Phase 3: Compare with base (non-Ollama) results

Usage:
    python benchmarks/run_benchmarks_v3_ollama.py
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
from ctxgraph.config.settings import Settings
from ctxgraph.config.providers import generate_summary

PROJECTS_DIR = REPO_ROOT / "benchmarks" / "projects"
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Same queries/scenarios as v3
SINGLE_SHOT_QUERIES = {
    "tiny_app": [
        "calculator add subtract multiply", "expression parser tokenize",
        "plugin system history logging", "math operations core functions",
        "main entry point CLI", "error handling division",
        "test calculator functions", "import dependencies",
    ],
    "web_api": [
        "user management CRUD", "JWT auth login register",
        "rate limit middleware", "blog posts publish",
        "admin routes permission", "password hashing auth service",
        "middleware pipeline", "user model fields", "post service pagination",
    ],
    "microsvc": [
        "auth service JWT OAuth", "billing payment stripe",
        "notification email push", "circuit breaker pattern",
        "service registry discovery", "event bus pub sub",
        "distributed tracing", "retry backoff timeout",
    ],
}

MULTI_TURN_SCENARIOS = {
    "tiny_app": [
        {"name": "Fix divide-by-zero in calculator", "turns": ["calculator divide math error", "core division function", "error handling try except", "plugin error logging", "test division edge cases"]},
        {"name": "Add new square root plugin", "turns": ["plugin system load dispatch", "calculator core math operations", "plugin base class interface", "history plugin example", "test plugin registration", "main entry CLI args"]},
        {"name": "Fix expression parser bug", "turns": ["expression parser tokenize", "parser token types regex", "parse error handling", "calculator evaluate expression", "test parser expressions"]},
        {"name": "Refactor calculator error handling", "turns": ["error handling calculator", "core math exceptions", "parser validation errors", "plugin error callback", "main CLI error messages", "test error cases"]},
        {"name": "Add power function to calculator", "turns": ["calculator core functions", "add power exponent", "expression parser power operator", "test power edge cases", "plugin history log power"]},
        {"name": "Improve CLI help and usage", "turns": ["main CLI argument parse", "CLI help text format", "calculator operation list", "plugin list command", "test CLI integration"]},
        {"name": "Add memory store plugin", "turns": ["plugin system history", "plugin base class API", "memory storage variables", "calculator use memory", "test memory plugin", "CLI memory commands"]},
        {"name": "Secure calculator input validation", "turns": ["expression parser tokenize", "input validation sanitize", "parser error handling", "calculator safe eval", "test invalid input", "main CLI input loop"]},
    ],
    "web_api": [
        {"name": "Add JWT refresh token flow", "turns": ["auth service JWT token", "JWT create decode verify", "auth middleware validate", "user session management", "login register routes", "refresh token endpoint", "test auth refresh flow"]},
        {"name": "Fix rate limiter bucket refill", "turns": ["rate limit middleware", "token bucket algorithm", "rate limit config settings", "middleware pipeline order", "test rate limiting", "rate limit headers response"]},
        {"name": "Add user role permissions", "turns": ["user model fields role", "user service create update", "auth middleware role check", "admin routes permission guard", "user routes role filter", "test role based access", "migration add role field"]},
        {"name": "Optimize blog post pagination", "turns": ["post service list query", "post model fields sort", "post routes pagination", "user service author posts", "test post pagination", "admin routes all posts"]},
        {"name": "Implement password reset flow", "turns": ["auth service password hash", "user service find by email", "reset token generate verify", "auth routes reset password", "email notification service", "test password reset", "rate limit reset attempts"]},
        {"name": "Build admin analytics dashboard", "turns": ["admin routes dashboard", "user service stats count", "post service analytics", "auth service login history", "middleware admin only", "test admin analytics"]},
        {"name": "Add API versioning support", "turns": ["routes version prefix", "middleware accept header", "config api version", "user routes backward compat", "post routes version check", "test versioned endpoints"]},
        {"name": "Implement request body validation", "turns": ["user model validation", "post model fields required", "services input sanitize", "routes error response", "middleware validation", "test invalid request body"]},
        {"name": "Add audit logging middleware", "turns": ["middleware logging request", "auth service user context", "audit log model storage", "middleware pipeline order", "admin routes audit trail", "test audit entries", "config audit enabled"]},
    ],
    "microsvc": [
        {"name": "Add OAuth2 GitHub provider", "turns": ["auth OAuth service", "auth JWT token create", "oauth authorize callback", "user model external id", "auth server routes", "test OAuth flow", "config OAuth settings", "shared logger debug"]},
        {"name": "Fix billing invoice rounding", "turns": ["billing invoice generate", "billing payment process", "billing plans pricing", "invoice model fields", "billing server routes", "test invoice rounding", "shared events invoice created"]},
        {"name": "Add SMS notification provider (Twilio)", "turns": ["notification SMS send", "notification provider base", "notification email SMTP", "notification templates", "notification server routes", "test SMS notification"]},
        {"name": "Tune circuit breaker thresholds", "turns": ["circuit breaker pattern", "circuit breaker state open closed", "shared retry backoff", "shared metrics counter", "shared events circuit trip", "test circuit breaker", "config circuit thresholds"]},
        {"name": "Add health check to service discovery", "turns": ["gateway service discovery", "discovery register heartbeat", "gateway router health", "shared retry health check", "gateway middleware timeout", "test discovery health"]},
        {"name": "Implement event bus retry mechanism", "turns": ["shared events pub sub", "shared retry exponential backoff", "shared logger structured", "billing events invoice created", "notification events user registered", "test event retry", "config retry max attempts", "shared metrics event count"]},
        {"name": "Add distributed tracing headers", "turns": ["shared tracing trace id", "gateway middleware propagate", "auth server tracing", "billing server tracing", "shared logger trace context", "test tracing propagation", "shared metrics trace duration"]},
        {"name": "Build metrics endpoint for Prometheus", "turns": ["shared metrics counter gauge", "gateway metrics requests", "auth metrics login count", "billing metrics revenue", "shared metrics endpoint", "test metrics output", "config metrics enabled", "notification metrics sent"]},
    ],
}


def count_tokens(text: str) -> int:
    return len(text.split())


def build_and_enrich(project: str, db_name: str, settings: Settings) -> tuple[dict, Storage]:
    proj_dir = PROJECTS_DIR / project
    db_path = RESULTS_DIR / db_name
    if db_path.exists():
        db_path.unlink()

    # Phase 1: build graph
    start = time.perf_counter()
    stats = build_graph(proj_dir, db_path=db_path)
    build_time = time.perf_counter() - start
    stats["build_time_ms"] = round(build_time * 1000, 2)

    storage = Storage(db_path)
    storage.connect()

    # Phase 2: enrich all file nodes with Ollama
    all_nodes = storage.get_all_nodes()
    file_nodes = [n for n in all_nodes if n.type == "file"]
    enrich_start = time.perf_counter()
    enriched = 0
    skipped = 0
    for fn in file_nodes:
        fp = proj_dir / (fn.path or "")
        if not fp.is_file():
            skipped += 1
            continue
        code = fp.read_text(encoding="utf-8", errors="replace")
        context = f"File: {fn.path} — {fn.name}"
        summary = generate_summary(settings, code, context=context)
        if summary and len(summary.split()) > 3:
            storage.update_node_summary(fn.id, summary.strip())
            enriched += 1
        else:
            skipped += 1
    enrich_time = time.perf_counter() - enrich_start
    stats["ollama_enriched"] = enriched
    stats["ollama_skipped"] = skipped
    stats["ollama_time_s"] = round(enrich_time, 1)
    stats["ollama_time_per_file_s"] = round(enrich_time / max(enriched, 1), 1)

    print(f"  Enriched {enriched} files via Ollama in {enrich_time:.1f}s ({stats['ollama_time_per_file_s']}s/file)")
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


def run_all(project_filter: str | None):
    settings = Settings()
    settings._data["ai"]["model"] = "qwen2.5-coder:7b"
    settings._data["ai"]["temperature"] = 0.1

    output = {"single_shot": [], "multi_turn": []}

    for proj in ["tiny_app", "web_api", "microsvc"]:
        if project_filter and proj != project_filter:
            continue

        raw_total, raw_count = get_raw_tokens(proj)
        print(f"\n{'='*60}")
        print(f"  {proj} ({raw_count} files, {raw_total} raw tokens) — WITH OLLAMA")
        print(f"{'='*60}")

        db_name = f"v3_ollama_{proj}.db"
        stats, storage = build_and_enrich(proj, db_name, settings)

        # Single-shot
        print(f"  Running {len(SINGLE_SHOT_QUERIES[proj])} single-shot queries...")
        for query in SINGLE_SHOT_QUERIES[proj]:
            capsule = render_capsule(storage, query, max_nodes=10)
            cap_tok = count_tokens(capsule)
            nodes, edges = generate_context_subgraph(storage, query, max_nodes=10)
            savings = round((1 - cap_tok / max(raw_total, 1)) * 100, 1)
            output["single_shot"].append({
                "type": "ollama_single_shot", "project": proj, "query": query,
                "capsule_tokens": cap_tok, "capsule_nodes": len(nodes),
                "capsule_edges": len(edges), "savings_pct": savings,
                "raw_tokens": raw_total,
                "build_time_ms": stats["build_time_ms"],
                "ollama_time_s": stats["ollama_time_s"],
            })

        # Multi-turn
        print(f"  Running {len(MULTI_TURN_SCENARIOS[proj])} multi-turn scenarios...")
        for scenario in MULTI_TURN_SCENARIOS[proj]:
            turns = []
            cumulative_tokens = 0
            seen_nodes = set()
            for i, query in enumerate(scenario["turns"]):
                capsule = render_capsule(storage, query, max_nodes=10)
                cap_tok = count_tokens(capsule)
                nodes, edges = generate_context_subgraph(storage, query, max_nodes=10)
                turn_ids = {n.id for n in nodes}
                new_nodes = turn_ids - seen_nodes
                overlap = round((1 - len(new_nodes) / max(len(turn_ids), 1)) * 100, 1) if turn_ids else 100.0
                seen_nodes.update(turn_ids)
                cumulative_tokens += cap_tok
                turns.append({
                    "turn": i + 1, "query": query,
                    "capsule_tokens": cap_tok, "capsule_nodes": len(nodes),
                    "new_nodes_this_turn": len(new_nodes),
                    "overlap_pct": overlap,
                })
            savings = round((1 - cumulative_tokens / max(raw_total, 1)) * 100, 1)
            output["multi_turn"].append({
                "type": "ollama_multi_turn", "project": proj,
                "scenario": scenario["name"],
                "total_turns": len(scenario["turns"]),
                "cumulative_capsule_tokens": cumulative_tokens,
                "avg_tokens_per_turn": round(cumulative_tokens / len(scenario["turns"]), 1),
                "savings_vs_raw_pct": savings,
                "raw_tokens_all_files": raw_total,
                "build_time_ms": stats["build_time_ms"],
                "ollama_time_s": stats["ollama_time_s"],
                "unique_nodes_visited": len(seen_nodes),
                "graph_coverage_pct": round(len(seen_nodes) / max(stats.get("total_nodes", 1), 1) * 100, 1),
                "turns": turns,
            })

        storage.close()

    with open(RESULTS_DIR / "benchmark_results_v3_ollama.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {RESULTS_DIR / 'benchmark_results_v3_ollama.json'}")
    return output


def compare_with_base(ollama_out: dict):
    base_path = RESULTS_DIR / "benchmark_results_v3.json"
    if not base_path.exists():
        print("No base (non-Ollama) results found. Run run_benchmarks_v3.py first.")
        return

    with open(base_path) as f:
        base = json.load(f)

    print(f"\n{'='*70}")
    print(f"  WITH vs WITHOUT OLLAMA — 50 CASE COMPARISON")
    print(f"{'='*70}")

    # Single-shot comparison
    print(f"\n  SINGLE-SHOT AVERAGES:")
    print(f"  {'Project':<12} {'Base Tok':<12} {'Ollama Tok':<14} {'Tok +':<10} {'Base Saved':<12} {'Ollama Saved':<14}")
    print(f"  {'-'*12} {'-'*12} {'-'*14} {'-'*10} {'-'*12} {'-'*14}")
    for proj in ["tiny_app", "web_api", "microsvc"]:
        base_ss = [r for r in base["single_shot"] if r["project"] == proj]
        ollama_ss = [r for r in ollama_out["single_shot"] if r["project"] == proj]
        if base_ss and ollama_ss:
            b_avg = round(sum(r["capsule_tokens"] for r in base_ss) / len(base_ss), 1)
            o_avg = round(sum(r["capsule_tokens"] for r in ollama_ss) / len(ollama_ss), 1)
            b_sav = round(sum(r["savings_pct"] for r in base_ss) / len(base_ss), 1)
            o_sav = round(sum(r["savings_pct"] for r in ollama_ss) / len(ollama_ss), 1)
            delta = round(o_avg - b_avg, 1)
            print(f"  {proj:<12} {b_avg:<12} {o_avg:<14} +{delta:<8} {b_sav:<10}% {o_sav:<12}%")

    # Multi-turn comparison
    print(f"\n  MULTI-TURN AVERAGES:")
    print(f"  {'Project':<12} {'Base TotTok':<14} {'Ollama TotTok':<14} {'Tok +':<12} {'Base Sav%':<12} {'Ollama Sav%':<14}")
    print(f"  {'-'*12} {'-'*14} {'-'*14} {'-'*12} {'-'*12} {'-'*14}")
    for proj in ["tiny_app", "web_api", "microsvc"]:
        base_mt = [r for r in base["multi_turn"] if r["project"] == proj]
        ollama_mt = [r for r in ollama_out["multi_turn"] if r["project"] == proj]
        if base_mt and ollama_mt:
            b_tot = round(sum(r["cumulative_capsule_tokens"] for r in base_mt) / len(base_mt), 1)
            o_tot = round(sum(r["cumulative_capsule_tokens"] for r in ollama_mt) / len(ollama_mt), 1)
            b_sav = round(sum(r["savings_vs_raw_pct"] for r in base_mt) / len(base_mt), 1)
            o_sav = round(sum(r["savings_vs_raw_pct"] for r in ollama_mt) / len(ollama_mt), 1)
            delta = round(o_tot - b_tot, 1)
            print(f"  {proj:<12} {b_tot:<14} {o_tot:<14} +{delta:<10} {b_sav:<10}% {o_sav:<12}%")

    # Overall
    print()
    base_all_ss = base["single_shot"]
    base_all_mt = base["multi_turn"]
    ola_all_ss = ollama_out["single_shot"]
    ola_all_mt = ollama_out["multi_turn"]

    b_ss_avg = round(sum(r["capsule_tokens"] for r in base_all_ss) / len(base_all_ss), 1)
    o_ss_avg = round(sum(r["capsule_tokens"] for r in ola_all_ss) / len(ola_all_ss), 1)
    b_mt_avg = round(sum(r["cumulative_capsule_tokens"] for r in base_all_mt) / len(base_all_mt), 1)
    o_mt_avg = round(sum(r["cumulative_capsule_tokens"] for r in ola_all_mt) / len(ola_all_mt), 1)
    b_ss_sav = round(sum(r["savings_pct"] for r in base_all_ss) / len(base_all_ss), 1)
    o_ss_sav = round(sum(r["savings_pct"] for r in ola_all_ss) / len(ola_all_ss), 1)

    print(f"  OVERALL AVERAGES:")
    print(f"    Single-shot:     Base: {b_ss_avg} tok ({b_ss_sav}%)  |  Ollama: {o_ss_avg} tok ({o_ss_sav}%)  |  Δ +{round(o_ss_avg-b_ss_avg,1)} tok")
    print(f"    Multi-turn tot:  Base: {b_mt_avg} tok  |  Ollama: {o_mt_avg} tok  |  Δ +{round(o_mt_avg-b_mt_avg,1)} tok")

    # Ollama time cost
    ola_times = [r.get("ollama_time_s", 0) for r in ola_all_ss]
    avg_ollama_time = round(sum(ola_times) / max(len(ola_times), 1), 1) if ola_times else 0
    print(f"    Ollama enrichment time: {avg_ollama_time}s per project (average)")
    print(f"    Token overhead: +{round((o_ss_avg-b_ss_avg)/max(b_ss_avg,1)*100,1)}% for single-shot, +{round((o_mt_avg-b_mt_avg)/max(b_mt_avg,1)*100,1)}% for multi-turn")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="v3 benchmarks WITH Ollama")
    parser.add_argument("--project", help="Run only this project")
    parser.add_argument("--no-compare", action="store_true", help="Skip comparison with base")
    args = parser.parse_args()

    ollama_results = run_all(project_filter=args.project)

    if not args.no_compare:
        compare_with_base(ollama_results)
