# ctxgraph Benchmarks v3 — 50 Test Cases

25 single-shot + 25 multi-turn (5-10 turns each) across `tiny_app`, `web_api`, `microsvc`.

**Methodology**: The baseline is `relevant_raw_tokens` — raw token count of only the files whose symbols appear in the query's context subgraph. This simulates on-demand file loading (a human sending only relevant files to the LLM per turn), which is the realistic alternative to using ctxgraph.

---

## Base (no LLM enrichment)

AST-only summaries (symbol names, file paths, inheritance — no LLM).

### Single-Shot (25 queries)

| # | Project | Query | Relevant Raw | Capsule | vs Relevant | vs All |
|:-:|:---|:---|:---:|:---:|:---:|:---:|
| 1 | tiny_app | calculator add subtract multiply | 1,116 | 61 | 94.5% | 96.1% |
| 2 | tiny_app | expression parser tokenize | 998 | 65 | 93.5% | 95.8% |
| 3 | tiny_app | plugin system history logging | 375 | 82 | 78.1% | 94.7% |
| 4 | tiny_app | math operations core functions | 417 | 74 | 82.3% | 95.3% |
| 5 | tiny_app | main entry point CLI | 1,276 | 89 | 93.0% | 94.3% |
| 6 | tiny_app | error handling division | 0 | 19 | N/A | 98.8% |
| 7 | tiny_app | test calculator functions | 257 | 16 | 93.8% | 99.0% |
| 8 | tiny_app | import dependencies | 0 | 18 | N/A | 98.8% |
| 9 | web_api | user management CRUD | 1,388 | 77 | 94.5% | 98.8% |
| 10 | web_api | JWT auth login register | 1,929 | 92 | 95.2% | 98.6% |
| 11 | web_api | rate limit middleware | 1,253 | 98 | 92.2% | 98.5% |
| 12 | web_api | blog posts publish | 1,573 | 65 | 95.9% | 99.0% |
| 13 | web_api | admin routes permission | 3,271 | 33 | 99.0% | 99.5% |
| 14 | web_api | password hashing auth service | 1,929 | 98 | 94.9% | 98.5% |
| 15 | web_api | middleware pipeline | 1,253 | 100 | 92.0% | 98.5% |
| 16 | web_api | user model fields | 1,388 | 77 | 94.5% | 98.8% |
| 17 | web_api | post service pagination | 1,573 | 78 | 95.0% | 98.8% |
| 18 | microsvc | auth service JWT OAuth | 769 | 30 | 96.1% | 99.7% |
| 19 | microsvc | billing payment stripe | 763 | 27 | 96.5% | 99.7% |
| 20 | microsvc | notification email push | 1,150 | 23 | 98.0% | 99.8% |
| 21 | microsvc | circuit breaker pattern | 389 | 26 | 93.3% | 99.8% |
| 22 | microsvc | service registry discovery | 3,441 | 72 | 97.9% | 99.3% |
| 23 | microsvc | event bus pub sub | 1,683 | 18 | 98.9% | 99.8% |
| 24 | microsvc | distributed tracing | 280 | 25 | 91.1% | 99.8% |
| 25 | microsvc | retry backoff timeout | 1,796 | 56 | 96.9% | 99.5% |

**Average: 1,211 relevant raw → 57 capsule tok/case, 86.3% vs relevant, 98.4% vs all files.**

### Multi-Turn (25 scenarios)

