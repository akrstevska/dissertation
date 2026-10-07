"""Run one architecture over the LangSmith dataset as an experiment, scored by the evaluators.

  python evaluation/run_experiment.py                                  # agent, smoke split
  python evaluation/run_experiment.py --config monolithic_shared_stored
  MODEL=gpt-6-luna python evaluation/run_experiment.py --split base --repeat 3
  python evaluation/run_experiment.py --add-judge <experiment name>    # judge one run per scenario
  python evaluation/run_experiment.py --add-judge <experiment name> --judge-repeats 3  # top up

LangSmith records tokens, cost and latency per run; the evaluators add the score columns.
"""
import argparse
import inspect
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
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
    """Only the agents' decisions; the full run, tool calls included, is in the trace."""
    tools.load(inputs["scenario_id"])
    state = pipeline.invoke({"trigger": inputs["trigger"],
                             "trigger_input": inputs["trigger_input"], "trace": []})
    out = {k: state.get(k) for k in ("diagnosis", "remediation", "escalation", "detection")}
    if out["remediation"] is None:
        # routing.after_diagnosis skipped the remediation agent; that route is itself the
        # decision: low confidence goes to a human, olt/router scope to infrastructure
        low = out["diagnosis"]["confidence"] < 0.5
        out["remediation"] = {"action": "manual_review" if low else "escalate_infrastructure",
                              "routed": True}
    return out


def baseline(config: str):
    def target(inputs: dict) -> dict:
        return monolithic.diagnose(monolithic.load(inputs["scenario_id"]), config)
    return target


def add_judge(client, experiment: str, repeats: int, workers: int):
    """Judge the first `repeats` repetitions of each scenario and attach the scores as feedback.
    A judge key a run already has is skipped, so a top-up never judges or pays twice."""
    per_example = {}
    for r in sorted(client.list_runs(project_name=experiment, is_root=True), key=lambda r: r.start_time):
        per_example.setdefault(r.reference_example_id, []).append(r)
    runs = [r for reps in per_example.values() for r in reps[:repeats]]
    done = {}
    for f in client.list_feedback(run_ids=[r.id for r in runs], feedback_key=[ev.__name__ for ev in JUDGE]):
        done.setdefault(f.run_id, set()).add(f.key)
    examples = {e.id: e for e in client.list_examples(dataset_name=DATASET)}

    def judge(run):
        todo = [ev for ev in JUDGE if ev.__name__ not in done.get(run.id, set())]
        if not todo:
            return 0
        ex = examples[run.reference_example_id]
        args = {"inputs": ex.inputs, "outputs": run.outputs or {}, "reference_outputs": ex.outputs}
        for ev in todo:
            r = ev(**{k: args[k] for k in inspect.signature(ev).parameters})
            client.create_feedback(run.id, key=r["key"], score=r["score"], comment=r.get("comment"))
        print(ex.inputs["scenario_id"], "judged")
        return 1

    with ThreadPoolExecutor(workers) as ex:
        judged = sum(ex.map(judge, runs))
    print(f"\n{experiment}: judged {judged} runs, {len(runs) - judged} already judged")


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
    ap.add_argument("--judge-repeats", type=int, default=1, metavar="N",
                    help="with --add-judge: judge the first N repetitions per scenario")
    a = ap.parse_args()
    client = Client()

    if a.add_judge:
        add_judge(client, a.add_judge, a.judge_repeats, a.workers)
        sys.exit()
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
