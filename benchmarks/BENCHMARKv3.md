# ctxgraph Benchmarks v3 — 50 Test Cases

25 single-shot + 25 multi-turn (5-10 turns each) across `tiny_app`, `web_api`, `microsvc`.

## Single-Shot (25 queries)

| # | Project | Query | Tokens | Saved |
|:-:|:---|:---|:---:|:---:|
| 1 | tiny_app | calculator add subtract multiply | 55 | 96.5% |
| 2 | tiny_app | expression parser tokenize | 65 | 95.8% |
| 3 | tiny_app | plugin system history logging | 82 | 94.7% |
| 4 | tiny_app | math operations core functions | 67 | 95.7% |
| 5 | tiny_app | main entry point CLI | 29 | 98.1% |
| 6 | tiny_app | error handling division | 19 | 98.8% |
| 7 | tiny_app | test calculator functions | 16 | 99.0% |
| 8 | tiny_app | import dependencies | 18 | 98.8% |
| 9 | web_api | user management CRUD | 77 | 98.8% |
| 10 | web_api | JWT auth login register | 92 | 98.6% |
| 11 | web_api | rate limit middleware | 98 | 98.5% |
| 12 | web_api | blog posts publish | 66 | 99.0% |
| 13 | web_api | admin routes permission | 33 | 99.5% |
| 14 | web_api | password hashing auth service | 91 | 98.6% |
| 15 | web_api | middleware pipeline | 98 | 98.5% |
| 16 | web_api | user model fields | 77 | 98.8% |
| 17 | web_api | post service pagination | 79 | 98.8% |
| 18 | microsvc | auth service JWT OAuth | 30 | 99.7% |
| 19 | microsvc | billing payment stripe | 27 | 99.7% |
| 20 | microsvc | notification email push | 23 | 99.8% |
| 21 | microsvc | circuit breaker pattern | 26 | 99.8% |
| 22 | microsvc | service registry discovery | 59 | 99.4% |
| 23 | microsvc | event bus pub sub | 23 | 99.8% |
| 24 | microsvc | distributed tracing | 25 | 99.8% |
| 25 | microsvc | retry backoff timeout | 30 | 99.7% |

**Single-shot average: 52.2 tok/case, 98.6% savings vs raw files.**

## Multi-Turn (25 scenarios, 5-10 turns each)

| # | Project | Scenario | Turns | Total Tok | Avg/Turn | Saved | Graph Coverage |
|:-:|:---|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | tiny_app | Fix divide-by-zero in calculator | 5 | 273 | 54.6 | 82.5% | 59.0% |
| 2 | tiny_app | Add new square root plugin | 6 | 400 | 66.7 | 74.3% | 47.5% |
| 3 | tiny_app | Fix expression parser bug | 5 | 291 | 58.2 | 81.3% | 49.2% |
| 4 | tiny_app | Refactor calculator error handling | 6 | 301 | 50.2 | 80.7% | 67.2% |
| 5 | tiny_app | Add power function to calculator | 5 | 292 | 58.4 | 81.3% | 55.7% |
| 6 | tiny_app | Improve CLI help and usage | 5 | 260 | 52.0 | 83.3% | 59.0% |
| 7 | tiny_app | Add memory store plugin | 6 | 310 | 51.7 | 80.1% | 41.0% |
| 8 | tiny_app | Secure calculator input validation | 6 | 269 | 44.8 | 82.7% | 45.9% |
| 9 | web_api | Add JWT refresh token flow | 7 | 547 | 78.1 | 91.7% | 31.0% |
| 10 | web_api | Fix rate limiter bucket refill | 6 | 469 | 78.2 | 92.9% | 17.5% |
| 11 | web_api | Add user role permissions | 7 | 441 | 63.0 | 93.3% | 28.1% |
| 12 | web_api | Optimize blog post pagination | 6 | 415 | 69.2 | 93.7% | 22.2% |
| 13 | web_api | Implement password reset flow | 7 | 515 | 73.6 | 92.2% | 24.6% |
| 14 | web_api | Build admin analytics dashboard | 6 | 424 | 70.7 | 93.5% | 25.1% |
| 15 | web_api | Add API versioning support | 6 | 467 | 77.8 | 92.9% | 30.4% |
| 16 | web_api | Implement request body validation | 6 | 409 | 68.2 | 93.8% | 31.6% |
| 17 | web_api | Add audit logging middleware | 7 | 449 | 64.1 | 93.2% | 29.2% |
| 18 | microsvc | Add OAuth2 GitHub provider | 8 | 197 | 24.6 | 98.1% | 12.4% |
| 19 | microsvc | Fix billing invoice rounding | 7 | 159 | 22.7 | 98.5% | 15.7% |
| 20 | microsvc | Add SMS notification provider | 6 | 146 | 24.3 | 98.6% | 11.1% |
| 21 | microsvc | Tune circuit breaker thresholds | 7 | 209 | 29.9 | 98.0% | 11.1% |
| 22 | microsvc | Add health check to service discovery | 6 | 192 | 32.0 | 98.2% | 9.8% |
| 23 | microsvc | Implement event bus retry mechanism | 8 | 207 | 25.9 | 98.0% | 18.3% |
| 24 | microsvc | Add distributed tracing headers | 7 | 186 | 26.6 | 98.2% | 13.4% |
| 25 | microsvc | Build metrics endpoint for Prometheus | 8 | 192 | 24.0 | 98.2% | 11.4% |

