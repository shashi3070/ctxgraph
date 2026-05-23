# ctxgraph Workflow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER                                 │
│  ccg "fix jwt expiry"                                       │
│  ctx build                                                   │
│  ctx capsule "search"                                        │
│  ctx view                                                    │
└───────────┬─────────────────────────────────────────────┬───┘
            │                                             │
            ▼                                             ▼
┌───────────────────────┐                   ┌───────────────────────┐
│   ccg (Claude Wrapper) │                   │   ctx (Graph CLI)     │
│                       │                   │                       │
│  1. Capture query     │                   │  build  → AST analysis│
│  2. ctx capsule       │                   │  capsule → DSL output │
│  3. Inject context    │                   │  query  → search      │
│  4. Launch claude CLI  │                   │  view   → D3.js viz   │
└───────────┬───────────┘                   └───────────┬───────────┘
            │                                           │
            ▼                                           ▼
┌───────────────────────┐                   ┌───────────────────────┐
│    Claude Code (SSO)  │                   │   SQLite Graph DB     │
│                       │                   │   .ctxgraph/graph.db  │
│  Sees: [CONTEXT]      │                   │                       │
│  ...capsule...        │◄──────────────────│  nodes:  files, funcs │
│  [/CONTEXT]           │     queries        │  edges:  imports,     │
│  TASK: fix jwt        │     via MCP (P2)  │         calls, defines│
└───────────────────────┘                   └───────────────────────┘
```

## Data Flow

### Phase 1: Static Graph Build (`ctx build`)

```
Repository (Python files)
    │
    ▼
┌──────────────────────────────────────────────┐
│           ctx build pipeline                  │
│                                               │
│  For each *.py file (excluding patterns):     │
│    │                                          │
│    ├── importer.py (AST)                      │
│    │    └── Extract: import X, from X import Y│
│    │         → Edge: file → file (imports)    │
│    │                                          │
│    ├── symbols.py (AST)                       │
│    │    └── Extract: classes, functions,       │
│    │         methods, async funcs              │
│    │         → Node: class, function          │
│    │         → Edge: file → symbol (defines)  │
│    │         → Edge: symbol → symbol (calls)  │
│    │                                          │
│    └── semantic.py (docstrings)               │
│         └── Extract: module/class/func docs   │
│              → Node.summary                   │
│                                               │
│  Store: nodes table + edges table             │
│    └── SQLite: .ctxgraph/graph.db             │
└──────────────────────────────────────────────┘
```

### Phase 2: Context Capsule (`ctx capsule "query"`)

```
User: "fix JWT expiry in auth"
    │
    ▼
┌──────────────────────────────────────────────┐
│           Relevance Engine                    │
│                                               │
│  1. Tokenize query → ["jwt", "expiry", "auth"]│
│  2. Search nodes by name + summary + path     │
│  3. Score: name match (2x), text match (0.5x) │
│     × importance factor                        │
│  4. BFS from matched nodes (depth=2)          │
│     → include neighbors for context            │
│  5. Rank and select top N nodes               │
│                                               │
│  Output: ranked list of (Node, score) pairs   │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│           DSL Renderer                        │
│                                               │
│  Token-efficient format (vs JSON):            │
│                                               │
│  [CTX]fix JWT expiry in auth                  │
│                                               │
│  [F]src/connectors/auth/jwt.py                │
│    D:JWT token lifecycle, validation          │
│    S:JWTValidator, create_token, decode       │
│                                               │
│  [C]JWTValidator                              │
│    D:Validates JWT tokens                     │
│                                               │
│  [DEP]                                        │
│    auth/jwt.py → auth/session.py              │
│    auth/jwt.py → core/redis.py                │
│                                               │
│  ~90% fewer tokens than equivalent JSON       │
└──────────────────┬───────────────────────────┘
                   ▼
            ┌──────────────┐
            │ Claude sees  │
            │ this context  │
            └──────────────┘
```

### Phase 3: Claude Wrapper (`ccg "fix jwt"`)

```
Terminal: ccg "fix JWT expiry"
    │
    ▼
┌──────────────────────────────────────────────┐
│           ccg wrapper                         │
│                                               │
│  1. Parse: query = "fix JWT expiry"           │
│  2. Detect mode (--mode=fast/balanced/deep)   │
│  3. Generate context capsule                  │
│  4. Build augmented prompt:                   │
│     [CONTEXT]                                 │
│     ...capsule...                             │
│     [/CONTEXT]                                │
│     TASK: fix JWT expiry                      │
│  5. Spawn claude CLI with prompt              │
│                                               │
│  --chat mode: instead spawn interactive       │
│  session with context pre-loaded              │
└──────────────────────────────────────────────┘
```

## Mode Selection

| Mode | Max Nodes | Depth | Use Case |
|------|-----------|-------|----------|
| `--mode=fast` | 10 | 1 | Quick questions, small tasks |
| `--mode=balanced` (default) | 20 | 2 | General development work |
| `--mode=deep` | 40 | 3 | Complex refactoring, architecture |

```
Usage:
  ctx capsule "query" --mode=fast       # minimal context
  ctx capsule "query" --mode=deep       # full context
  ccg --mode=deep "refactor auth flow"  # via wrapper
```

## Exclusion Rules

Default exclusions: `__pycache__`, `.git`, `node_modules`, `venv`, `dist`, `build`, migrations, minified files, etc.

Custom:
```
ctx build --exclude "legacy/*" --exclude "vendor/*"
```

## Project Structure

```
.ctxgraph/
├── graph.db          # SQLite knowledge graph
├── context.md        # Current context (for --chat mode)
└── graph.html        # Exported D3.js visualization
```

## Commands Reference

| Command | Purpose |
|---------|---------|
| `ctx build` | Build knowledge graph from repo |
| `ctx capsule "query"` | Generate context capsule |
| `ctx query "search"` | Search graph interactively |
| `ctx view` | Open D3.js graph visualization |
| `ctx info` | Show graph statistics |
| `ccg "query"` | Claude wrapper (single-shot) |
| `ccg --chat "query"` | Claude wrapper (interactive) |
| `ccg --overview` | Send project overview to Claude |
