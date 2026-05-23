# v4 Benchmark: Cross-Module Import Edge Validation

**Date**: 2026-05-24
**Project**: `complex_app` — 35 files, 7 modules (`auth`, `billing`, `inventory`, `orders`, `notifications`, `analytics`, `shared` + `tests/`)
**Goal**: Validate that cross-module import edges are correctly detected and graph captures full structural dependencies.

## Key Fix

The importer's `_resolve_import_target` was failing when import paths included the top-level package name. For example, `from complex_app.auth.service import AuthService` was resolved to `complex_app/auth/service.py` relative to root, but the actual file lives at `auth/service.py` (since root is already `complex_app`).

**Fix**: Added fallback resolution — if the first component of the module path matches the root directory name, also try resolving without it.

```python
# Before: only tried full module path
package_path = module_name.replace(".", "/")

# After: tries both full path and stripped path
if parts[0] == root_name:
    candidates.append("/".join(parts[1:]))
```

## Graph Results

| Metric | Value |
|--------|-------|
| Files analyzed | 26 |
| Files skipped | 9 (test artifacts, `__pycache__`) |
| Total nodes | 230 |
| Total edges | **422** |
| Total import edges | **84** |
| Cross-module import edges | **84** (all imports are cross-module) |
| Cross-module module pairs | **18** |

All 84 import edges are cross-module (spanning different top-level directories). 18 distinct module pairs. Every module connects to at least one other module.

## Cross-Module Import Matrix

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

## Token Efficiency

| Scenario | Base (no enrichment) | Ollama (enriched) |
|----------|---------------------|-------------------|
| Raw tokens | 7,679 | 7,679 |
| Single-shot avg tokens | 25.4 | 208.6 |
| Single-shot avg savings | **99.7%** | **97.3%** |
| Multi-turn avg tot tokens | 141.1 | 1,401.6 |
| Multi-turn avg savings | **98.2%** | **81.7%** |
| Ollama enrichment | — | 26 files, 129s (5.0s/file) |

## Observations

1. **Cross-module edges validated**: All 84 import edges connect files across different modules. `shared/` is the hub (47 incoming edges).
2. **Token savings remain excellent**: Even with LLM-enriched summaries, 97%+ savings single-shot, 82%+ multi-turn.
3. **Ollama enclarge overhead**: 129s for 26 files (`qwen2.5-coder:7b`) — 5.0s/file with GPU. Acceptable for one-time build but significant for iterative use.
4. **Graph size**: 230 nodes + 422 edges stored in ~500KB SQLite DB. Build time under 180ms.