| # | Project | Scenario | Turns | Relevant Raw | Capsule Tot | Avg/Turn | vs Relevant | vs All | Coverage |
|:-:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | tiny_app | Fix divide-by-zero in calculator | 5 | 1,022 | 301 | 60.2 | 70.5% | 80.7% | 57.4% |
| 2 | tiny_app | Add new square root plugin | 6 | 1,533 | 464 | 77.3 | 69.7% | 70.2% | 49.2% |
| 3 | tiny_app | Fix expression parser bug | 5 | 1,373 | 295 | 59.0 | 78.5% | 81.1% | 49.2% |
| 4 | tiny_app | Refactor calculator error handling | 6 | 1,533 | 374 | 62.3 | 75.6% | 76.0% | 67.2% |
| 5 | tiny_app | Add power function to calculator | 5 | 1,533 | 289 | 57.8 | 81.1% | 81.5% | 54.1% |
| 6 | tiny_app | Improve CLI help and usage | 5 | 1,533 | 336 | 67.2 | 78.1% | 78.4% | 62.3% |
| 7 | tiny_app | Add memory store plugin | 6 | 1,533 | 376 | 62.7 | 75.5% | 75.9% | 45.9% |
| 8 | tiny_app | Secure calculator input validation | 6 | 1,533 | 312 | 52.0 | 79.6% | 80.0% | 52.5% |
| 9 | web_api | Add JWT refresh token flow | 7 | 5,904 | 571 | 81.6 | 90.3% | 91.3% | 29.8% |
| 10 | web_api | Fix rate limiter bucket refill | 6 | 2,469 | 471 | 78.5 | 80.9% | 92.8% | 17.5% |
| 11 | web_api | Add user role permissions | 7 | 5,943 | 458 | 65.4 | 92.3% | 93.0% | 27.5% |
| 12 | web_api | Optimize blog post pagination | 6 | 3,466 | 436 | 72.7 | 87.4% | 93.4% | 21.1% |
| 13 | web_api | Implement password reset flow | 7 | 4,684 | 533 | 76.1 | 88.6% | 91.9% | 23.4% |
| 14 | web_api | Build admin analytics dashboard | 6 | 5,943 | 439 | 73.2 | 92.6% | 93.3% | 24.0% |
| 15 | web_api | Add API versioning support | 6 | 5,633 | 480 | 80.0 | 91.5% | 92.7% | 31.6% |
| 16 | web_api | Implement request body validation | 6 | 6,063 | 407 | 67.8 | 93.3% | 93.8% | 31.6% |
| 17 | web_api | Add audit logging middleware | 7 | 6,066 | 509 | 72.7 | 91.6% | 92.2% | 32.7% |
| 18 | microsvc | Add OAuth2 GitHub provider | 8 | 5,455 | 204 | 25.5 | 96.3% | 98.1% | 12.4% |
| 19 | microsvc | Fix billing invoice rounding | 7 | 6,946 | 159 | 22.7 | 97.7% | 98.5% | 15.7% |
| 20 | microsvc | Add SMS notification provider | 6 | 6,426 | 218 | 36.3 | 96.6% | 97.9% | 10.8% |
| 21 | microsvc | Tune circuit breaker thresholds | 7 | 2,952 | 215 | 30.7 | 92.7% | 98.0% | 11.1% |
| 22 | microsvc | Add health check to service discovery | 6 | 5,238 | 211 | 35.2 | 96.0% | 98.0% | 9.8% |
| 23 | microsvc | Implement event bus retry mechanism | 8 | 6,800 | 224 | 28.0 | 96.7% | 97.9% | 19.3% |
| 24 | microsvc | Add distributed tracing headers | 7 | 6,409 | 188 | 26.9 | 97.1% | 98.2% | 13.7% |
| 25 | microsvc | Build metrics endpoint for Prometheus | 8 | 6,608 | 192 | 24.0 | 97.1% | 98.2% | 11.4% |

**Average: 4,184 relevant raw → 347 capsule tot tok, 55.8 tok/turn, 87.5% vs relevant, 89.7% vs all.**

**Overall: 8,662 capsule vs 104,598 relevant raw = 91.7% savings (vs 156,263 all raw = 94.5%).**

---

## With Ollama (qwen2.5-coder:7b enrichment)

Same 50 cases but file summaries enriched by local LLM (5-18 files enriched per project, ~129s total).

### Single-Shot (25 queries)

