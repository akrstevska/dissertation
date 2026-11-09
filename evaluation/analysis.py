"""Results from the exported experiments (evaluation/results/final/*.csv), using the
definitions frozen in docs/hypotheses.md. No API calls.

  python evaluation/analysis.py

Case correct = fault_type, remediation and priority all correct. Paired comparisons are per
scenario: a scenario's score is its mean over repetitions. McNemar uses the per-scenario
majority (correct in at least half the repetitions); the bootstrap resamples scenarios.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

FINAL = Path(__file__).parent / "results" / "final"
MODELS = ["gpt-5.6-luna", "gpt-6-luna", "gpt-5.4-nano"]
CONFIGS = ["agent", "monolithic_stored", "monolithic_shared_stored"]
FIELDS = ["fault_type", "remediation", "priority", "category", "human_review", "scope",
          "service_impact", "customer_count", "detection"]
LIVE = {"DS-001", "DS-002", "FC-001", "FC-002", "FC-004", "FD-002",
        "OO-001", "OO-002", "OO-003", "PP-003", "SV-001", "SV-002"}  # docs/hypotheses.md
REWRITTEN = {"SF-002", "RA-003", "RA-004", "OF-001", "OF-002", "RU-001"}  # engineer review


def num(x):
    return float(x) if x not in ("", None) else None


def load():
    runs = defaultdict(list)  # (model, config) -> rows
    for f in FINAL.glob("*-gpt-*.csv"):  # experiment exports only, not summary_table.csv
        for r in csv.DictReader(f.open()):
            out = json.loads(r["outputs"] or "{}")
            r["got_fault"] = (out.get("diagnosis") or {}).get("fault_type")
            r["got_action"] = (out.get("remediation") or {}).get("action")
            r["case"] = float(all(num(r[k]) == 1 for k in ("fault_type", "remediation", "priority")))
            runs[(r["model"], r["config"])].append(r)
    return runs


def per_scenario(rows, key="case"):
    s = defaultdict(list)
    for r in rows:
        if num(r[key]) is not None:
            s[r["scenario_id"]].append(num(r[key]))
    return {k: sum(v) / len(v) for k, v in s.items()}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def mcnemar(a, b):
    """Exact two-sided McNemar on per-scenario majority correct."""
    ids = sorted(set(a) & set(b))
    only_a = sum(1 for i in ids if a[i] >= 0.5 > b[i])
    only_b = sum(1 for i in ids if b[i] >= 0.5 > a[i])
    n = only_a + only_b
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(only_a, only_b) + 1)) / 2 ** n) if n else 1.0
    return only_a, only_b, p


def bootstrap(a, b, ids, n=10000, seed=0):
    ids = sorted(ids)
    d = np.array([a[i] - b[i] for i in ids])
    rng = np.random.default_rng(seed)
    boots = d[rng.integers(0, len(d), (n, len(d)))].mean(axis=1)
    return d.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5)


def consistency(rows):
    """Share of scenarios whose fault_type and action are identical in every repetition."""
    s = defaultdict(set)
    for r in rows:
        s[r["scenario_id"]].add((r["got_fault"], r["got_action"]))
    return sum(1 for v in s.values() if len(v) == 1) / len(s)


def compare(runs, model, a_cfg, b_cfg, subset=None):
    a, b = per_scenario(runs[(model, a_cfg)]), per_scenario(runs[(model, b_cfg)])
    ids = set(a) & set(b) if subset is None else set(a) & set(b) & subset
    diff, lo, hi = bootstrap(a, b, ids)
    oa, ob, p = mcnemar({i: a[i] for i in ids}, {i: b[i] for i in ids})
    verdict = "supported" if lo > 0 or hi < 0 else "direction only"
    return f"{diff:+.2f} [{lo:+.2f}, {hi:+.2f}]  wins {oa}-{ob}  McNemar p={p:.3f}  ({verdict})"


if __name__ == "__main__":
    runs = load()
    rows_out = []

    print("== Main table (mean over all runs) ==")
    head = ["model", "config", "runs", "case"] + FIELDS + ["evidence", "unsupported", "consistency",
                                                            "tokens", "cost_usd", "seconds"]
    print("  ".join(h[:8].rjust(8) for h in head))
    for m in MODELS:
        for c in CONFIGS:
            rows = runs[(m, c)]
            reps = len({r["repetition"] for r in rows})
            row = [m, c, len(rows), mean(r["case"] for r in rows)] + \
                  [mean(num(r[f]) for r in rows) for f in FIELDS] + \
                  [mean(num(r["evidence_coverage"]) for r in rows),
                   mean(num(r["unsupported_claims"]) for r in rows),
                   consistency(rows) if reps > 1 else float("nan"),
                   mean(num(r["total_tokens"]) for r in rows),
                   mean(num(r["cost"]) for r in rows),
                   mean(num(r["seconds"]) for r in rows)]
            rows_out.append(row)
            print("  ".join(str(x)[:8].rjust(8) if isinstance(x, str) else
                            ("     nan" if x != x else f"{x:8.3f}" if x < 100 else f"{x:8.0f}") if not isinstance(x, int)
                            else f"{x:8d}" for x in row))

    with (FINAL / "summary_table.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows_out)

    print("\n== Paired comparisons on case correct (diff = agent - monolith, 95% bootstrap CI) ==")
    for m in MODELS:
        for c in CONFIGS[1:]:
            print(f"{m:14} agent vs {c:26} {compare(runs, m, 'agent', c)}")

    print("\n== H1: by difficulty (luna, agent vs monolithic_stored) ==")
    diff_of = {r["scenario_id"]: r["difficulty"] for r in runs[("gpt-5.6-luna", "agent")]}
    for d in ("easy", "medium", "hard"):
        ids = {s for s, v in diff_of.items() if v == d}
        print(f"  {d:7} n={len(ids):2}  {compare(runs, 'gpt-5.6-luna', 'agent', 'monolithic_stored', ids)}")

    print("\n== H2: live-verification scenarios vs the rest (agent vs monolithic_shared_stored) ==")
    all_ids = set(diff_of)
    for m in MODELS:
        print(f"  {m:14} live  n=12  {compare(runs, m, 'agent', 'monolithic_shared_stored', LIVE)}")
        print(f"  {m:14} other n=23  {compare(runs, m, 'agent', 'monolithic_shared_stored', all_ids - LIVE)}")

    print("\n== Engineer-rewritten scenarios (partial held-out), case correct ==")
    for m in MODELS:
        print(f"  {m:14} " + "  ".join(
            f"{c}={mean(r['case'] for r in runs[(m, c)] if r['scenario_id'] in REWRITTEN):.2f}" for c in CONFIGS))
