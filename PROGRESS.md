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

All items currently **not started**:

| Feature | Description |
|---------|-------------|
| MCP Server | Dynamic graph queries via MCP protocol (`ctx serve`, `search_graph`, `get_context_capsule`, `get_file_dependencies`, `get_project_overview`) |
| Git Co-Change Graph | Co-change edges from git history (`ctx build --git`) |
| Embedding Search | Semantic search replacing keyword match (`ctx build --embeddings`) |
| Runtime Graph | Auto-instrumentation of FastAPI/Flask routes (`@ctx_trace`) |
| Auto-Watch | Re-build on file changes (`ctx watch`) |
| LLM Summaries | AI-generated summaries for deeper context (`ctx build --llm-summary`) |

See `PHASE2.md` for full details.

## Package Structure

```
src/ctxgraph/
├── cli/main.py          — Typer CLI (build, capsule, query, view, info)
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
├── mcp/server.py        — MCP skeleton (requires mcp package)
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
| Source files | 28 Python files |
| Test files | 10 (64 tests) |
| External dependencies (runtime) | `typer`, `rich` |
| External dependencies (tests) | `pytest` |
| Zero-dep core | analyzers, models, storage, query, capsule |
| Token savings (DSL vs JSON) | ~90% |
| Build time (147 files) | 1.58s |
| Platforms | Windows + Linux |

## Known Limitations

- Python-only analysis — other languages return file-level nodes only
- Keyword-based search (no semantic/embedding matching)
- No MCP server integration yet (Phase 2)
- No incremental rebuild — full rebuild on every `ctx build`
- MCP server file exists as a skeleton only (`src/ctxgraph/mcp/server.py`), requires `mcp>=1.0.0`
