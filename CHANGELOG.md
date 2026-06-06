# Changelog

## v0.3.0 (2026-06-06)

### Added
- `ctx init` — scaffold `.ctxgraph/` directory with `config.toml`, default skills, and `history.jsonl`
- `ctx ask <query>` — ask questions about the codebase via LLM (Ollama/Claude/OpenAI) with automatic token savings display
- `ctx history [--tail N] [--filter F] [--stats]` — query history viewer with aggregate statistics
- `ctx skill list|show <name>` — skills system with two default skills (`project-style`, `field-guide`)
- `ctx capsule --savings` — token savings table comparing capsule DSL vs raw `.py` files vs JSON
- `ctx capsule --skill <name>` — prepend skill context to capsules
- `ctx ask --graph` — show graph search results alongside LLM answer
- `ctx ask --provider` / `--model` — override LLM provider/model per query
- `ctx build --provider` / `--model` — forward provider/model settings
- History module: JSONL append, tail/filter/stats queries, auto-prune
- Skills module: TOML-based skill discovery, built-in defaults, per-command activation
- Token savings module: rough token estimation for raw `.py` files, capsule DSL, and JSON equivalent
- 14 new end-to-end tests (78 total)

### Changed
- Capsule renderer accepts optional `skill_context` parameter for skill system prompt prepend
- Settings module: provider/model endpoint forwarded to `--provider`/`--model` CLI flags

## v0.2.4 (2026-06-02)

### Fixed
- README framework examples rewritten with clearer 3-step flow (build → get_storage → render_capsule)

## v0.2.3 (2026-06-02)

### Fixed
- README provider examples: added Windows PowerShell `$env:` syntax

## v0.2.2 (2026-06-02)

### Fixed
- README graph image now uses absolute GitHub URL (renders on PyPI)

## v0.2.1 (2026-06-02)

### Added
- Azure OpenAI provider (`CTXGRAPH_PROVIDER=azure`, `AZURE_OPENAI_API_KEY`)
- `ctx view --svg` — static SVG graph output
- `docs/graph.svg` — graph visualization embedded in README
- Framework integrations guide — LangChain, LangGraph, OpenAI Agents SDK, Azure OpenAI
- Python API examples in README (`build_graph`, `render_capsule`, `search_relevant_nodes`)

### Changed
- README rewritten with polished hero, better tables, graph image
- PyPI description now highlights token efficiency

## v0.2.0 (2026-06-02)

### Added
- `ctx serve` command — starts MCP server for dynamic graph queries via the Model Context Protocol
- MCP optional dependency group (`pip install ctxgraph[mcp]`)
- `benchmarks/projects/dataflow/` — 35-file complex benchmark project (event-driven pipeline engine)
- `benchmarks/run_ollama_comparison.py` — with/without graph LLM answer quality comparison
- `CHANGELOG.md`, `USAGE.md`, comprehensive `README.md`

### Changed
- `mcp/server.py` is no longer a skeleton — fully wired to CLI
- `__init__.py` removed from `DEFAULT_EXCLUDE` — legitimate source file
- Benchmark baseline corrected: `raw_tokens` counts **all** `.py` files (not just graph nodes)
- README, PROGRESS.md, WORKFLOW.md rewritten with benchmark results and architecture docs
- PyPI description updated for token efficiency focus

### Fixed
- `test_config.py:test_exclude_patterns` — removed undefined `tmp_path` reference
- Duplicate `__pycache__` entry in `DEFAULT_EXCLUDE`

### Benchmark Results
- **97.0%** average token savings (capsule vs raw files) across 4 projects, 42 runs
- **4.7x** compression vs equivalent JSON format
- **+16.7pp** average LLM answer coverage improvement (Ollama comparison)

## v0.1.0 (2026-05-23)

Initial release:
- `ctx build` — AST-based knowledge graph builder for Python projects
- `ctx capsule <query>` — Token-efficient DSL context capsule generation
- `ctx query <term>` — Keyword search with BFS neighborhood expansion
- `ctx view` — D3.js force-directed HTML graph visualizer
- `ctx info` — Graph statistics
- `ccg` wrapper — Claude Code integration with interactive/single-shot modes
- Configuration system (TOML/JSON/env)
- LLM providers (Ollama, Claude, OpenAI, custom)
- Exclusion patterns for builds
- 64 passing tests
- Benchmark framework with JSON vs DSL comparison
