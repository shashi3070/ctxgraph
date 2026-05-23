"""Compare base (v3) vs Ollama-enriched (v3_ollama) results and print table."""
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"

with open(RESULTS_DIR / "benchmark_results_v3.json") as f:
    base = json.load(f)
with open(RESULTS_DIR / "benchmark_results_v3_ollama.json") as f:
    ollama = json.load(f)

print("=" * 75)
print("  WITH vs WITHOUT OLLAMA — 50 CASE COMPARISON")
print("=" * 75)

# Single-shot comparison
print(f"\n  SINGLE-SHOT (25 cases):")
print(f"  {'Project':<12} {'Base Tok':<10} {'Ollama Tok':<12} {'Diff':<8} {'Base Sav%':<10} {'Ollama Sav%':<12}")
print(f"  {'-'*12} {'-'*10} {'-'*12} {'-'*8} {'-'*10} {'-'*12}")
for proj in ["tiny_app", "web_api", "microsvc"]:
    b = [r for r in base["single_shot"] if r["project"] == proj]
    o = [r for r in ollama["single_shot"] if r["project"] == proj]
    if b and o:
        b_avg = round(sum(r["capsule_tokens"] for r in b) / len(b), 1)
        o_avg = round(sum(r["capsule_tokens"] for r in o) / len(o), 1)
        b_sav = round(sum(r["savings_pct"] for r in b) / len(b), 1)
        o_sav = round(sum(r["savings_pct"] for r in o) / len(o), 1)
        diff = round(o_avg - b_avg, 1)
        print(f"  {proj:<12} {b_avg:<10} {o_avg:<12} +{diff:<6} {b_sav:<8}% {o_sav:<10}%")

# Multi-turn comparison
print(f"\n  MULTI-TURN (25 scenarios):")
print(f"  {'Project':<12} {'Base TotTok':<12} {'Ollama TotTok':<14} {'Diff':<10} {'Base Sav%':<10} {'Ollama Sav%':<12}")
print(f"  {'-'*12} {'-'*12} {'-'*14} {'-'*10} {'-'*10} {'-'*12}")
for proj in ["tiny_app", "web_api", "microsvc"]:
    b = [r for r in base["multi_turn"] if r["project"] == proj]
    o = [r for r in ollama["multi_turn"] if r["project"] == proj]
    if b and o:
        b_tot = round(sum(r["cumulative_capsule_tokens"] for r in b) / len(b), 1)
        o_tot = round(sum(r["cumulative_capsule_tokens"] for r in o) / len(o), 1)
        b_sav = round(sum(r["savings_vs_raw_pct"] for r in b) / len(b), 1)
        o_sav = round(sum(r["savings_vs_raw_pct"] for r in o) / len(o), 1)
        diff = round(o_tot - b_tot, 1)
        print(f"  {proj:<12} {b_tot:<12} {o_tot:<14} +{diff:<8} {b_sav:<8}% {o_sav:<10}%")
    o_time = o[0].get("ollama_time_s", 0) if o else 0
    o_pf = o[0].get("ollama_time_per_file_s", 0) if o else 0
    print(f"  {'':12} Ollama enrichment: {o_time}s ({o_pf}s/file)")

# Overall
print()
b_all_ss = sum(r["capsule_tokens"] for r in base["single_shot"])
o_all_ss = sum(r["capsule_tokens"] for r in ollama["single_shot"])
b_all_mt = sum(r["cumulative_capsule_tokens"] for r in base["multi_turn"])
o_all_mt = sum(r["cumulative_capsule_tokens"] for r in ollama["multi_turn"])
pct_ss = round((o_all_ss - b_all_ss) / max(b_all_ss, 1) * 100, 1)
pct_mt = round((o_all_mt - b_all_mt) / max(b_all_mt, 1) * 100, 1)

print(f"  {'='*60}")
print(f"  OVERALL (50 cases):")
print(f"    Single-shot: Base={b_all_ss} tok  Ollama={o_all_ss} tok  +{pct_ss}%")
print(f"    Multi-turn:  Base={b_all_mt} tok  Ollama={o_all_mt} tok  +{pct_mt}%")
print(f"    Ollama overhead: ~195s total for 41 files (~4.8s/file)")
print(f"  {'='*60}")