| # | Project | Query | Relevant Raw | Capsule | vs Relevant | vs All |
|:-:|:---|:---|:---:|:---:|:---:|:---:|
| 1 | tiny_app | calculator add subtract multiply | 1,533 | 301 | 80.4% | 80.7% |
| 2 | tiny_app | expression parser tokenize | 998 | 180 | 82.0% | 88.4% |
| 3 | tiny_app | plugin system history logging | 605 | 165 | 72.7% | 89.4% |
| 4 | tiny_app | math operations core functions | 1,158 | 267 | 76.9% | 82.9% |
| 5 | tiny_app | main entry point CLI | 1,276 | 270 | 78.8% | 82.7% |
| 6 | tiny_app | error handling division | 1,533 | 318 | 79.3% | 79.6% |
| 7 | tiny_app | test calculator functions | 257 | 60 | 76.7% | 96.1% |
| 8 | tiny_app | import dependencies | 0 | 18 | N/A | 98.8% |
| 9 | web_api | user management CRUD | 1,388 | 214 | 84.6% | 96.7% |
| 10 | web_api | JWT auth login register | 1,420 | 256 | 82.0% | 96.1% |
| 11 | web_api | rate limit middleware | 1,253 | 205 | 83.6% | 96.9% |
| 12 | web_api | blog posts publish | 1,573 | 170 | 89.2% | 97.4% |
| 13 | web_api | admin routes permission | 3,271 | 66 | 98.0% | 99.0% |
| 14 | web_api | password hashing auth service | 1,338 | 175 | 86.9% | 97.3% |
| 15 | web_api | middleware pipeline | 1,253 | 294 | 76.5% | 95.5% |
| 16 | web_api | user model fields | 1,388 | 172 | 87.6% | 97.4% |
| 17 | web_api | post service pagination | 1,693 | 221 | 86.9% | 96.6% |
| 18 | microsvc | auth service JWT OAuth | 769 | 69 | 91.0% | 99.3% |
| 19 | microsvc | billing payment stripe | 1,357 | 140 | 89.7% | 98.7% |
| 20 | microsvc | notification email push | 3,171 | 271 | 91.5% | 97.4% |
| 21 | microsvc | circuit breaker pattern | 2,117 | 300 | 85.8% | 97.2% |
| 22 | microsvc | service registry discovery | 3,441 | 343 | 90.0% | 96.8% |
| 23 | microsvc | event bus pub sub | 1,089 | 90 | 91.7% | 99.1% |
| 24 | microsvc | distributed tracing | 3,577 | 354 | 90.1% | 96.7% |
| 25 | microsvc | retry backoff timeout | 1,309 | 241 | 81.6% | 97.7% |

**Average: 1,551 relevant raw → 206 capsule tok/case, 81.3% vs relevant, 94.2% vs all files.**

### Multi-Turn (25 scenarios)

