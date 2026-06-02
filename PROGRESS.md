# ctxgraph — Progress

## Phase 1: Build + Capsule + View + Wrapper (v0.1.0) ✅ Done

All core features implemented and tested:
- `ctx build` — Full AST walk, symbol resolution, call edge inference, dependency extraction
- `ctx capsule <query>` — Token-efficient DSL context capsule with mode selection (fast/balanced/deep)
- `ctx query <term>` — Keyword search with BFS neighborhood expansion and relevance scoring
- `ctx view` — D3.js force-directed graph visualizer (static HTML, zero JS toolchain)
- `ctx info` — Graph statistics (nodes, edges, types, build time)
- `ccg` — Claude wrapper with `--chat` (interactive) and `-p` (single-shot) modes

**Verification**: 64 tests pass. E2E validated on `uni-connect` (147 files, 1090 nodes, 1565 edges, 1.58s build).

## Phase 2: Advanced Features (v0.2.0+) 📋 Planned

| Feature | Status | Description |
|---------|--------|-------------|
| MCP Server | ✅ Done | Dynamic graph queries via MCP protocol (`ctx serve`, `search_graph`, `get_context_capsule`, `get_file_dependencies`, `get_project_overview`) |
| Git Co-Change Graph | ❌ Not started | Co-change edges from git history (`ctx build --git`) |
| Embedding Search | ❌ Not started | Semantic search replacing keyword match (`ctx build --embeddings`) |
| Runtime Graph | ❌ Not started | Auto-instrumentation of FastAPI/Flask routes (`@ctx_trace`) |
| Auto-Watch | ❌ Not started | Re-build on file changes (`ctx watch`) |
| LLM Summaries | ❌ Not started | AI-generated summaries for deeper context (`ctx build --llm-summary`) |

See `PHASE2.md` for full details.

## Package Structure

```
src/ctxgraph/
├── cli/main.py          — Typer CLI (build, capsule, query, view, info, serve)
├── graph/
│   ├── models.py        — Node, Edge, Graph dataclasses
│   ├── storage.py       — SQLite persistence layer
│   ├── builder.py       — Graph build orchestrator
│   └── query.py         — Tokenizer + BFS + relevance scoring
├── capsule/renderer.py  — Token-efficient DSL capsule generation
├── analyzers/python/
│   ├── importer.py      — AST import extraction
│   ├── symbols.py       — Full AST class/function/method detection
│   └── semantic.py      — Docstring-based summaries
├── config/
│   ├── settings.py      — Config loading (TOML/JSON/env overrides)
│   └── providers.py     — Ollama, Claude, OpenAI, custom API clients
├── view/visualizer.py   — D3.js force-directed HTML graph
├── wrapper/claude.py    — ccg Claude wrapper script
├── mcp/server.py        — MCP server (requires `mcp` package, `ctx serve` command)
└── exclude/patterns.py  — Exclusion patterns (default + user)
tests/
├── test_models.py       (9)
├── test_storage.py      (6)
├── test_analyzers.py    (13)
├── test_capsule.py      (4)
├── test_query.py        (5)
├── test_config.py       (8)
├── test_integration.py  (7)
├── test_benchmark.py    (5)
├── test_model_mode.py   (7)
└── fixtures/complex_project/  — Sample layered test project
```

## Metrics

| Item | Value |
|------|-------|
| Source files | 29 Python files |
| Test files | 10 (64 tests) |
| External dependencies (runtime) | `typer`, `rich` |
| External dependencies (tests) | `pytest` |
| Zero-dep core | analyzers, models, storage, query, capsule |
| Token savings (DSL vs JSON) | ~4.7x fewer tokens (avg over 4 projects) |
| Token savings (capsule vs raw files) | ~97.0% saved (avg over 4 projects) |
| Build time (147 files) | 1.58s |
| Platforms | Windows + Linux |

### Token Efficiency Benchmarks (corrected baseline — all .py files)

| Project | Files | Raw Tokens | Avg Capsule Tokens | Avg Saved | Build Time |
|---------|-------|-----------|-------------------|-----------|------------|
| tiny_app | 7 | 1,558 | ~112 | **92.8%** | ~82ms |
| web_api | 23 | 6,567 | ~136 | **97.9%** | ~474ms |
| microsvc | 22 | 10,587 | ~63 | **99.4%** | ~916ms |
| dataflow | 35 | ~12,500 | ~78 | **~99.4%** | ~560ms |

- DSL format averages **4.7x fewer tokens** than equivalent JSON representation
- Baseline corrected: counts ALL `.py` files (including `__init__.py`), not just graph nodes

### Ollama Comparison (with vs without ctxgraph context)

| Metric | Value |
|--------|-------|
| Projects tested | tiny_app, web_api, microsvc, dataflow |
| Total queries | 9 |
| Coverage improved | **4/9** queries (44%) |
| Avg coverage improvement | **+16.7pp** keyword recall |
| Model | qwen2.5-coder:7b (local Ollama) |

**Key findings:**
- For **project-specific** questions (e.g., "What processors are available?", "What services communicate?"), ctxgraph improves coverage from ~33-50% to **67-100%**
- For **general CS knowledge** questions (e.g., "How does the event bus work?"), the model already knows — no improvement needed
- Context capsule adds tokens but gives the model **concrete file names, class names, and dependency links** it cannot guess from training data alone
- One regression: PipelineBuilder question — without context the model guessed a generic answer matching all keywords; with context it focused on the actual code and missed one keyword

## Known Limitations

- Python-only analysis — other languages return file-level nodes only
- Keyword-based search (no semantic/embedding matching)
- No incremental rebuild — full rebuild on every `ctx build`
- MCP server uses stdio mode only (SSE not yet supported)
- MCP requires `pip install ctxgraph[mcp]` for the `mcp` and `anyio` packages
