# ctxgraph — AI Context Engine for Python

**Slash your LLM token costs by 97%.** ctxgraph builds a multi-layer knowledge graph from your Python codebase, then generates *compact context capsules* — delivering only what your AI needs, not every line of code.

```bash
pip install ctxgraph

ctx build                          # Build knowledge graph
ctx capsule "fix JWT expiry"       # 92-99% fewer tokens vs raw code
ccg "fix the login redirect bug"   # Launch Claude with context pre-loaded
ctx view                           # Interactive D3.js visualization (or --svg for static)
```

<img src="https://raw.githubusercontent.com/shashi3070/ctxgraph/master/docs/graph.svg" alt="ctxgraph knowledge graph visualization" width="100%">

---

## Why ctxgraph?

Sending entire files to an AI is wasteful. ctxgraph analyzes your code with AST-based static analysis, stores the result in a queryable SQLite graph, and retrieves *only the relevant nodes* — compressed into a token-efficient DSL format.

| Without ctxgraph | With ctxgraph | Savings |
|:---|---:|:---:|
| All files dumped to context | Targeted capsule (10-40 nodes) | **97% fewer tokens** |
| JSON-formatted metadata | Custom DSL format | **4.7× less than JSON** |
| Model guesses filenames | Graph provides exact paths | **+16.7pp answer coverage** |

---

## How It Works

```
Repository (.py files)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  ctx build                                               │
│                                                          │
│  1. importer.py (AST)  →  import edges (file→file)       │
│  2. symbols.py (AST)   →  classes, functions, methods    │
│  3. semantic.py        →  docstring summaries            │
│                                                          │
│  Store: SQLite (nodes + edges)                           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  ctx capsule "<query>"                                  │
│                                                          │
│  1. Tokenize query → keyword search                      │
│  2. Score: name matches (2x), text (0.5x)                │
│  3. BFS neighborhood expansion (depth=1-3)               │
│  4. Render token-efficient DSL → AI-ready capsule        │
└─────────────────────────────────────────────────────────┘
```

### Architecture

```
┌─────────┐    ┌──────────────┐    ┌──────────────┐
│   CLI   │───▶│  Analyzers   │───▶│   SQLite DB  │
│  typer  │    │  AST-based   │    │  .ctxgraph/  │
└────┬────┘    └──────────────┘    └──────┬───────┘
     │                                    │
     ├── ctx build ──────────────────────▶│  Graph build
     │                                    │
     ├── ctx capsule ◀───────────────────│  Query + BFS
     │                                    │
     ├── ctx query ◀─────────────────────│  Keyword search
     │                                    │
     ├── ctx view ◀──────────────────────│  D3.js viz
     │                                    │
     ├── ctx serve ◀─────────────────────│  MCP server
     │                                    │
     └── ccg wrapper ───▶ Claude Code ───┘  AI tool
```

---

## Token Efficiency

### The DSL Advantage

ctxgraph's compact format uses **79% fewer tokens** than JSON for the same data:

```
JSON: 426 tokens                        DSL: 143 tokens
─────                                     ────
{                                         [CTX]calculator expression parsing
  "nodes": [
    {                                     [F]calc/parser.py
      "id": "file:calc/parser.py",         D:Tokenize and parse math expressions
      "type": "file",                      S:tokenize, parse, Expression
      "name": "parser.py",               [F]calc/core.py
      ...                                  D:Core math operations
    }                                     [C]Calculator
  ],                                       D:Main calculator class
  "edges": [...]                          [DEP]
}                                           parser.py → core.py
                                            parser.py → plugins.py
```

**4.7× compression ratio** vs equivalent JSON — tested across all benchmark projects.

### Capsule vs Raw Files

| Project | Files | Raw Tokens | Avg Capsule | Savings | Build Time |
|---------|:-----:|:----------:|:-----------:|:-------:|:----------:|
| tiny_app | 7 | 1,558 | ~112 | **92.8%** | ~82ms |
| web_api | 23 | 6,567 | ~136 | **97.9%** | ~474ms |
| microsvc | 22 | 10,587 | ~63 | **99.4%** | ~916ms |
| dataflow | 35 | ~12,500 | ~78 | **~99.4%** | ~560ms |

> **97.0% average token reduction** across 4 projects, 42 benchmark runs. The larger the project, the greater the savings.

### With Graph vs Without (Ollama)

