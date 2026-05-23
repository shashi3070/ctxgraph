# ctxgraph Benchmarks v2 — Single-Shot vs Multi-Turn vs Error Tests

## Comparison

Single-shot = one isolated query per capsule (v1 approach). Multi-turn = 5-6 sequential queries simulating a real coding session (v2 approach).

### Token Efficiency

| Project | Type | Avg Tok/Turn | Total Capsule | Raw Files | Savings | Build |
|---------|------|:---:|:---:|:---:|:---:|:---:|
| tiny_app (7 files) | single-shot | 74 | — | 1,533 | **95.2%** | 63ms |
| tiny_app (7 files) | multi-turn (5) | 98 | 488 | 1,533 | **68.2%** | 61ms |
| web_api (23 files) | single-shot | 131 | — | 6,191 | **97.9%** | 184ms |
| web_api (23 files) | multi-turn (6) | 127 | 760 | 6,191 | **87.7%** | 183ms |
| microsvc (22 files) | single-shot | 48 | — | 10,342 | **99.5%** | 455ms |
| microsvc (22 files) | multi-turn (6) | 42 | 253 | 10,342 | **97.6%** | 480ms |

**Multi-turn average: 89 tok/turn, 84.5% savings vs raw files.**

### Multi-turn Overlap (sequential query reuse)

| Scenario | Turns | Tok/Turn | Overlap Range | New Nodes/Turn |
|----------|:---:|:---:|:---:|:---:|
| Calculator plugin bug fix (tiny_app) | 5 | 98 | 10-95% | 1-18 |
| Add JWT auth middleware (web_api) | 6 | 127 | 25-60% | 8-15 |
| Debug billing payment flow (microsvc) | 6 | 42 | 0-75% | 5-20 |

Multi-turn queries share 25-95% nodes with previous turns — most capsules are incremental, not starting from scratch.

## Error / Sad Path Tests

| Test | Scenario | Result | Detail |
|------|----------|:---:|--------|
| e1 | Build on non-existent directory | PASS | Returns empty graph (0 nodes) — no crash |
| e2 | Build on empty project (init only) | PASS | 0 nodes — empty graph handled gracefully |
| e3 | Build with syntax errors in file | PASS | 2 nodes (files tracked, no symbols extracted from broken file) |
| e4 | Capsule query without graph DB | PASS | Returns empty capsule (no crash) |
| e5 | Query with special characters (`!@#$%^&*()`) | PASS | 17 tokens, handled like normal text |
| e6 | Very long query (1000+ chars) | PASS | 214 tokens — no buffer issues |
| e7 | Syntax error file: tracked but not analyzed | PASS | File node exists, zero symbol nodes extracted |

**Result: 7/7 error tests pass.** ctxgraph handles all edge cases gracefully — no crashes, no hangs.

## v1 vs v2 Summary

| Dimension | v1 (single-shot) | v2 (multi-turn) |
|-----------|:---:|:---:|
| Queries per project | 1 | 5-6 |
| Token savings vs raw | 95-99% | 68-98% |
| Captures session context reuse | No | Yes (overlap tracked) |
| Error/sad path coverage | None | 7 tests |
| Realism | Good for one-off lookups | Better simulates coding session |

## How to Run

```bash
# Full v2 suite (single-shot + multi-turn + error tests + comparison)
python benchmarks/run_benchmarks_v2.py

# Multi-turn only
python benchmarks/run_benchmarks_v2.py --only-multiturn

# Error tests only
python benchmarks/run_benchmarks_v2.py --only-errors

# Single project
python benchmarks/run_benchmarks_v2.py --project web_api

# Show comparison from last run (no re-run)
python benchmarks/run_benchmarks_v2.py --compare
```

## With vs Without Ollama (qwen2.5-coder:7b)

Comparison of docstring-only summaries (base) vs LLM-enriched summaries.

| Project | Files | Raw Tokens | Base Capsule | Enriched Capsule | Token Overhead | Ollama Time |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| tiny_app | 5 | 1,533 | 26 tok (98.3%) | 67 tok (95.6%) | +157.7% | 23.0s (4.6s/file) |
| web_api | 18 | 6,191 | 141 tok (97.7%) | 260 tok (95.8%) | +84.4% | 82.5s (4.6s/file) |
| microsvc | 18 | 10,342 | 17 tok (99.8%) | 17 tok (99.8%) | +0.0% | 83.9s (4.7s/file) |

**Trade-off:**
- **Without Ollama**: ~60-600ms build, 95-99% token savings — ideal for quick iteration
- **With Ollama**: +84-158% more capsule tokens, +4.6s/file build time — richer summaries, best for offline batch builds
- microsvc showed no diff because the "main" query matched files without docstrings to improve

Run: `python benchmarks/run_with_ollama.py`

## How to See the Graph (UI)

```bash
# Generate interactive D3.js force-directed graph
ctx view

# Open in browser automatically (add --no-open to skip)
ctx view --open

# Save to custom path
ctx view --output mygraph.html

# For benchmark projects
ctx view --repo benchmarks/projects/web_api
```

The graph shows nodes (files=blue, classes=green, functions=orange) with edges for imports, calls, inheritance, and containment. Supports zoom, drag, search, and filter by type.

## Raw Data

Full JSON output:
- `benchmarks/results/benchmark_results_v2.json` — v2 benchmarks
- `benchmarks/results/ollama_comparison.json` — Ollama comparison
