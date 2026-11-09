"""Judge validation: a fixed sample of 30 judge verdicts to label by hand, then agreement.

  python evaluation/judge_check.py sample    # writes results/final/judge_check.csv
  python evaluation/judge_check.py score     # agreement and Cohen's kappa once author_label is filled

20 evidence_coverage items (10 judged present, 10 absent) and 10 unsupported_claims
statements (5 flagged, 5 from runs judged all supported), spread over the three configs.
"""
import csv
import glob
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "evaluation" / "results" / "final" / "judge_check.csv"
COLS = ["id", "check", "config", "model", "scenario_id", "repetition", "item_or_statement",
        "diagnosis", "judge_label", "judge_reason", "llm_label", "llm_reason",
        "author_label", "author_note"]


def runs():
    for f in sorted(glob.glob(str(ROOT / "evaluation/results/final/*-*-*.csv"))):
        yield from csv.DictReader(open(f))


def sample():
    rng = random.Random(2026)
    cov, flagged, clean = [], [], []
    for r in runs():
        d = json.loads(r["outputs"])["diagnosis"]
        text = "Root cause: " + d.get("root_cause", "") + "\nEvidence:\n" + "\n".join(
            f"{i}. {e}" for i, e in enumerate(d.get("evidence") or []))
        base = {"config": r["config"], "model": r["model"], "scenario_id": r["scenario_id"],
                "repetition": r["repetition"], "diagnosis": text}
        for m in re.finditer(r"^\[(Y|N)\] (\S+): (.*)$", r["evidence_coverage_comment"], re.M):
            cov.append(base | {"check": "evidence_coverage", "item_or_statement": m.group(2),
                               "judge_label": "present" if m.group(1) == "Y" else "absent",
                               "judge_reason": m.group(3)})
        c = r["unsupported_claims_comment"]
        if c == "all supported" and d.get("evidence"):
            i = rng.randrange(len(d["evidence"]))
            clean.append(base | {"check": "unsupported_claims", "item_or_statement": f"#{i}: {d['evidence'][i]}",
                                 "judge_label": "supported", "judge_reason": "all supported"})
        for m in re.finditer(r"^#(\d+): .*? -- (.*)$", c, re.M):
            i = int(m.group(1))
            flagged.append(base | {"check": "unsupported_claims", "item_or_statement": f"#{i}: {d['evidence'][i]}",
                                   "judge_label": "unsupported", "judge_reason": m.group(2)})

    def pick(pool, n):
        # spread over the three configs
        by = {}
        for x in pool:
            by.setdefault(x["config"], []).append(x)
        out = []
        while len(out) < n:
            for k in sorted(by):
                if by[k] and len(out) < n:
                    out.append(by[k].pop(rng.randrange(len(by[k]))))
        return out

    chosen = (pick([x for x in cov if x["judge_label"] == "present"], 10) +
              pick([x for x in cov if x["judge_label"] == "absent"], 10) +
              pick(flagged, 5) + pick(clean, 5))
    rng.shuffle(chosen)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for k, x in enumerate(chosen, 1):
            w.writerow({c: x.get(c, "") for c in COLS} | {"id": k})
    print(f"{len(chosen)} verdicts -> {OUT}")


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def score(col="author_label"):
    rows = [r for r in csv.DictReader(open(OUT)) if r[col]]
    for check in ("evidence_coverage", "unsupported_claims", None):
        sub = [r for r in rows if check is None or r["check"] == check]
        # pooled over both checks: credit (present/supported) vs no credit
        ok = lambda v: v if check else v in ("present", "supported")
        po, k = kappa([ok(r["judge_label"]) for r in sub], [ok(r[col]) for r in sub])
        print(f"{check or 'all':20} n={len(sub):2}  agreement={po:.0%}  kappa={k:.2f}")
    for r in rows:
        if r["judge_label"] != r[col]:
            print(f"  disagree #{r['id']} {r['check']} {r['scenario_id']}: judge={r['judge_label']} {col}={r[col]}")


if __name__ == "__main__":
    {"sample": sample, "score": lambda: score(sys.argv[2] if len(sys.argv) > 2 else "author_label")}[sys.argv[1]]()