| Query | No Context | With ctxgraph | Δ |
|-------|:----------:|:-------------:|:-:|
| Calculator expression parsing | 100% | 100% | — |
| Plugin registration system | 33% | **100%** | **+67pp** |
| JWT authentication (web_api) | 75% | **100%** | **+25pp** |
| Middleware pipeline (web_api) | 100% | 100% | — |
| Circuit breaker (microsvc) | 75% | 75% | — |
| Services & communication | 50% | **100%** | **+50pp** |
| PipelineBuilder pattern | 100% | 75% | -25pp* |
| Processor registration | 33% | **67%** | **+34pp** |
| Event bus & error handling | 100% | 100% | — |
> \* Without context the model gave a generic answer matching all keywords; with context it focused on actual code — more honest, more useful.

**+16.7pp average coverage improvement** — better answers, concrete file names, real code structure.

---

## Commands

### `ctx build` — Build knowledge graph
```bash
ctx build                        # Current directory
ctx build /path/to/project       # Specific repo
ctx build --exclude "vendor/*"   # Custom exclude patterns
```

### `ctx capsule <query>` — Generate context
```bash
ctx capsule "fix JWT token validation"              # Balanced (default: 20 nodes, depth 2)
ctx capsule "fix JWT token validation" --mode fast  # Fast (10 nodes, depth 1)
ctx capsule "fix JWT token validation" --mode deep  # Deep (40 nodes, depth 3)
ctx capsule --overview                              # Project architecture overview
```

| Mode | Max Nodes | BFS Depth | When to Use |
|------|:---------:|:---------:|-------------|
| `fast` | 10 | 1 | Quick questions, small fixes |
| `balanced` (default) | 20 | 2 | General development |
| `deep` | 40 | 3 | Complex refactoring, architecture |

### `ctx query <search>` — Search graph
```bash
ctx query "user auth"
ctx query "payment gateway" --mode deep
```
Returns ranked nodes with relevance scores.

### `ctx view` — Visualize graph
```bash
ctx view
ctx view --output graph.html
ctx view --port 8080 --no-open
```
Interactive D3.js force-directed HTML — no JS build tools needed.

### `ctx serve` — MCP server
```bash
pip install ctxgraph[mcp]
ctx serve
```
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
Tools: `search_graph`, `get_context_capsule`, `get_file_dependencies`, `get_project_overview`.

### `ctx info` — Graph statistics
```bash
ctx info
# ┌────────────────────┬───────┐
# │ Total Nodes        │ 1090  │
# │ Total Edges        │ 1565  │
# │   files            │ 147   │
# │   classes          │ 45    │
# │   functions        │ 312   │
# └────────────────────┴───────┘
```

---

## Claude Wrapper (`ccg`)

```bash
ccg "fix the JWT expiry bug in auth module"          # Single-shot
ccg --chat "refactor the payment flow"               # Interactive session
ccg --overview                                        # Project overview
ccg --mode deep "redesign the database schema"        # Deep mode
```

---

## Configuration

`.ctxgraph/config.toml`:
```toml
[graph]
exclude = ["legacy/*", "vendor/*"]

[ai]
provider = "ollama"           # ollama, claude, openai, azure, custom
model = "qwen2.5-coder:7b"
endpoint = "http://localhost:11434"

[context]
mode = "balanced"
max_nodes = 20
max_depth = 2
```

| Environment Variable | Overrides |
|----------------------|-----------|
| `CTXGRAPH_PROVIDER` | `ai.provider` |
| `CTXGRAPH_MODEL` | `ai.model` |
| `CTXGRAPH_ENDPOINT` | `ai.endpoint` |
| `ANTHROPIC_API_KEY` | Claude API |
| `OPENAI_API_KEY` | OpenAI API |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API |

```bash
# Ollama (default — no env vars needed)
ctx capsule "query"

# Claude
CTXGRAPH_PROVIDER=claude CTXGRAPH_MODEL=claude-sonnet-4-20250514 ctx capsule "query"

# OpenAI
CTXGRAPH_PROVIDER=openai CTXGRAPH_MODEL=gpt-4o ctx capsule "query"

# Azure OpenAI
CTXGRAPH_PROVIDER=azure \
  CTXGRAPH_MODEL=gpt-4o \
  CTXGRAPH_ENDPOINT=https://my-resource.openai.azure.com \
  AZURE_OPENAI_API_KEY=sk-... \
  ctx capsule "query"

# Custom (OpenAI-compatible)
CTXGRAPH_PROVIDER=custom CTXGRAPH_ENDPOINT=http://my-api/v1 ctx capsule "query"
```

