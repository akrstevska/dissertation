"""Run scenarios through the pipeline.

  python run.py FD-001
  python run.py all
  python run.py all --workers 5
  python run.py all --fresh
"""
import argparse
import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # before the langchain imports, so LANGSMITH_* is set when tracing starts

import tools  # noqa: E402
from graph import pipeline  # noqa: E402

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "evaluation" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
MODEL = os.getenv("MODEL", "claude-haiku-4-5-20251001")


def all_ids() -> list[str]:
    return sorted(p.name.split("-")[0] + "-" + p.name.split("-")[1]
                  for p in (ROOT / "scenarios").glob("*.json"))


def run_one(sid: str, config: str = "agent", fresh: bool = False) -> dict:
    out = RESULTS / f"{sid}_{config}_{MODEL}.json"
    if out.exists() and not fresh:
        return json.loads(out.read_text())

    scenario = tools.load(sid)
    start = time.time()
    try:
        state = pipeline.invoke({
            "trigger": scenario["trigger"]["type"],
            "trigger_input": scenario["trigger"]["input"],
            "trace": [],
        })
        record = {"scenario_id": sid, "config": config, "model": MODEL,
                  "seconds": round(time.time() - start, 1),
                  "result": state, "ground_truth": scenario["ground_truth"]}
    except Exception as e:
        record = {"scenario_id": sid, "config": config, "model": MODEL,
                  "seconds": round(time.time() - start, 1),
                  "error": str(e), "traceback": traceback.format_exc()}

    out.write_text(json.dumps(record, indent=2))
    return record


def show(r: dict):
    if "error" in r:
        print(f"{r['scenario_id']:10} ERROR  {r['error'][:70]}")
        return
    d = r["result"].get("diagnosis") or {}
    gt = r["ground_truth"]
    hit = "OK " if d.get("fault_type") == gt["fault_type"] else "MISS"
    print(f"{r['scenario_id']:10} {hit}  {r['seconds']:>5}s  "
          f"got={d.get('fault_type','-'):28} want={gt['fault_type']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--config", default="agent")
    a = ap.parse_args()

    ids = all_ids() if a.target == "all" else [a.target]
    t0 = time.time()

    if a.workers > 1 and len(ids) > 1:
        with ThreadPoolExecutor(a.workers) as ex:
            results = list(ex.map(lambda s: run_one(s, a.config, a.fresh), ids))
    else:
        results = [run_one(s, a.config, a.fresh) for s in ids]

    for r in results:
        show(r)

    ok = sum(1 for r in results if "error" not in r
             and (r["result"].get("diagnosis") or {}).get("fault_type")
             == r["ground_truth"]["fault_type"])
    print(f"\n{ok}/{len(results)} correct in {time.time() - t0:.0f}s")
