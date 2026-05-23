# ctxgraph

Context graph engine for AI coding assistants. Builds a multi-layer knowledge graph of your codebase and generates token-efficient context capsules for Claude and other AI tools.

```bash
pip install ctxgraph
```

```bash
# Build the graph
ctx build

# Generate a context capsule for a task
ctx capsule "fix jwt expiry in auth"

# Launch Claude with context pre-loaded
ccg "fix the login redirect bug"

# Visualize the graph
ctx view
```
