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
from prompts import DIAGNOSIS                # noqa: E402
from prompts.thresholds import THRESHOLDS    # noqa: E402
from prompt_template import (build, discriminators, CLEAN_DISCRIMINATORS,  # noqa: E402
                             FAULT_TYPES)

RESULTS = ROOT / "evaluation" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

# "monolithic" gets the enum and the calibrated thresholds only. "monolithic_shared" also
# gets the diagnosis agent's discriminator block, which isolates staging and tools from the
# domain knowledge the pipeline's prompts accumulated.
CONFIGS = {"monolithic": "",
           "monolithic_shared": discriminators(DIAGNOSIS),
           "monolithic_clean": CLEAN_DISCRIMINATORS}

REQUIRED = ["fault_type", "root_cause", "confidence", "severity",
            "affected_scope", "remediation", "reasoning"]

# The enum must match the pipeline's or the comparison measures vocabulary, not diagnosis.
missing = [f for f in FAULT_TYPES if f not in DIAGNOSIS]
assert not missing, f"fault types absent from the diagnosis prompt: {missing}"


def all_ids() -> list[str]:
    return sorted("-".join(p.name.split("-")[:2]) for p in (ROOT / "scenarios").glob("*.json"))


def load(sid: str) -> dict:
    return json.loads(next((ROOT / "scenarios").glob(f"{sid}-*.json")).read_text())


def run_one(sid: str, config: str, tag: str = "", fresh: bool = False) -> dict:
    out = RESULTS / f"{sid}_{config}{tag}_{MODEL}.json"
    if out.exists() and not fresh:
        return json.loads(out.read_text())

    scenario = load(sid)
    start = time.time()
    try:
        answer = ask_json(build(scenario, THRESHOLDS, CONFIGS[config]), REQUIRED)
        record = {"scenario_id": sid, "config": config + tag, "model": MODEL,
                  "seconds": round(time.time() - start, 1),
                  "result": {
                      # mirrored into the pipeline's key names so one scorer reads both
                      "diagnosis": {"fault_type": answer["fault_type"],
                                    "root_cause": answer["root_cause"],
                                    "confidence": answer["confidence"],
                                    "affected_scope": answer["affected_scope"],
                                    "evidence": answer["reasoning"]},
                      "remediation": {"action": answer["remediation"]},
                      "escalation": {"priority": answer["severity"]},
                      "monolithic": answer},
                  "ground_truth": scenario["ground_truth"]}
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
    ap.add_argument("--config", default="monolithic", choices=sorted(CONFIGS))
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
