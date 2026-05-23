# v4 Benchmark: Cross-Module Import Edge Validation

**Project**: `complex_app` — 35 files, 7 modules (`auth`, `billing`, `inventory`, `orders`, `notifications`, `analytics`, `shared` + `tests/`)
**Goal**: Validate cross-module import edges + token efficiency with relevant-raw baseline.

**Methodology**: `relevant_raw` = raw tokens of only the files whose symbols appear in the query's context subgraph (simulates on-demand file loading per turn, the realistic alternative to ctxgraph).

---

## Import Fix

`_resolve_import_target` in `importer.py` failed when import paths included the top-level package name (e.g., `from complex_app.auth.service import AuthService` resolved to `complex_app/auth/service.py` but root is already `complex_app`). Added fallback that strips the root directory name from the module path.

## Graph Results

| Metric | Value |
|--------|-------|
| Files analyzed | 26 |
| Files skipped | 9 |
| Total nodes | 230 |
| Total edges | **422** |
| Import edges | 84 (all cross-module) |
| Cross-module pairs | 18 |

### Cross-Module Import Matrix

| Source | Targets |
|--------|---------|
| `auth/` (5 files) | `shared/` (12), `tests/` (2) |
| `billing/` (2 files) | `shared/` (6), `auth/` (1), `notifications/` (1) |
| `inventory/` (4 files) | `shared/` (9), `auth/` (2), `notifications/` (1) |
| `orders/` (2 files) | `shared/` (6) |
| `notifications/` (3 files) | `shared/` (8) |
| `analytics/` (2 files) | `shared/` (5) |
| `shared/` (5 files) | `auth/` (1) |
| `tests/` (3 files) | `analytics/` (3), `auth/` (2), `notifications/` (2), `shared/` (2), `billing/` (1), `inventory/` (1), `orders/` (1) |

---

## Token Efficiency

### Base (AST only — no LLM enrichment)

| Metric | vs All Raw | vs Relevant Raw |
|--------|:---:|:---:|
| Raw tokens (35 files) | 7,679 | — |
| Single-shot avg | 26.6 tok (**99.6%**) | 26.6 tok (**96.8%**) |
| Multi-turn cumulative avg | 141.1 tok (**98.2%**) | 141.1 tok (**96.8%**) |
| Overall multi-turn | — | **96.8% savings** |

### Ollama (qwen2.5-coder:7b, 26 files enriched, 128.6s)

| Metric | vs All Raw | vs Relevant Raw |
|--------|:---:|:---:|
| Single-shot avg | 238.6 tok (**96.9%**) | 238.6 tok (**83.8%**) |
| Multi-turn cumulative avg | 1,628.6 tok (**78.8%**) | 1,628.6 tok (**68.6%**) |

### Comparison

| Metric | Base | Ollama |
|--------|:---:|:---:|
| Single-shot capsule avg | 26.6 tok | 238.6 tok |
| Single-shot savings vs relevant | **96.8%** | **83.8%** |
| Multi-turn cumulative avg | 141.1 tok | 1,628.6 tok |
| Multi-turn savings vs relevant | **96.8%** | **68.6%** |
| Build time | 189ms | 183ms |
| Enrichment time | — | 128.6s (4.9s/file) |

## Observations

1. **Cross-module edges working**: 84 import edges, all cross-module. Every module connected. `shared/` is hub with 47 incoming edges.
2. **Even vs relevant raw, AST-only saves 97%**: The capsule format is dramatically more compact than raw source code for the same set of files.
3. **Ollama enrichment costs 4x more tokens**: Natural-language summaries are informative but increase capsule size significantly. Still saves 69% vs relevant raw on multi-turn.
4. **Graph size**: 230 nodes + 422 edges in ~500KB SQLite DB, built in <190ms.

## Running

```bash
python benchmarks/run_benchmarks_v4.py
```