**Multi-turn average: 320.8 tot tok, 51.6 tok/turn, 90.8% savings, 30.7% graph coverage per scenario.**

## Key Findings

| Metric | Single-Shot | Multi-Turn |
|--------|:---:|:---:|
| Total test cases | 25 | 25 |
| Avg tokens | 52.2/case | 51.6/turn |
| Avg savings vs raw | 98.6% | 90.8% |
| Total tokens across all cases | 1,305 | 8,020 |
| Equivalent raw tokens | ~93,000 | ~156,000 |
| Overall savings | **98.6%** | **94.9%** |
| Avg turns per scenario | — | 6.4 |
| Avg graph coverage | — | 30.7% |

## How to Run

### Normal (no enrichment, AST-only summaries)
```bash
# Full v3 suite (all 50 cases)
python benchmarks/run_benchmarks_v3.py

# 25 single-shot only
python benchmarks/run_benchmarks_v3.py --single-only

# 25 multi-turn only
python benchmarks/run_benchmarks_v3.py --multiturn-only

# Single project
python benchmarks/run_benchmarks_v3.py --project web_api
```

### With Ollama (local LLM enrichment)
```bash
# Requires Ollama running at http://localhost:11434
python benchmarks/run_benchmarks_v3.py --ollama

# Single project with Ollama
python benchmarks/run_benchmarks_v3.py --project web_api --ollama
```

### With Claude (cloud LLM enrichment)
```bash
# Set Claude provider via env vars
$env:CTXGRAPH_PROVIDER = "claude"
$env:CTXGRAPH_MODEL = "claude-sonnet-4-20250514"
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Run with --ollama flag (uses configured provider)
python benchmarks/run_benchmarks_v3.py --ollama
```

### Switching Providers

| Variable | Example | Purpose |
|----------|---------|---------|
| `CTXGRAPH_PROVIDER` | `claude`, `openai`, `ollama` | Select provider |
| `CTXGRAPH_MODEL` | `claude-sonnet-4-20250514`, `gpt-4o` | Override model |
| `CTXGRAPH_ENDPOINT` | `http://custom:11434` | Override API endpoint |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude API key |
| `OPENAI_API_KEY` | `sk-...` | OpenAI API key |

Or create `.ctxgraph/config.toml` in the project root:
```toml
[ai]
provider = "claude"
model = "claude-sonnet-4-20250514"
api_key = "sk-ant-..."
temperature = 0.1
```

## How to Visualize

```bash
ctx build benchmarks/projects/web_api
ctx view --repo benchmarks/projects/web_api
```
