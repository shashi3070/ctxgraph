# Changelog

## v0.5.7 (2026-06-06)

### Fixed
- Re-upload to PyPI with architecture image already live on GitHub master so it renders correctly

## v0.5.6 (2026-06-06)

### Changed
- Fixed approach comparison image URL to use raw GitHub link so it renders on PyPI
- Replaced hero architecture image with new overview diagram, kept graph.svg below it

## v0.5.5 (2026-06-06)

### Changed
- Restructured README: MCP/Claude use case now leads the hero, approach comparison moved to
  "Why ctxgraph?" section, `ctx serve` promoted to first command in Commands section

## v0.5.4 (2026-06-06)

### Fixed
- `ctx chat` `/resume` crash: `MarkupError: closing tag '[/]' has nothing to close` when
  session picker rendered a non-highlighted row with empty style string, producing
  `[]...[/]` which Rich interpreted as markup tags. Now uses `escape()` for all text
  content and row-level `style=` parameter instead of inline markup wrapping.

## v0.5.3 (2026-06-06)

### Fixed
- MCP server now captures and displays the actual `mcp` import error instead of a generic
  "missing dependencies" message, making Windows security policy issues (e.g. `pywintypes.dll`
  blocked by AppLocker/Defender) diagnosable
- Added specific detection of `pywintypes.dll` load failures with a suggested workaround
  (`pip install mcp==1.0.0`)

## v0.5.2 (2026-06-06)

### Added
- `read_file` MCP tool — Claude can read actual source file contents from the repo (with path traversal protection)
- `search_files` MCP tool — Claude can discover files by glob pattern (e.g. `**/*service*`, `src/**/*.py`)
- `read_file` response now includes line count and token estimate (e.g. `Line count: 47 | Tokens: ~612`)

### Changed
- README MCP tools list updated with `read_file` and `search_files`

## v0.5.1 (2026-06-06)

### Added
- `CTXGRAPH_REPO_PATH` environment variable support — MCP server now checks this env var when neither `--repo` nor a `.ctxgraph` walk-up resolves, making Claude Desktop integration reliable on Windows
- Diagnostic stderr output in MCP server — prints the resolved repo root and graph DB path on startup, so users can see exactly where the server is looking

### Changed
- MCP server "no graph found" error now includes the exact path searched and suggests using `--repo` or `CTXGRAPH_REPO_PATH`
- README Claude Desktop config examples updated with `--repo` and `CTXGRAPH_REPO_PATH` patterns
- Windows note added to MCP section

## v0.5.0 (2026-06-06)

### Added
- `_find_repo_root()` in MCP server — auto-discovers project root by walking up from `cwd()` looking for `.ctxgraph/`
- `_parse_toml_value()` in settings — properly parses unquoted TOML values as `int`, `float`, or `bool` instead of always storing as strings
- Defensive `int()`/`float()` conversions in all numeric setting properties (`chat_max_session_tokens`, `temperature`, `max_tokens`, `max_nodes`, `max_depth`)

### Fixed
- `TypeError: can't multiply sequence by non-int of type 'float'` in chat mode when `max_session_tokens` was read from TOML config
- Custom TOML parser now correctly distinguishes quoted strings from unquoted numeric/bool values

### Changed
- README rewritten to clearly communicate dual nature: works as a token-saving context engine (no LLM needed) and as a full AI coding assistant (with Ollama/Claude/OpenAI)
- Package description updated

## v0.3.1 (2026-06-06)

### Changed
- Comprehensive README rewrite with full feature coverage, Quick Start, example output, custom skill guide, per-command flag tables, and Python API examples for all new modules (history, skills, savings)

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
