"""Evaluators. Each takes the system's output and the ground truth and returns a score.

Used by LangSmith's evaluate() (outputs, reference_outputs), and directly on saved
result files:

  python evaluation/evaluators.py evaluation/results/FD-001_agent_gpt-5.6-luna.json
"""
import json
import sys
from pathlib import Path

ZABBIX = ["Not classified", "Information", "Warning", "Average", "High", "Disaster"]


def _diag(o):
    return o.get("diagnosis") or {}


def _esc(o):
    return o.get("escalation") or {}


def _match(key, got, want):
    return {"key": key, "score": int(got == want), "comment": f"got={got} want={want}"}


# --- deterministic ----------------------------------------------------------

def fault_type(outputs, reference_outputs):
    return _match("fault_type", _diag(outputs).get("fault_type"), reference_outputs["fault_type"])


def remediation(outputs, reference_outputs):
    got = (outputs.get("remediation") or {}).get("action")
    return _match("remediation", got, reference_outputs["expected_remediation"])


def priority(outputs, reference_outputs):
    return _match("priority", _esc(outputs).get("priority"),
                  reference_outputs["expected_escalation"]["priority"])


def priority_distance(outputs, reference_outputs):
    """Levels off on the Zabbix scale: + over-escalated, - under-escalated."""
    got, want = _esc(outputs).get("priority"), reference_outputs["expected_escalation"]["priority"]
    if got not in ZABBIX:
        return {"key": "priority_distance", "score": None, "comment": f"no valid priority: {got}"}
    return {"key": "priority_distance", "score": ZABBIX.index(got) - ZABBIX.index(want),
            "comment": f"got={got} want={want}"}


def category(outputs, reference_outputs):
    return _match("category", _esc(outputs).get("category"),
                  reference_outputs["expected_escalation"]["category"])


def human_review(outputs, reference_outputs):
    return _match("human_review", _esc(outputs).get("requires_human_review"),
                  reference_outputs["expected_escalation"]["requires_human_review"])


def scope(outputs, reference_outputs):
    gt = reference_outputs
    return {"results": [
        _match("scope", _diag(outputs).get("affected_scope"), gt["affected_scope"]),
        _match("service_impact", _esc(outputs).get("service_impact"), gt["service_impact"]),
        _match("customer_count", _esc(outputs).get("affected_customer_count"), gt["affected_customer_count"]),
    ]}


def confidence(outputs, reference_outputs):
    """Recorded, not judged: compared against correctness in analysis."""
    return {"key": "confidence", "score": _diag(outputs).get("confidence")}


DETERMINISTIC = [fault_type, remediation, priority, priority_distance, category,
                 human_review, scope, confidence]


# --- running on saved result files --------------------------------------------

def ground_truth(sid: str) -> dict:
    """Always the current scenario, never the copy stored in an old result file."""
    path = next((Path(__file__).parent.parent / "scenarios").glob(f"{sid}-*.json"))
    return json.loads(path.read_text())["ground_truth"]


def score_record(record: dict, evaluators=None) -> list[dict]:
    outputs, gt = record.get("result") or {}, ground_truth(record["scenario_id"])
    rows = []
    for ev in evaluators or DETERMINISTIC:
        r = ev(outputs, gt)
        rows.extend(r["results"] if "results" in r else [r])
    return rows


if __name__ == "__main__":
    for f in sys.argv[1:]:
        rec = json.loads(Path(f).read_text())
        print(f"\n{rec['scenario_id']}  {rec['config']}")
        for r in score_record(rec):
            print(f"  {r['key']:18} {str(r['score']):6} {r.get('comment', '')}")
