"""Copy the final experiments out of LangSmith into CSVs, one row per run.

  python evaluation/export.py

Writes evaluation/results/final/<experiment>.csv: outputs, every score and judge comment,
tokens, cost, latency, and for the agent the sequence of tool calls (traces may expire).
"""
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))
from langsmith import Client  # noqa: E402
from langsmith.utils import LangSmithRateLimitError  # noqa: E402

from dataset import DATASET  # noqa: E402

OUT = Path(__file__).parent / "results" / "final"


def export(client, project, examples):
    runs = sorted(client.list_runs(project_name=project.name, is_root=True), key=lambda r: r.start_time)
    agent = (project.extra or {}).get("metadata", {}).get("config") == "agent"

    def fetch(r):
        # one request per run: a bulk feedback query over many runs silently skipped some rows
        for wait in (0, 15, 30, 60, 120):  # LangSmith caps API requests per minute
            time.sleep(wait)
            try:
                fb = {f.key: f for f in client.list_feedback(run_ids=[r.id])}
                tools = sorted(client.list_runs(project_name=project.name, trace_id=r.trace_id,
                                                run_type="tool"), key=lambda t: t.start_time) if agent else []
                return fb, [t.name for t in tools]
            except LangSmithRateLimitError:
                pass
        raise RuntimeError(f"rate limited on run {r.id}")

    with ThreadPoolExecutor(3) as pool:
        fetched = dict(zip([r.id for r in runs], pool.map(fetch, runs)))
    meta = (project.extra or {}).get("metadata", {})
    seen, rows = {}, []
    for r in runs:
        ex = examples[r.reference_example_id]
        seen[ex.id] = seen.get(ex.id, 0) + 1
        row = {"experiment": project.name, "config": meta.get("config"), "model": meta.get("model"),
               "commit": meta.get("commit"), "scenario_id": ex.inputs["scenario_id"],
               "difficulty": ex.metadata.get("difficulty"), "repetition": seen[ex.id],
               "run_id": str(r.id), "error": r.error or "",
               "seconds": round((r.end_time - r.start_time).total_seconds(), 1),
               "total_tokens": r.total_tokens, "cost": r.total_cost,
               "outputs": json.dumps(r.outputs or {})}
        feedback, tools = fetched[r.id]
        for key, f in feedback.items():
            row[key] = f.score
            if f.comment and key in ("evidence_coverage", "unsupported_claims"):
                row[f"{key}_comment"] = f.comment
        if agent:
            row["tool_calls"] = json.dumps(tools)
        rows.append(row)
    cols = list(dict.fromkeys(k for row in rows for k in row))
    with open(OUT / f"{project.name}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"{project.name}: {len(rows)} runs")


if __name__ == "__main__":
    client = Client()
    OUT.mkdir(parents=True, exist_ok=True)
    ds = client.read_dataset(dataset_name=DATASET)
    examples = {e.id: e for e in client.list_examples(dataset_id=ds.id)}
    for p in client.list_projects(reference_dataset_id=ds.id):
        if (p.extra or {}).get("metadata", {}).get("split") == "base":
            export(client, p, examples)
