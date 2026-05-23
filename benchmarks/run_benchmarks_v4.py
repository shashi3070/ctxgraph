"""v4 benchmark — complex_app only, single-shot + multi-turn, with/without Ollama."""
import json, sys, time
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

PROJECT = "complex_app"
PROJ_DIR = REPO_ROOT / "benchmarks" / "projects" / PROJECT
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def count_tokens(text):
    return len(text.split())

def get_raw_tokens():
    total, count = 0, 0
    for fp in PROJ_DIR.rglob("*.py"):
        if fp.is_file():
            try:
                total += count_tokens(fp.read_text(encoding="utf-8", errors="replace"))
                count += 1
            except Exception:
                pass
    return total, count

def raw_tokens_for_files(file_paths):
    total = 0
    for fp_rel in file_paths:
        fpath = PROJ_DIR / (fp_rel or "")
        if fpath.is_file():
            try:
                total += count_tokens(fpath.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    return total

def relevant_file_paths(nodes):
    paths = set()
    for n in nodes:
        if n.path:
            paths.add(n.path)
    return paths

SINGLE_QUERIES = [
    "order creation workflow payment",
    "user authentication login",
    "inventory stock management",
    "billing subscription invoice",
    "notification email push",
    "analytics event tracking dashboard",
    "order state machine workflow",
    "warehouse transfer stock",
    "payment gateway stripe paypal",
    "auth middleware permission role",
    "JWT token creation validation",
    "product category inventory",
    "cart checkout coupon discount",
    "shipment tracking delivery",
    "user registration verification",
    "password reset email",
    "service base class repository",
    "cache TTL configuration",
    "database transaction query",
    "error handling validation",
    "report generation metrics",
    "event bus publish subscribe",
    "rate limit throttling",
    "config environment settings",
    "integration test full flow",
]

MULTI_TURN_SCENARIOS = [
    {
        "name": "Build complete order checkout flow",
        "turns": [
            "auth service user authentication",
            "inventory product stock check reserve",
            "billing payment process charge",
            "notification order confirmation send",
            "analytics event tracking order creation",
            "order create cart checkout workflow",
        ],
    },
    {
        "name": "Debug subscription billing failure",
        "turns": [
            "billing subscription plan payment method",
            "billing payment gateway stripe",
            "auth user lookup validation",
            "notification send failure alert",
            "analytics track payment failure event",
            "billing invoice retry payment",
            "shared database transaction rollback",
        ],
    },
    {
        "name": "Implement user permission system",
        "turns": [
            "auth models role permission",
            "auth middleware require role decorator",
            "auth service has_permission check",
            "shared errors authorization error",
            "inventory service admin product create",
            "orders service user order list",
            "auth JWT token payload roles",
        ],
    },
    {
        "name": "Add product inventory management",
        "turns": [
            "inventory product category create",
            "inventory stock check reserve release",
            "inventory warehouse transfer",
            "shared cache product lookup",
            "notification low stock alert",
            "analytics track product view event",
            "orders service use inventory reservation",
        ],
    },
    {
        "name": "Set up notification delivery pipeline",
        "turns": [
            "notification models template preference",
            "notification email provider SMTP sendgrid",
            "notification push provider FCM APNs",
            "notification service send bulk",
            "auth user preference lookup",
            "analytics track notification sent",
            "shared config email settings",
        ],
    },
    {
        "name": "Build analytics dashboard",
        "turns": [
            "analytics models event metric report",
            "analytics service track event",
            "analytics event tracker specialized",
            "auth user context for events",
            "orders service create track event",
            "billing payment track event",
            "analytics report generation aggregation",
        ],
    },
    {
        "name": "Implement event-driven architecture",
        "turns": [
            "shared base event handler",
            "shared database transaction",
            "shared cache TTL",
            "shared config environment",
            "auth events user registered",
            "billing events invoice created",
            "orders events order placed",
        ],
    },
    {
        "name": "Cross-cutting error handling refactor",
        "turns": [
            "shared errors all error types",
            "auth service authentication error",
            "billing service validation error",
            "inventory service not found error",
            "orders service authorization error",
            "notification service service unavailable",
            "analytics service database error",
        ],
    },
]

def build_and_enrich(settings):
    db_name = f"v4_{PROJECT}_ollama.db"
    db_path = RESULTS_DIR / db_name
    if db_path.exists():
        db_path.unlink()

    start = time.perf_counter()
    stats = build_graph(PROJ_DIR, db_path=db_path)
    build_time = time.perf_counter() - start
    stats["build_time_ms"] = round(build_time * 1000, 2)

    storage = Storage(db_path)
    storage.connect()
    all_nodes = storage.get_all_nodes()
    file_nodes = [n for n in all_nodes if n.type == "file"]

    enrich_start = time.perf_counter()
    enriched = 0
    skipped = 0
    for fn in file_nodes:
        fp = PROJ_DIR / (fn.path or "")
        if not fp.is_file():
            skipped += 1
            continue
        code = fp.read_text(encoding="utf-8", errors="replace")
        summary = generate_summary(settings, code, context=f"File: {fn.path} - {fn.name}")
        if summary and len(summary.split()) > 3:
            storage.update_node_summary(fn.id, summary.strip())
            enriched += 1
        else:
            skipped += 1
    enrich_time = time.perf_counter() - enrich_start
    stats["ollama_enriched"] = enriched
    stats["ollama_skipped"] = skipped
    stats["ollama_time_s"] = round(enrich_time, 1)
    stats["ollama_time_per_file_s"] = round(enrich_time / max(enriched, 1), 1) if enriched else 0
    print(f"  Enriched {enriched} files via Ollama in {enrich_time:.1f}s ({stats['ollama_time_per_file_s']}s/file)")
    return stats, storage, enriched

def run_single_shot(storage, raw_total, raw_count, label, enrich_time):
    results = []
    print(f"  Running {len(SINGLE_QUERIES)} single-shot queries ({label})...")
    for query in SINGLE_QUERIES:
        capsule = render_capsule(storage, query, max_nodes=10)
        cap_tok = count_tokens(capsule)
        nodes, edges = generate_context_subgraph(storage, query, max_nodes=10)
        savings = round((1 - cap_tok / max(raw_total, 1)) * 100, 1)
        relevant_files = relevant_file_paths(nodes)
        relevant_raw = raw_tokens_for_files(relevant_files)
        sv_rel = round((1 - cap_tok / max(relevant_raw, 1)) * 100, 1) if relevant_raw else 0.0
        results.append({
            "label": label, "query": query,
            "capsule_tokens": cap_tok, "capsule_nodes": len(nodes),
            "capsule_edges": len(edges), "savings_pct": savings,
            "savings_vs_relevant_pct": sv_rel,
            "relevant_raw_tokens": relevant_raw,
            "raw_tokens": raw_total,
        })
    avg = round(sum(r["capsule_tokens"] for r in results) / len(results), 1)
    avg_sav = round(sum(r["savings_pct"] for r in results) / len(results), 1)
    avg_rel = round(sum(r.get("savings_vs_relevant_pct", 0) for r in results) / len(results), 1)
    print(f"    Avg: {raw_total} raw ({avg_rel}% vs relevant) -> {avg} capsule tok/case, {avg_sav}% vs all")
    return results

def run_multi_turn(storage, raw_total, raw_count, label):
    results = []
    print(f"  Running {len(MULTI_TURN_SCENARIOS)} multi-turn scenarios ({label})...")
    for scenario in MULTI_TURN_SCENARIOS:
        turns = []
        cumulative = 0
        seen = set()
        seen_files = set()
        cumulative_relevant_raw = 0
        for i, q in enumerate(scenario["turns"]):
            capsule = render_capsule(storage, q, max_nodes=10)
            tok = count_tokens(capsule)
            nodes, edges = generate_context_subgraph(storage, q, max_nodes=10)
            ids = {n.id for n in nodes}
            new = ids - seen
            overlap = round((1 - len(new) / max(len(ids), 1)) * 100, 1) if ids else 100.0
            seen.update(ids)
            cumulative += tok
            turn_files = relevant_file_paths(nodes)
            new_files = turn_files - seen_files
            seen_files.update(turn_files)
            cumulative_relevant_raw += raw_tokens_for_files(new_files)
            turns.append({
                "turn": i+1, "query": q, "capsule_tokens": tok,
                "capsule_nodes": len(nodes), "new_nodes": len(new), "overlap_pct": overlap,
                "relevant_raw_this_turn": raw_tokens_for_files(new_files),
            })
        savings = round((1 - cumulative / max(raw_total, 1)) * 100, 1)
        sv_rel = round((1 - cumulative / max(cumulative_relevant_raw, 1)) * 100, 1) if cumulative_relevant_raw else 0.0
        results.append({
            "label": label, "scenario": scenario["name"],
            "total_turns": len(scenario["turns"]),
            "cumulative_tokens": cumulative,
            "avg_tokens_per_turn": round(cumulative / len(scenario["turns"]), 1),
            "savings_vs_raw_pct": savings,
            "savings_vs_relevant_pct": sv_rel,
            "cumulative_relevant_raw_tokens": cumulative_relevant_raw,
            "unique_nodes_visited": len(seen),
            "graph_coverage_pct": round(len(seen) / 230 * 100, 1),
            "raw_tokens_all_files": raw_total,
            "turns": turns,
        })
    avg_tot = round(sum(r["cumulative_tokens"] for r in results) / len(results), 1)
    avg_sav = round(sum(r["savings_vs_raw_pct"] for r in results) / len(results), 1)
    avg_rel = round(sum(r.get("savings_vs_relevant_pct", 0) for r in results) / len(results), 1)
    print(f"    Avg: {raw_total} raw ({avg_rel}% vs relevant) -> {avg_tot} capsule tot tok/scenario, {avg_sav}% vs all")
    return results

def main():
    settings = Settings()
    settings._data["ai"]["model"] = "qwen2.5-coder:7b"
    settings._data["ai"]["temperature"] = 0.1

    raw_total, raw_count = get_raw_tokens()
    print(f"{'='*60}")
    print(f"  complex_app ({raw_count} files, {raw_total} raw tokens)")
    print(f"{'='*60}")

    # Phase 1: Build + enrich with Ollama
    print("\n--- Phase 1: Build + Ollama enrichment ---")
    stats_ola, storage_ola, enriched = build_and_enrich(settings)

    # Phase 2: Build without Ollama (base)
    print("\n--- Phase 2: Base build (no Ollama) ---")
    db_base = RESULTS_DIR / f"v4_{PROJECT}_base.db"
    if db_base.exists():
        db_base.unlink()
    start = time.perf_counter()
    stats_base = build_graph(PROJ_DIR, db_path=db_base)
    stats_base["build_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
    storage_base = Storage(db_base)
    storage_base.connect()

    # Phase 3: Run benchmarks
    print("\n--- Phase 3: Benchmarks ---")
    ss_base = run_single_shot(storage_base, raw_total, raw_count, "base", 0)
    ss_olla = run_single_shot(storage_ola, raw_total, raw_count, "ollama", stats_ola["ollama_time_s"])
    mt_base = run_multi_turn(storage_base, raw_total, raw_count, "base")
    mt_olla = run_multi_turn(storage_ola, raw_total, raw_count, "ollama")

    storage_base.close()
    storage_ola.close()

    output = {
        "project": PROJECT,
        "files": raw_count,
        "raw_tokens": raw_total,
        "build_time_ms": stats_base["build_time_ms"],
        "build_time_ollama_ms": stats_ola["build_time_ms"],
        "ollama_enrich_time_s": stats_ola["ollama_time_s"],
        "ollama_enriched_files": enriched,
        "ollama_time_per_file_s": stats_ola["ollama_time_per_file_s"],
        "total_nodes": stats_base.get("total_nodes", 0),
        "total_edges": stats_base.get("total_edges", 0),
        "single_shot": {"base": ss_base, "ollama": ss_olla},
        "multi_turn": {"base": mt_base, "ollama": mt_olla},
    }

    with open(RESULTS_DIR / "benchmark_results_v4.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {RESULTS_DIR / 'benchmark_results_v4.json'}")

    # Print comparison
    print(f"\n{'='*95}")
    print(f"  complex_app — WITH vs WITHOUT OLLAMA")
    print(f"{'='*95}")
    print(f"  {'Metric':<35} {'RawAll':<12} {'Relevant':<12} {'Base':<12} {'Ollama':<12}")
    print(f"  {'-'*35} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    raw_total, _ = get_raw_tokens()
    b_ss_avg = round(sum(r["capsule_tokens"] for r in ss_base) / len(ss_base), 1)
    o_ss_avg = round(sum(r["capsule_tokens"] for r in ss_olla) / len(ss_olla), 1)
    b_ss_sav = round(sum(r["savings_pct"] for r in ss_base) / len(ss_base), 1)
    o_ss_sav = round(sum(r["savings_pct"] for r in ss_olla) / len(ss_olla), 1)
    b_ss_rel = round(sum(r.get("savings_vs_relevant_pct", 0) for r in ss_base) / len(ss_base), 1)
    o_ss_rel = round(sum(r.get("savings_vs_relevant_pct", 0) for r in ss_olla) / len(ss_olla), 1)
    b_mt_avg = round(sum(r["cumulative_tokens"] for r in mt_base) / len(mt_base), 1)
    o_mt_avg = round(sum(r["cumulative_tokens"] for r in mt_olla) / len(mt_olla), 1)
    b_mt_sav = round(sum(r["savings_vs_raw_pct"] for r in mt_base) / len(mt_base), 1)
    o_mt_sav = round(sum(r["savings_vs_raw_pct"] for r in mt_olla) / len(mt_olla), 1)
    b_mt_rel = round(sum(r.get("savings_vs_relevant_pct", 0) for r in mt_base) / len(mt_base), 1)
    o_mt_rel = round(sum(r.get("savings_vs_relevant_pct", 0) for r in mt_olla) / len(mt_olla), 1)
    print(f"  {'Raw tokens total':<35} {raw_total:<12} {'-':<12} {'-':<12} {'-':<12}")
    print(f"  {'SS avg capsule tok':<35} {'-':<12} {'-':<12} {b_ss_avg:<12} {o_ss_avg:<12}")
    print(f"  {'SS savings vs all':<35} {'-':<12} {'-':<12} {b_ss_sav:<11}% {o_ss_sav:<11}%")
    print(f"  {'SS savings vs relevant':<35} {'-':<12} {'-':<12} {b_ss_rel:<11}% {o_ss_rel:<11}%")
    print(f"  {'MT avg cumul capsule':<35} {'-':<12} {'-':<12} {b_mt_avg:<12} {o_mt_avg:<12}")
    print(f"  {'MT savings vs all':<35} {'-':<12} {'-':<12} {b_mt_sav:<11}% {o_mt_sav:<11}%")
    print(f"  {'MT savings vs relevant':<35} {'-':<12} {'-':<12} {b_mt_rel:<11}% {o_mt_rel:<11}%")
    print(f"  {'Build time':<35} {'-':<12} {'-':<12} {stats_base['build_time_ms']:<11}ms {stats_ola['build_time_ms']:<11}ms")
    print(f"  {'Graph nodes':<35} {'-':<12} {'-':<12} {stats_base.get('total_nodes',0):<12} {stats_ola.get('total_nodes',0):<12}")
    print(f"  {'Graph edges':<35} {'-':<12} {'-':<12} {stats_base.get('total_edges',0):<12} {stats_ola.get('total_edges',0):<12}")

if __name__ == "__main__":
    main()