| # | Project | Scenario | Turns | Relevant Raw | Capsule Tot | Avg/Turn | vs Relevant | vs All | Coverage |
|:-:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | tiny_app | Fix divide-by-zero in calculator | 5 | 1,533 | 1,072 | 214.4 | 30.1% | 31.2% | 52.5% |
| 2 | tiny_app | Add new square root plugin | 6 | 1,533 | 1,165 | 194.2 | 24.0% | 25.2% | 45.9% |
| 3 | tiny_app | Fix expression parser bug | 5 | 1,373 | 846 | 169.2 | 38.4% | 45.7% | 47.5% |
| 4 | tiny_app | Refactor calculator error handling | 6 | 1,533 | 1,210 | 201.7 | 21.1% | 22.3% | 62.3% |
| 5 | tiny_app | Add power function to calculator | 5 | 1,533 | 845 | 169.0 | 44.9% | 45.8% | 50.8% |
| 6 | tiny_app | Improve CLI help and usage | 5 | 1,533 | 932 | 186.4 | 39.2% | 40.2% | 55.7% |
| 7 | tiny_app | Add memory store plugin | 6 | 1,533 | 1,067 | 177.8 | 30.4% | 31.5% | 37.7% |
| 8 | tiny_app | Secure calculator input validation | 6 | 1,533 | 1,325 | 220.8 | 13.6% | 15.0% | 45.9% |
| 9 | web_api | Add JWT refresh token flow | 7 | 5,904 | 1,241 | 177.3 | 79.0% | 81.1% | 30.4% |
| 10 | web_api | Fix rate limiter bucket refill | 6 | 3,422 | 1,352 | 225.3 | 60.5% | 79.4% | 18.1% |
| 11 | web_api | Add user role permissions | 7 | 5,943 | 1,258 | 179.7 | 78.8% | 80.8% | 26.9% |
| 12 | web_api | Optimize blog post pagination | 6 | 3,591 | 1,261 | 210.2 | 64.9% | 80.8% | 18.7% |
| 13 | web_api | Implement password reset flow | 7 | 4,304 | 1,254 | 179.1 | 70.9% | 80.9% | 23.4% |
| 14 | web_api | Build admin analytics dashboard | 6 | 6,024 | 941 | 156.8 | 84.4% | 85.7% | 23.4% |
| 15 | web_api | Add API versioning support | 6 | 5,208 | 1,418 | 236.3 | 72.8% | 78.4% | 31.6% |
| 16 | web_api | Implement request body validation | 6 | 6,063 | 1,025 | 170.8 | 83.1% | 84.4% | 31.0% |
| 17 | web_api | Add audit logging middleware | 7 | 6,191 | 1,594 | 227.7 | 74.3% | 75.7% | 31.0% |
| 18 | microsvc | Add OAuth2 GitHub provider | 8 | 7,162 | 1,111 | 138.9 | 84.5% | 89.5% | 12.4% |
| 19 | microsvc | Fix billing invoice rounding | 7 | 7,526 | 1,299 | 185.6 | 82.7% | 87.7% | 15.7% |
| 20 | microsvc | Add SMS notification provider | 6 | 7,006 | 1,376 | 229.3 | 80.4% | 87.0% | 11.8% |
| 21 | microsvc | Tune circuit breaker thresholds | 7 | 5,181 | 1,164 | 166.3 | 77.5% | 89.0% | 12.1% |
| 22 | microsvc | Add health check to service discovery | 6 | 5,739 | 982 | 163.7 | 82.9% | 90.7% | 12.1% |
| 23 | microsvc | Implement event bus retry mechanism | 8 | 7,700 | 1,255 | 156.9 | 83.7% | 88.1% | 19.0% |
| 24 | microsvc | Add distributed tracing headers | 7 | 6,409 | 924 | 132.0 | 85.6% | 91.3% | 12.1% |
| 25 | microsvc | Build metrics endpoint for Prometheus | 8 | 5,792 | 1,272 | 159.0 | 78.0% | 88.0% | 11.8% |

**Average: 4,451 relevant raw → 1,168 capsule tot tok, 185.1 tok/turn, 62.6% vs relevant, 67.8% vs all.**

**Overall: 29,189 capsule vs 111,269 relevant raw = 73.8% savings (vs 156,263 all raw = 81.3%).**

---

## Summary Comparison

| Metric | Base (AST only) | Ollama (enriched) |
|--------|:---:|:---:|
| Single-shot avg capsule | 57 tok/case | 206 tok/case |
| Single-shot savings vs relevant raw | **86.3%** | **81.3%** |
| Multi-turn savings vs relevant raw | **87.5%** | **62.6%** |
| Multi-turn overall savings | **91.7%** | **73.8%** |
| Enrichment time | — | ~129s (41 files) |
| Enrichment cost | 0 | 5-18 enriched files/project |

## Key Findings

1. **Realistic baseline (relevant raw)**: When comparing against only the files needed for a query (not the entire project), ctxgraph still saves **86% single-shot, 88% multi-turn** with AST-only summaries.
2. **Ollama enrichment adds value but costs tokens**: Natural-language summaries are 3-4x larger than AST-only capsules, reducing savings from 88% to 63% on multi-turn.
3. **Small projects see less savings**: `tiny_app` (7 files) has lower margin because the relevant files often cover most of the project.
4. **Large projects benefit most**: `microsvc` (22 files, 10K+ raw) sees 96-98% savings even vs relevant raw.

## Running

```bash
python benchmarks/run_benchmarks_v3.py           # base (AST only)
python benchmarks/run_benchmarks_v3.py --ollama   # with Ollama enrichment
```

Both save results to `benchmarks/results/benchmark_results_v3[_ollama].json`.
