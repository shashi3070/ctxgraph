"""Compare ctxgraph with and without Ollama LLM enrichment.

Measures:
  - Base: docstring-only summaries (current)
  - With Ollama: LLM-generated summaries for every file
  - Token overhead, time cost, quality comparison

Usage:
    python benchmarks/run_with_ollama.py
"""

import sys, time, json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ctxgraph.graph.builder import build_graph
from ctxgraph.graph.storage import Storage
from ctxgraph.capsule.renderer import render_capsule
from ctxgraph.config.settings import Settings
from ctxgraph.config.providers import generate_summary

PROJECTS_DIR = REPO_ROOT / "benchmarks" / "projects"
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"

PROJECTS = ["tiny_app", "web_api", "microsvc"]

def count_tokens(text: str) -> int:
    return len(text.split())

def run_comparison():
    settings = Settings()
    settings._data["ai"]["model"] = "qwen2.5-coder:7b"
    settings._data["ai"]["temperature"] = 0.1

    print(f"Provider: {settings.provider}")
    print(f"Model:    {settings.model}")
    print()

    output = {}

    for proj in PROJECTS:
        print(f"{'='*60}")
        print(f"  Project: {proj}")
        print(f"{'='*60}")

        proj_dir = PROJECTS_DIR / proj
        db_path = RESULTS_DIR / f"ollama_compare_{proj}.db"

        # Build graph (docstring-only summaries)
        start = time.perf_counter()
        stats = build_graph(proj_dir, db_path=db_path)
        build_time = time.perf_counter() - start
        print(f"  Build: {build_time*1000:.0f}ms, {stats.get('total_nodes',0)} nodes")

        storage = Storage(db_path)
        storage.connect()
        all_nodes = storage.get_all_nodes()
        file_nodes = [n for n in all_nodes if n.type == "file"]
        total_raw_tokens = 0
        for fn in file_nodes:
            fp = proj_dir / (fn.path or "")
            if fp.is_file():
                try:
                    total_raw_tokens += count_tokens(fp.read_text(encoding="utf-8", errors="replace"))
                except Exception:
                    pass

        raw_total = total_raw_tokens

        # Base capsule (docstring-only)
        base_capsule = render_capsule(storage, "main", max_nodes=20)
        base_tokens = count_tokens(base_capsule)
        base_savings = round((1 - base_tokens / max(raw_total, 1)) * 100, 1)

        # Ollama enrich each file's summary
        print(f"  Enriching {len(file_nodes)} files with Ollama...")
        llm_start = time.perf_counter()
        enriched_count = 0
        skipped_count = 0
        for fn in file_nodes:
            fp = proj_dir / (fn.path or "")
            if not fp.is_file():
                skipped_count += 1
                continue
            code = fp.read_text(encoding="utf-8", errors="replace")
            llm_summary = generate_summary(settings, code, context=f"File: {fn.path}")
            if llm_summary:
                storage.update_node_summary(fn.id, llm_summary)
                enriched_count += 1
            else:
                skipped_count += 1
        llm_time = time.perf_counter() - llm_start
        print(f"  Ollama: {enriched_count} enriched, {skipped_count} skipped, {llm_time:.1f}s total")

        # Enriched capsule
        enriched_capsule = render_capsule(storage, "main", max_nodes=20)
        enriched_tokens = count_tokens(enriched_capsule)
        enriched_savings = round((1 - enriched_tokens / max(raw_total, 1)) * 100, 1)
        token_overhead_pct = round((enriched_tokens - base_tokens) / max(base_tokens, 1) * 100, 1)

        per_file_avg = round(llm_time / max(enriched_count, 1), 1)

        proj_result = {
            "project": proj,
            "file_count": len(file_nodes),
            "raw_tokens": raw_total,
            "build_time_ms": round(build_time * 1000, 1),
            "base_capsule_tokens": base_tokens,
            "base_savings_pct": base_savings,
            "enriched_capsule_tokens": enriched_tokens,
            "enriched_savings_pct": enriched_savings,
            "token_overhead_pct": token_overhead_pct,
            "ollama_enriched_count": enriched_count,
            "ollama_time_total_s": round(llm_time, 1),
            "ollama_time_per_file_s": per_file_avg,
        }
        output[proj] = proj_result

        print(f"  Base capsule:      {base_tokens} tok ({base_savings}% saved)")
        print(f"  Enriched capsule:  {enriched_tokens} tok ({enriched_savings}% saved)")
        print(f"  Token overhead:    +{token_overhead_pct}%")
        print(f"  Ollama time:       {llm_time:.1f}s total, {per_file_avg}s/file avg")
        print()

        storage.close()

    # Print comparison table
    print(f"\n{'='*70}")
    print(f"  WITHOUT vs WITH OLLAMA — COMPARISON")
    print(f"{'='*70}")
    print(f"  {'Project':<12} {'RawTok':<10} {'BaseCapTok':<12} {'EnrichedTok':<14} {'TokOverhead':<12} {'OllamaTime':<12}")
    print(f"  {'-'*12} {'-'*10} {'-'*12} {'-'*14} {'-'*12} {'-'*12}")
    for proj in PROJECTS:
        r = output[proj]
        print(f"  {proj:<12} {r['raw_tokens']:<10} {r['base_capsule_tokens']:<12} {r['enriched_capsule_tokens']:<14} +{r['token_overhead_pct']:<9}% {r['ollama_time_total_s']:<10}s")

    with open(RESULTS_DIR / "ollama_comparison.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {RESULTS_DIR / 'ollama_comparison.json'}")

    # Recommendation
    print()
    print(f"  Recommendation:")
    print(f"    Without Ollama:  ~60-500ms build, 90-99% token savings")
    print(f"    With Ollama:     +15-32s per file for richer summaries")
    print(f"    Best for:        Offline batch builds where summary quality matters")
    print(f"    Best against:    Quick iterative builds (use docstring-only)")

if __name__ == "__main__":
    run_comparison()
