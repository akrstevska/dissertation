"""Monolithic baseline: all scenario data in one prompt, one LLM call, no tools.

The control group for the pipeline.

  python monolithic.py FD-001
  python monolithic.py all --workers 4
  python monolithic.py all --workers 4 --repeat 3
"""
import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from llm import ask_json, MODEL              # noqa: E402
from prompts import DETECTION, DIAGNOSIS, REMEDIATION, ESCALATION  # noqa: E402
from prompts.remediation_prompt import ACTIONS          # noqa: E402
from prompts.thresholds import THRESHOLDS    # noqa: E402
from prompt_template import (build, between, discriminators,  # noqa: E402
                             FAULT_TYPES, CATEGORIES, STORED_SECTIONS)

RESULTS = ROOT / "evaluation" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

# Everything the pipeline's agents know, sliced from their live prompts so it cannot drift:
# detection's reading and screening rules (its tool-order instructions excluded), the
# diagnosis discriminators and closing rules, and the remediation and escalation rules.
SHARED = "\n\n".join([
    "Reading and screening rules:\n" + between(DETECTION, "- Read every number", "Give preliminary_severity"),
    discriminators(DIAGNOSIS),
    between(DIAGNOSIS, "Verify before you conclude.", "fault_type must be exactly"),
    "Remediation rules:\n" + between(REMEDIATION, "- ONU offline", "action must be exactly"),
    "Escalation rules:\n" + between(ESCALATION, "Priority:", "Reply with JSON only"),
])

# config -> (domain knowledge, data sections). Both get the thresholds and the closed
# lists, and only stored data: live probes are what only an agent that acts can collect.
# monolithic_stored is a single general prompt; monolithic_shared_stored also carries every
# rule the agents have, which separates the architecture from the knowledge.
CONFIGS = {"monolithic_stored": ("", STORED_SECTIONS),
           "monolithic_shared_stored": (SHARED, STORED_SECTIONS)}

REQUIRED = ["fault_type", "root_cause", "confidence", "affected_scope", "action", "priority",
            "category", "requires_human_review", "review_reason", "affected_customer_count",
            "service_impact", "reasoning"]

# The vocabularies must match the pipeline's or the comparison measures wording, not diagnosis.
missing = [f for f in FAULT_TYPES if f not in DIAGNOSIS] + [c for c in CATEGORIES if c not in ESCALATION]
assert not missing, f"vocabulary absent from the pipeline prompts: {missing}"


def all_ids() -> list[str]:
    return sorted("-".join(p.name.split("-")[:2]) for p in (ROOT / "scenarios").glob("*.json"))


def load(sid: str) -> dict:
    return json.loads(next((ROOT / "scenarios").glob(f"{sid}-*.json")).read_text())


def diagnose(scenario: dict, config: str) -> dict:
    knowledge, sections = CONFIGS[config]
    a = ask_json(build(scenario, THRESHOLDS, ACTIONS, knowledge, sections), REQUIRED)
    # mirrored into the pipeline's key names so one scorer reads both
    return {"diagnosis": {k: a[k] for k in ("fault_type", "root_cause", "confidence", "affected_scope")}
                         | {"evidence": a["reasoning"]},
            "remediation": {"action": a["action"]},
            "escalation": {k: a[k] for k in ("priority", "category", "requires_human_review",
                                             "review_reason", "affected_customer_count",
                                             "service_impact")},
            "monolithic": a}


def run_one(sid: str, config: str, tag: str = "", fresh: bool = False) -> dict:
    out = RESULTS / f"{sid}_{config}{tag}_{MODEL}.json"
    if out.exists() and not fresh:
        return json.loads(out.read_text())

    scenario = load(sid)
    start = time.time()
    try:
        result = diagnose(scenario, config)
        record = {"scenario_id": sid, "config": config + tag, "model": MODEL,
                  "seconds": round(time.time() - start, 1),
                  "result": result, "ground_truth": scenario["ground_truth"]}
    except Exception as e:
        record = {"scenario_id": sid, "config": config + tag, "model": MODEL,
                  "seconds": round(time.time() - start, 1),
                  "error": str(e), "traceback": traceback.format_exc()}

    out.write_text(json.dumps(record, indent=2))
    return record


def show(r: dict):
    if "error" in r:
        print(f"{r['scenario_id']:10} ERROR  {r['error'][:70]}")
        return
    got = r["result"]["diagnosis"]["fault_type"]
    want = r["ground_truth"]["fault_type"]
    print(f"{r['scenario_id']:10} {'OK ' if got == want else 'MISS'}  {r['seconds']:>5}s  "
          f"got={got:28} want={want}")


def one_pass(ids: list[str], config: str, workers: int, tag: str, fresh: bool) -> list[dict]:
    if workers > 1 and len(ids) > 1:
        with ThreadPoolExecutor(workers) as ex:
            return list(ex.map(lambda s: run_one(s, config, tag, fresh), ids))
    return [run_one(s, config, tag, fresh) for s in ids]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--repeat", type=int, default=1,
                    help="passes to run; results are tagged _p1, _p2, ... when above 1")
    ap.add_argument("--config", default="monolithic_stored", choices=sorted(CONFIGS))
    a = ap.parse_args()

    ids = all_ids() if a.target == "all" else [a.target]

    for p in range(1, a.repeat + 1):
        tag = f"_p{p}" if a.repeat > 1 else ""
        t0 = time.time()
        results = one_pass(ids, a.config, a.workers, tag, a.fresh)
        for r in results:
            show(r)
        ok = sum(1 for r in results if "error" not in r
                 and r["result"]["diagnosis"]["fault_type"] == r["ground_truth"]["fault_type"])
        print(f"\npass {p}: {ok}/{len(results)} correct in {time.time() - t0:.0f}s\n")
