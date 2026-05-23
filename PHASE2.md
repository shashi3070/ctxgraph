# Phase 2: MCP Server & Advanced Features

## Goal

Move from "static context capsule" to "dynamic graph queries" — Claude queries the graph directly via MCP tools instead of receiving a pre-baked capsule.

## MCP Architecture

```
┌─────────────────────┐
│   Claude Desktop     │
│   (or any MCP client)│
└─────────┬───────────┘
          │ MCP Protocol (stdio/SSE)
          ▼
┌─────────────────────┐
│   ctxgraph MCP Server│
│   ctx serve          │
│                      │
│   Tools:             │
│   ├── search_graph   │
│   ├── get_context_   │
│   │   capsule        │
│   ├── get_file_      │
│   │   dependencies   │
│   └── get_project_   │
│       overview       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   SQLite Graph DB   │
│   .ctxgraph/graph.db│
└─────────────────────┘
```

## Configuration

Add to `claude_desktop_config.json`:

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

## MCP Tools

### 1. `search_graph(query, max_results)`
Claude asks: "What depends on auth.py?"
Response: list of related files + symbols with relevance scores

### 2. `get_context_capsule(query, mode)`
Same DSL capsule as Phase 1, but Claude requests it dynamically
when it detects a need for broader context.

### 3. `get_file_dependencies(file_path)`
Returns imports, callers, callees for any file in the graph.

### 4. `get_project_overview()`
High-level module structure for orientation.

## Advanced Features (Post-MVP)

### Runtime Graph (Layer 4)

```python
# Auto-instrument FastAPI/Flask routes
@ctx_trace
@app.get("/api/login")
def login():
    ...

# Generates:
# [ROUTE]/api/login → AuthMiddleware → JWTValidator → Redis
```

### Git Co-Change Graph (Layer 5)

```python
ctx build --git  # include git history

# Generates:
# auth.py → jwt.py (co-changed 15 times in last 30 commits)
# auth.py → session.py (co-changed 8 times)
```

### Relevance Embeddings (Semantic Search)

Replace keyword search with embedding-based similarity:
```python
ctx build --embeddings  # requires sentence-transformers

# Enables:
# "find the rate limiting code" → matches "throttling middleware"
```

### Auto-Watch Mode

```python
ctx watch  # re-build graph on file changes (watchdog)

# On save → re-analyze changed file → update SQLite
```

### Project-wide Graph with LLM Summaries

```python
ctx build --llm-summary  # uses a local/small LLM to write summaries

# Better than docstring-only extraction
```

## Performance Targets

| Feature | Phase 1 | Phase 2 |
|---------|---------|---------|
| Build time (10k files) | ~30s | ~30s |
| Capsule generation | ~50ms | ~10ms (pre-built) |
| MCP query response | N/A | ~5ms |
| Graph storage | ~5MB | ~5MB |
| Token savings vs files | ~90% | ~95% |

## Dependencies for Phase 2

```
mcp>=1.0.0        # MCP protocol server
anyio>=4.0        # async runtime (for MCP)

Optional:
sentence-transformers  # embedding search
watchdog               # file watching
httpx                  # LLM summary API calls
```

## Release Plan

```
v0.1.0  ─── Phase 1: Build + Capsule + View + Wrapper
v0.2.0  ─── Phase 2: MCP Server
v0.3.0  ─── Phase 2: Git graph + Embeddings
v0.4.0  ─── Phase 2: Runtime graph + Auto-watch
v1.0.0  ─── Stable release with all layers
```
