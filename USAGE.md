# ctxgraph — Usage Guide

## Quick Start

```bash
# Install
pip install ctxgraph

# Build graph for current project
ctx build

# Generate context capsule for a task
ctx capsule "add user authentication"

# Search the graph
ctx query "auth jwt"

# Visualize dependencies
ctx view

# Graph info
ctx info
```

---

## Commands

### `ctx build` — Build knowledge graph

```bash
# Current directory
ctx build

# Specific repo
ctx build /path/to/project
ctx build --repo /path/to/project

# Custom exclude patterns
ctx build --exclude "vendor/*" --exclude "legacy/*"

# Custom database path
ctx build --db /tmp/mygraph.db
```

Builds a multi-layer graph from Python AST analysis:

| Layer | What it extracts |
|-------|-----------------|
| **Imports** | `import X`, `from X import Y` → file-to-file edges |
| **Symbols** | Classes, functions, methods, async defs, calls, inheritance |
| **Semantic** | Docstring summaries → node enrichment |

Excluded by default: `__pycache__`, `.git`, `venv`, `node_modules`, `dist`, `build`, `*.egg-info`, `.pytest_cache`, migrations, minified files.

---

### `ctx capsule <query>` — Generate context capsule

```bash
# Default (balanced)
ctx capsule "fix JWT token validation"

# Fast mode — minimal context (10 nodes, depth 1)
ctx capsule "fix JWT token validation" --mode fast

# Deep mode — comprehensive context (40 nodes, depth 3)
ctx capsule "fix JWT token validation" --mode deep

# Project overview (no query needed)
ctx capsule --overview

# Specific repo
ctx capsule "add logging" --repo /path/to/project
```

Output is a token-efficient DSL format:

```
[CTX]fix JWT token validation

[F]src/auth/jwt.py
  D:JWT token lifecycle, validation
  S:JWTValidator, create_token, decode

[C]JWTValidator
  D:Validates JWT tokens, checks expiry

[DEP]
  auth/jwt.py -> auth/session.py
  auth/jwt.py -> core/redis.py
```

---

### `ctx query <search>` — Search graph

```bash
# Search by name, summary, or path
ctx query "user auth"

# Specify mode
ctx query "payment gateway" --mode deep

# Different repo
ctx query "database models" --repo /path/to/project
```

Returns ranked results with relevance scores.

---

### `ctx view` — Visualize graph

```bash
# Open in browser
ctx view

# Save to file
ctx view --output graph.html

# Custom port
ctx view --port 8080

# Don't open browser
ctx view --no-open
```

Generates an interactive D3.js force-directed HTML graph with:

- Search/filter by node type
- Pan, zoom, drag
- Hover tooltips with node details
- Color-coded by type (file, class, function)

---

### `ctx serve` — MCP server (experimental)

```bash
# Install MCP support
pip install ctxgraph[mcp]

# Start MCP server (stdio mode)
ctx serve

# With specific repo
ctx serve --repo /path/to/project
```

Starts a Model Context Protocol server for dynamic graph queries.
Claude Desktop config:

```json
{
  "mcpServers": {
    "ctxgraph": {
      "command": "ctx",
      "args": ["serve"]
    }
  }
}
```

Exposed tools:

| Tool | Description |
|------|-------------|
| `search_graph` | Search codebase for relevant files, classes, functions |
| `get_context_capsule` | Generate token-efficient context for a task |
| `get_file_dependencies` | Get dependency graph for a specific file |
| `get_project_overview` | High-level project structure |

---

### `ctx info` — Graph statistics

```bash
ctx info

# Output:
# ┌────────────────────┬───────┐
# │ Total Nodes        │ 1090  │
# │ Total Edges        │ 1565  │
# │   files            │ 147   │
# │   classes          │ 45    │
# │   functions        │ 312   │
# │ Last Build         │ ...   │
# └────────────────────┴───────┘
```

---

## Modes

| Mode | Max Nodes | BFS Depth | Use Case |
|------|-----------|-----------|----------|
| `fast` | 10 | 1 | Quick questions, small fixes |
| `balanced` (default) | 20 | 2 | General development |
| `deep` | 40 | 3 | Complex refactoring, architecture |

---

## Claude Wrapper (`ccg`)

```bash
# Single-shot: ask Claude a question with context
ccg "fix the JWT expiry bug in auth module"

# Interactive mode: open Claude session with context
ccg --chat "refactor the payment flow"

# Project overview
ccg --overview

# With specific mode
ccg --mode deep "redesign the database schema"
```

The wrapper:

1. Captures your query
2. Runs `ctx capsule` to generate context
3. Wraps it as `[CONTEXT]...capsule...[/CONTEXT]` with your task
4. Launches Claude CLI (single-shot) or starts interactive session

---

## Configuration

Config file: `.ctxgraph/config.toml` (or `.ctxgraph/config.json`)

```toml
# .ctxgraph/config.toml
[graph]
exclude = ["legacy/*", "vendor/*"]

[ai]
provider = "ollama"           # ollama, claude, openai, custom
model = "qwen2.5-coder:7b"
endpoint = "http://localhost:11434"

[context]
mode = "balanced"
max_nodes = 20
max_depth = 2
```

Environment overrides:

| Variable | Overrides |
|----------|-----------|
| `CTXGRAPH_PROVIDER` | `ai.provider` |
| `CTXGRAPH_MODEL` | `ai.model` |
| `CTXGRAPH_ENDPOINT` | `ai.endpoint` |
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |

---

## Provider Switching

```bash
# Ollama (default, no API key needed)
ctx capsule "query"

# Claude
CTXGRAPH_PROVIDER=claude CTXGRAPH_MODEL=claude-sonnet-4-20250514 ctx capsule "query"

# OpenAI
CTXGRAPH_PROVIDER=openai CTXGRAPH_MODEL=gpt-4o ctx capsule "query"

# Custom (any OpenAI-compatible API)
CTXGRAPH_PROVIDER=custom CTXGRAPH_ENDPOINT=http://my-api/v1 ctx capsule "query"
```

---

## Project Layout

```
.ctxgraph/
├── graph.db          # SQLite knowledge graph
├── context.md        # Current context (for --chat mode)
└── graph.html        # Exported D3.js visualization
```

---

## Examples

### Debug a failing test

```bash
# 1. Build the graph
ctx build

# 2. Ask about the test
ctx capsule "test_user_login is failing with auth error" --mode deep

# Output capsule →
# [F]tests/test_auth.py
# [F]src/auth/login.py
# [C]AuthService
# [DEP]...dependency chain...
```

### Understand a new codebase

```bash
# Quick overview
ctx capsule "project architecture" --overview

# Interactive exploration
ccg --chat "explain the overall architecture and data flow"
```

### Refactor across modules

```bash
# Deep context for complex task
ctx capsule "extract payment processing into separate module" --mode deep
```