> **Windows (PowerShell):** Use `$env:` prefix instead:
> ```powershell
> $env:CTXGRAPH_PROVIDER = "azure"; $env:CTXGRAPH_MODEL = "gpt-4o"; ctx capsule "query"
> ```
> Or set them once per session:
> ```powershell
> $env:CTXGRAPH_PROVIDER = "azure"
> $env:AZURE_OPENAI_API_KEY = "sk-..."
> ctx capsule "query"
> ```

---

## Use Cases

### Debug a failing test
```bash
ctx build
ctx capsule "test_user_login is failing with auth error" --mode deep
# → [F]tests/test_auth.py
#   [F]src/auth/login.py
#   [C]AuthService
#   [DEP] auth/login.py → core/database.py, auth/session.py
```

### Understand a new codebase
```bash
ctx capsule "project architecture" --overview
ccg --chat "explain the overall architecture and data flow"
```

### Refactor across modules
```bash
ctx capsule "extract payment processing into separate module" --mode deep
```

---

## Framework Integrations

ctxgraph is a Python library first — the CLI is just a wrapper. This makes it easy to feed code context into LangChain, LangGraph, OpenAI Agents, or any LLM pipeline.

### How the Python API works

The flow is always the same:

1. **`build_graph(path)`** → scans your code, stores a knowledge graph in `path/.ctxgraph/graph.db`
2. **`get_storage(path)`** → opens that SQLite database for queries (fast, no re-scanning)
3. **`render_capsule(storage, query)`** → searches the graph, returns a compact text capsule

```python
from pathlib import Path
from ctxgraph.graph.builder import build_graph, get_storage
from ctxgraph.capsule.renderer import render_capsule
from ctxgraph.graph.query import search_relevant_nodes

# --- Step 1: Build (one-time, ~0.1-1s per project) ---
stats = build_graph(Path("/path/to/my_project"))
print(f"Built: {stats['total_nodes']} nodes, {stats['total_edges']} edges")

# --- Step 2: Use (instant — reads the .db file) ---
storage = get_storage(Path("/path/to/my_project"))

# Generate a capsule — a token-efficient DSL string
capsule = render_capsule(storage, "fix JWT token validation", max_nodes=20)
print(capsule)
# → [CTX]fix JWT token validation
#   [F]src/auth/jwt.py
#     D:JWT token creation and validation
#   [F]src/auth/middleware.py
#     D:Auth middleware for request validation
#   ...

# Or search for nodes programmatically
results = search_relevant_nodes(storage, "auth login", max_nodes=10, max_depth=2)
for node, score in results:
    print(f"  {node.type}:{node.name}  (score={score})")
```

> **Tip:** `build_graph` is a one-time setup. In production, run `ctx build` during CI/deployment and let your app code only call `get_storage` + `render_capsule`.

### LangChain

Pass the capsule as context in your prompt template. The LLM gets exactly the files, classes, and dependencies it needs — no token waste.

```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ctxgraph.graph.builder import get_storage          # graph already built
from ctxgraph.capsule.renderer import render_capsule

# Load existing graph (zero build time)
storage = get_storage(Path("./my_project"))

# Generate capsule for the question
context = render_capsule(storage, "login rate limiter", max_nodes=15)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a senior Python dev. Answer using the code context below.\n\n{context}"),
    ("user", "{question}"),
])

llm = ChatOpenAI(model="gpt-4o")
response = prompt | llm | (lambda msg: msg.content)

print(response.invoke({
    "context": context,
    "question": "Where is the rate limiter applied in the login flow?",
}))
# → "The rate limiter is in src/auth/middleware.py at line 42.
#    It wraps the login endpoint with a 5req/min limit per IP."
```

### LangGraph

Expose ctxgraph as a tool the agent calls on-demand. The agent fetches context only when it hits a code-related question.

