"""
Ollama comparison benchmark: with ctxgraph vs without ctxgraph.

Measures:
1. Token usage (with vs without graph context)
2. Answer quality (keyword/reference coverage)
3. Whether graph helps the model locate relevant code

Usage:
    python benchmarks/run_ollama_comparison.py
    python benchmarks/run_ollama_comparison.py --project dataflow
    python benchmarks/run_ollama_comparison.py --retry 5
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ctxgraph.graph.builder import build_graph
from ctxgraph.graph.storage import Storage
from ctxgraph.capsule.renderer import render_capsule

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
PROJECTS_DIR = REPO_ROOT / "benchmarks" / "projects"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5-coder:7b"

QUERIES = {
    "tiny_app": [
        "How does the calculator parse expressions? Which file handles the parsing?",
        "Explain the plugin registration system in this project.",
    ],
    "web_api": [
        "How is JWT authentication implemented? Show the token validation flow.",
        "Explain the middleware pipeline - how do requests get processed?",
    ],
    "microsvc": [
        "How does the circuit breaker pattern work in this project?",
        "What services are available and how do they communicate?",
    ],
    "dataflow": [
        "How does the PipelineBuilder pattern work? Explain the stages and scheduling.",
        "What processors are available and how do you register a new one?",
        "How does the event bus work and how are errors handled?",
    ],
}

QUERY_KEYWORDS = {
    "How does the calculator parse expressions? Which file handles the parsing?": [
        "parse", "expression", "parser", "calculator"
    ],
    "Explain the plugin registration system in this project.": [
        "plugin", "register", "registry"
    ],
    "How is JWT authentication implemented? Show the token validation flow.": [
        "jwt", "token", "auth", "validate"
    ],
    "Explain the middleware pipeline - how do requests get processed?": [
        "middleware", "pipeline", "request"
    ],
    "How does the circuit breaker pattern work in this project?": [
        "circuit", "breaker", "retry", "failure"
    ],
    "What services are available and how do they communicate?": [
        "service", "auth", "billing", "communication"
    ],
    "How does the PipelineBuilder pattern work? Explain the stages and scheduling.": [
        "pipeline", "builder", "stage", "scheduler"
    ],
    "What processors are available and how do you register a new one?": [
        "processor", "registry", "register"
    ],
    "How does the event bus work and how are errors handled?": [
        "event", "bus", "handler", "error"
    ],
}


def count_tokens(text: str) -> int:
    return len(text.split())


def ollama_chat(messages: list[dict], max_retries: int = 3) -> dict:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }).encode("utf-8")

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
            print(f"    Ollama error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return {"error": f"Failed after {max_retries} attempts"}


def query_without_context(question: str) -> dict:
    messages = [
        {"role": "system", "content": "You are a code review assistant. Answer the question based on your training knowledge."},
        {"role": "user", "content": question},
    ]
    start = time.perf_counter()
    result = ollama_chat(messages)
    elapsed = time.perf_counter() - start

    prompt_tokens = count_tokens(messages[0]["content"] + "\n" + messages[1]["content"])
    answer = result.get("message", {}).get("content", "ERROR")
    output_tokens = count_tokens(answer)

    return {
        "answer": answer,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": prompt_tokens + output_tokens,
        "elapsed_seconds": round(elapsed, 2),
        "error": result.get("error"),
    }


def query_with_context(question: str, storage: Storage, project_dir: Path) -> dict:
    capsule = render_capsule(storage, question, max_nodes=20)
    capsule_tokens = count_tokens(capsule)

    messages = [
        {"role": "system", "content": "You are a code review assistant. Below is the relevant codebase context in DSL format, then a question. Use the context to answer accurately."},
        {"role": "user", "content": f"[CONTEXT]\n{capsule}\n[/CONTEXT]\n\n{question}"},
    ]
    start = time.perf_counter()
    result = ollama_chat(messages)
    elapsed = time.perf_counter() - start

    prompt_tokens = count_tokens(messages[0]["content"] + "\n" + messages[1]["content"])
    answer = result.get("message", {}).get("content", "ERROR")
    output_tokens = count_tokens(answer)

    return {
        "answer": answer,
        "capsule_tokens": capsule_tokens,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": prompt_tokens + output_tokens,
        "elapsed_seconds": round(elapsed, 2),
        "error": result.get("error"),
    }


def score_answer_coverage(answer: str, keywords: list[str]) -> dict:
    answer_lower = answer.lower()
    found = [kw for kw in keywords if kw.lower() in answer_lower]
    return {
        "keywords_found": found,
        "keywords_missed": [k for k in keywords if k.lower() not in answer_lower],
        "coverage_pct": round(len(found) / max(len(keywords), 1) * 100, 1),
    }


def run_comparison(project_name: str, max_retries: int = 3):
    proj_dir = PROJECTS_DIR / project_name
    if not proj_dir.is_dir():
        print(f"  [SKIP] Project not found: {proj_dir}")
        return []

    print(f"\n{'='*60}")
    print(f"  Project: {project_name}")
    print(f"{'='*60}")

    db_path = RESULTS_DIR / f"ollama_bench_{project_name}.db"
    print(f"  Building graph... ", end="", flush=True)
    try:
        stats = build_graph(proj_dir, db_path=db_path)
        print(f"OK ({stats.get('total_nodes', 0)} nodes, {stats.get('total_edges', 0)} edges)")
    except Exception as e:
        print(f"FAIL: {e}")
        return []

    storage = Storage(db_path)
    storage.connect()

    results = []
    queries = QUERIES.get(project_name, ["Describe this project"])

    for q_idx, question in enumerate(queries):
        keywords = QUERY_KEYWORDS.get(question, [])
        print(f"\n  --- Query {q_idx+1}: {question[:60]}...")

        # Without context
        print(f"    Without context... ", end="", flush=True)
        without = query_without_context(question)
        if without.get("error"):
            print(f"FAIL: {without['error']}")
            continue
        print(f"OK ({without['total_tokens']} tok, {without['elapsed_seconds']}s)")
        coverage_without = score_answer_coverage(without["answer"], keywords)
        print(f"      Coverage: {coverage_without['coverage_pct']}% (found: {coverage_without['keywords_found']})")

        # With context
        print(f"    With context... ", end="", flush=True)
        with_ctx = query_with_context(question, storage, proj_dir)
        if with_ctx.get("error"):
            print(f"FAIL: {with_ctx['error']}")
            continue
        print(f"OK ({with_ctx['total_tokens']} tok, {with_ctx['elapsed_seconds']}s)")
        coverage_with = score_answer_coverage(with_ctx["answer"], keywords)
        print(f"      Coverage: {coverage_with['coverage_pct']}% (found: {coverage_with['keywords_found']})")

        # Token comparison
        savings = without["prompt_tokens"] - with_ctx["prompt_tokens"]
        savings_pct = round((1 - with_ctx["prompt_tokens"] / max(without["prompt_tokens"], 1)) * 100, 1)
        print(f"      Prompt tokens: {without['prompt_tokens']} (no ctx) vs {with_ctx['prompt_tokens']} (ctx) = {savings:+.0f} tok ({savings_pct:+.1f}%)")

        results.append({
            "project": project_name,
            "query": question,
            "without_context": {k: v for k, v in without.items() if k != "answer"},
            "without_context_answer_snippet": without["answer"][:200],
            "without_context_coverage": coverage_without,
            "with_context": {k: v for k, v in with_ctx.items() if k != "answer"},
            "with_context_answer_snippet": with_ctx["answer"][:200],
            "with_context_coverage": coverage_with,
            "token_savings_abs": savings,
            "token_savings_pct": savings_pct,
        })

    storage.close()
    return results


def print_summary(all_results: list[dict]):
    print(f"\n{'='*70}")
    print(f"  OLLAMA COMPARISON SUMMARY")
    print(f"{'='*70}")

    coverage_deltas = []
    token_savings = []

    for r in all_results:
        wo_cov = r["without_context_coverage"]["coverage_pct"]
        w_cov = r["with_context_coverage"]["coverage_pct"]
        delta = w_cov - wo_cov
        tok_save = r["token_savings_pct"]
        coverage_deltas.append(delta)
        token_savings.append(tok_save)

        arrow = "+" if delta > 0 else (" " if delta == 0 else "")
        print(f"\n  [{r['project']}] {r['query'][:55]}")
        print(f"    Coverage: {wo_cov}% (no ctx) -> {w_cov}% (ctx) [{arrow}{delta:+.1f}pp]")
        print(f"    Tokens:   {r['without_context']['total_tokens']} (no ctx) vs {r['with_context']['total_tokens']} (ctx) [{r['token_savings_pct']:+.1f}%]")

    if all_results:
        avg_delta = sum(coverage_deltas) / len(coverage_deltas)
        avg_save = sum(token_savings) / len(token_savings)
        print(f"\n  {'='*70}")
        print(f"  AVERAGES:")
        print(f"    Coverage improvement: {avg_delta:+.1f}pp (keyword recall)")
        print(f"    Token change: {avg_save:+.1f}% (prompt)")
        print(f"    Note: Context adds capsule tokens but removes the need for the model to guess code structure")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ollama with/without ctxgraph benchmark")
    parser.add_argument("--project", help="Run only this project")
    parser.add_argument("--retry", type=int, default=3, help="Max retries per Ollama call")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    projects = [args.project] if args.project else ["tiny_app", "web_api", "microsvc", "dataflow"]

    import urllib.request
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            models = json.loads(resp.read().decode("utf-8"))
            available = [m["name"] for m in models.get("models", [])]
            if OLLAMA_MODEL not in available:
                print(f"[WARN] Model '{OLLAMA_MODEL}' not found. Available: {available}")
                print(f"       Run: ollama pull {OLLAMA_MODEL}")
    except Exception as e:
        print(f"[ERROR] Cannot reach Ollama at localhost:11434: {e}")
        print("       Make sure Ollama is running.")
        sys.exit(1)

    all_results = []
    for proj in projects:
        results = run_comparison(proj, max_retries=args.retry)
        all_results.extend(results)

    output_path = RESULTS_DIR / "ollama_comparison_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")

    print_summary(all_results)
