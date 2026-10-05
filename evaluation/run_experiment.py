"""Run one architecture over the LangSmith dataset as an experiment, scored by the evaluators.

  python evaluation/run_experiment.py                                  # agent, smoke split
  python evaluation/run_experiment.py --config monolithic_shared
  python evaluation/run_experiment.py --split base --repeat 3 --judge
  python evaluation/run_experiment.py --add-judge <experiment name>    # judge an existing run

LangSmith records tokens, cost and latency per run; the evaluators add the score columns.
"""
import argparse
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # before the langchain imports, so LANGSMITH_* is set when tracing starts

ROOT = Path(__file__).parent.parent
sys.path[:0] = [str(ROOT / "pipeline"), str(ROOT / "baseline")]

from langsmith import Client  # noqa: E402

import tools  # noqa: E402
from graph import pipeline  # noqa: E402
from llm import MODEL  # noqa: E402
import monolithic  # noqa: E402
from dataset import DATASET  # noqa: E402
from evaluators import DETERMINISTIC, JUDGE, JUDGE_MODEL  # noqa: E402

CONFIGS = ["agent"] + list(monolithic.CONFIGS)


def agent(inputs: dict) -> dict:
    tools.load(inputs["scenario_id"])
    return pipeline.invoke({"trigger": inputs["trigger"],
                            "trigger_input": inputs["trigger_input"], "trace": []})


def baseline(config: str):
    def target(inputs: dict) -> dict:
        return monolithic.diagnose(monolithic.load(inputs["scenario_id"]), config)
    return target


def summary(results):
    scores = {}
    for r in results:
        for e in r["evaluation_results"]["results"]:
            if isinstance(e.score, (int, float)):
                scores.setdefault(e.key, []).append(e.score)
    for key, vals in scores.items():
        print(f"  {key:18} mean {sum(vals) / len(vals):6.2f}   n={len(vals)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="agent", choices=CONFIGS)
    ap.add_argument("--split", default="smoke")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--judge", action="store_true", help="add the LLM judge evaluators")
    ap.add_argument("--add-judge", metavar="EXPERIMENT", help="judge an existing experiment, no re-run")
    a = ap.parse_args()
    client = Client()

    if a.add_judge:
        results = client.evaluate(a.add_judge, evaluators=JUDGE, max_concurrency=a.workers)
    else:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
        results = client.evaluate(
            agent if a.config == "agent" else baseline(a.config),
            data=client.list_examples(dataset_name=DATASET, splits=[a.split]),
            evaluators=DETERMINISTIC + (JUDGE if a.judge else []),
            experiment_prefix=f"{a.config}-{MODEL}",
            metadata={"config": a.config, "model": MODEL, "split": a.split, "commit": commit,
                      "judge_model": JUDGE_MODEL if a.judge else None},
            num_repetitions=a.repeat,
            max_concurrency=a.workers,
        )
    print(f"\n{results.experiment_name}")
    summary(results)