```python
from pathlib import Path
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from ctxgraph.graph.builder import get_storage
from ctxgraph.capsule.renderer import render_capsule

# Pre-built graph — loaded instantly
_storage = get_storage(Path("./my_project"))

@tool
def code_context(task: str) -> str:
    """Fetch relevant source code for a development task.
    Use this whenever the user asks about implementation details,
    bug fixes, or architecture in the codebase."""
    return render_capsule(_storage, task, max_nodes=20)

# --- Build LangGraph ---
tools = [code_context]
model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools)

def agent_node(state: MessagesState):
    return {"messages": [model.invoke(state["messages"])]}

graph = StateGraph(MessagesState)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    lambda s: "tools" if s["messages"][-1].tool_calls else "__end__",
)
graph.add_edge("tools", "agent")

app = graph.compile()

# --- Run ---
for chunk in app.stream({"messages": [("user", "How does payment retry work?")]}):
    for node, vals in chunk.items():
        msg = vals["messages"][0]
        if hasattr(msg, "content") and msg.content:
            print(f"[{node}]: {msg.content[:300]}")
```

When the user asks about code, the agent calls `code_context("payment retry")`, gets back a capsule with `[F]src/payment/retry.py`, `[F]src/payment/processor.py`, and their dependency edges, then answers with those files in context.

### OpenAI Agents SDK

Same pattern — ctxgraph is a function tool the agent invokes.

```python
from pathlib import Path
from agents import Agent, Runner, function_tool
from ctxgraph.graph.builder import get_storage
from ctxgraph.capsule.renderer import render_capsule

_storage = get_storage(Path("./my_project"))

@function_tool
def fetch_code_context(task_description: str) -> str:
    """Retrieve code context from the project's knowledge graph.
    Provide a task description like 'JWT auth middleware' or 'payment processor'."""
    return render_capsule(_storage, task_description, max_nodes=20)

agent = Agent(
    name="Code Assistant",
    instructions="You help developers understand their codebase. Use fetch_code_context to get relevant files before answering.",
    model="gpt-4o",
    tools=[fetch_code_context],
)

result = Runner.run_sync(agent, "How does the notification system handle email vs SMS?")
print(result.final_output)
```

### Azure OpenAI (direct client)

For Azure OpenAI or any OpenAI-compatible endpoint, inject the capsule directly into the system message.

```python
import os
from openai import AzureOpenAI
from pathlib import Path
from ctxgraph.graph.builder import get_storage
from ctxgraph.capsule.renderer import render_capsule

storage = get_storage(Path("./my_project"))
context = render_capsule(storage, "event bus architecture", max_nodes=25)

client = AzureOpenAI(
    api_version="2024-08-01-preview",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)

response = client.chat.completions.create(
    model="gpt-4o",  # deployment name
    messages=[
        {"role": "system", "content": f"You are a senior developer. Code context:\n\n{context}"},
        {"role": "user", "content": "How do I add a new event handler?"},
    ],
)
print(response.choices[0].message.content)
```

---

## Development

```bash
git clone https://github.com/shashi3070/ctxgraph.git
cd ctxgraph
pip install -e ".[dev]"
pytest
python benchmarks/run_benchmarks.py
python benchmarks/run_ollama_comparison.py   # Requires local Ollama
```

### Project Structure
```
src/ctxgraph/
├── cli/main.py              — Typer CLI (6 commands)
├── graph/
│   ├── models.py            — Node, Edge, Graph dataclasses
│   ├── storage.py           — SQLite persistence
│   ├── builder.py           — Graph build orchestrator
│   └── query.py             — Tokenizer + BFS + relevance scoring
├── capsule/renderer.py      — DSL context generation
├── analyzers/python/
│   ├── importer.py          — AST import extraction
│   ├── symbols.py           — AST class/function/method analysis
│   └── semantic.py          — Docstring summarization
├── config/
│   ├── settings.py          — TOML/JSON/env config loading
│   └── providers.py         — Ollama, Claude, OpenAI clients
├── clients/models.py        — Mode enum (fast/balanced/deep)
├── exclude/patterns.py      — Exclusion pattern matching
├── view/visualizer.py       — D3.js HTML graph generator
├── wrapper/claude.py        — ccg Claude wrapper
└── mcp/server.py            — MCP protocol server
```

---

## Limitations

- **Python-only analysis** — other languages get file-level nodes only
- **Keyword-based search** — no semantic/embedding matching (planned)
- **No incremental rebuild** — full rebuild on every `ctx build` (planned)
- **MCP server** — stdio mode only, SSE not yet supported

---

## License

MIT
