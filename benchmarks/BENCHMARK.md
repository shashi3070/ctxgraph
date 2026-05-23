# ctxgraph Benchmarks

## Projects

Three synthetic Python projects under `benchmarks/projects/`:

| Project | Files | Description |
|---------|-------|-------------|
| `tiny_app`   | 7   | CLI calculator with plugins, parser, tests |
| `web_api`    | 23  | FastAPI-like web service with middleware, routes, services, models |
| `microsvc`   | 22  | Microservices ecosystem with auth, billing, notifications, shared libs |

## Token Efficiency

### Capsule vs Raw File Reading

Tokens saved by using ctxgraph capsule instead of feeding raw source files.

| Project | Query | Mode | Capsule Tokens | Raw File Tokens | Saved |
|---------|-------|------|---------------|-----------------|-------|
| tiny_app | math operations | fast | 18 | 1,533 | **98.8%** |
| tiny_app | calculator | balanced | 89 | 1,533 | **94.2%** |
| tiny_app | parse expression | deep | 144 | 1,533 | **90.6%** |
| web_api | admin routes | fast | 32 | 6,191 | **99.5%** |
| web_api | user management | balanced | 135 | 6,191 | **97.8%** |
| web_api | JWT auth login | deep | 265 | 6,191 | **95.7%** |
| microsvc | auth service | fast | 12 | 10,342 | **99.9%** |
| microsvc | payment billing | balanced | 42 | 10,342 | **99.6%** |
| microsvc | service discovery | deep | 88 | 10,342 | **99.1%** |

### JSON vs DSL Format

Tokens saved by using the compact DSL format over equivalent JSON.

| Project | Query | DSL Tokens | JSON Tokens | Ratio |
|---------|-------|-----------|-------------|-------|
| tiny_app | calculator | 89 | 354 | **4.0x** |
| tiny_app | parse expression | 129 | 451 | **3.5x** |
| web_api | user management | 135 | 411 | **3.0x** |
| web_api | JWT auth login | 140 | 316 | **2.3x** |
| microsvc | auth service | 32 | 219 | **6.8x** |
| microsvc | payment billing | 42 | 395 | **9.4x** |

### Build Time

| Project | Files | Build Time |
|---------|-------|-----------|
| tiny_app | 7 | ~63ms |
| web_api | 23 | ~190ms |
| microsvc | 22 | ~700ms |

## Ollama LLM Summary (qwen2.5-coder:7b)

Performance of on-demand code summarization via Ollama (local GPU).

| Code Sample | Tokens | Time | Summary Quality |
|------------|--------|------|----------------|
| JWT validation (5 lines) | 49 tok | 18.1s | Accurate — describes decode, expiry handling |
| Circuit breaker class (40 lines) | 62 tok | 26.7s | Accurate — describes pattern, state transitions |
| Full middleware file (196 tok) | 60 tok | 32.0s | Correct — identifies AuthMiddleware, JWT flow |

## Key Takeaways

1. **90-99% token savings** — capsule replaces raw files with structured dependency-aware summaries
2. **2.3-9.4x DSL advantage** — custom DSL is significantly more compact than JSON for the same data
3. **Fast build** — even 22-file projects build in under 1 second
4. **Local LLM works** — qwen2.5-coder:7b produces accurate code summaries (15-32s per call on GPU)

## How to Re-run

```bash
# Run all benchmarks
python benchmarks/run_benchmarks.py

# Run a single project
python benchmarks/run_benchmarks.py --project tiny_app

# Run with specific mode
python benchmarks/run_benchmarks.py --project web_api --mode deep

# Test Ollama summarization (requires running Ollama)
python benchmarks/run_benchmarks.py --ollama

# Raw JSON results saved to:
#   benchmarks/results/benchmark_results.json
```

Results are cached per query in `benchmarks/results/*.db`. Delete `.db` files to force a fresh build.
