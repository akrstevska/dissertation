"""Evaluators. Each takes the system's output and the ground truth and returns a score.

Used by LangSmith's evaluate() (inputs, outputs, reference_outputs), and directly on
saved result files:

  python evaluation/evaluators.py evaluation/results/FD-001_agent_gpt-5.6-luna.json
  python evaluation/evaluators.py --judge evaluation/results/DC-002_agent_gpt-5.6-luna.json
"""
import inspect
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
from prompts.thresholds import THRESHOLDS  # noqa: E402

SCENARIOS = Path(__file__).parent.parent / "scenarios"
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


# --- LLM judge ----------------------------------------------------------------
# A different model family from the system under test, so it is not marking its own work.

JUDGE_MODEL = "claude-sonnet-5-5"


class Coverage(BaseModel):
    present: bool = Field(description="true only if the diagnosis states this evidence with the observation behind it")
    quote: str = Field(description="the sentence from the diagnosis that carries it, or empty")
    reason: str = Field(description="one sentence")


class Claim(BaseModel):
    index: int
    supported: bool
    reason: str = Field(description="one sentence; for an unsupported claim, what the data actually shows")


class Claims(BaseModel):
    claims: list[Claim]


COVERAGE_PROMPT = """You are checking a network fault diagnosis for one piece of required evidence.

Required evidence: {item}

What this item means in this case, from the reference reasoning:
{reasoning}

The system's diagnosis:
Root cause: {root_cause}
Evidence:
{evidence}

Does the diagnosis state this evidence, together with the observation or value that shows it?
Reaching the conclusion without the observation behind it does not count. Wording may differ
from the reference; judge the substance."""

CLAIMS_PROMPT = """You are checking whether a network fault diagnosis is supported by its data.

Below is all the data the system had access to, the calibrated thresholds for this network,
and the numbered evidence statements the system gave. For each statement decide:

supported   - every value, event and observation it states is in the data or follows directly
              from it under the thresholds
unsupported - it states a value, event or observation the data does not contain or contradicts

Judge factual support only, not whether the diagnosis is correct. Rounding is fine.

Thresholds:
{thresholds}

Data:
{data}

Evidence statements:
{statements}"""


def _judge(schema):
    return ChatAnthropic(model=JUDGE_MODEL, temperature=0, max_tokens=4000).with_structured_output(schema)


def _bullets(items):
    return "\n".join(f"- {x}" for x in items)


def evidence_coverage(outputs, reference_outputs):
    """Share of required_evidence items the diagnosis actually states. One judge call per item."""
    d = _diag(outputs)
    if not d.get("evidence"):
        return {"key": "evidence_coverage", "score": 0, "comment": "no evidence given"}
    verdicts = []
    for item in reference_outputs["required_evidence"]:
        v = _judge(Coverage).invoke(COVERAGE_PROMPT.format(
            item=item, reasoning=_bullets(reference_outputs["expected_reasoning"]),
            root_cause=d.get("root_cause", ""), evidence=_bullets(d["evidence"])))
        verdicts.append((item, v))
    score = sum(v.present for _, v in verdicts) / len(verdicts)
    comment = "\n".join(f"[{'Y' if v.present else 'N'}] {item}: {v.reason}" for item, v in verdicts)
    return {"key": "evidence_coverage", "score": round(score, 2), "comment": comment}


def unsupported_claims(inputs, outputs, reference_outputs):
    """Evidence statements the scenario data does not support: the hallucination count."""
    evidence = _diag(outputs).get("evidence") or []
    if not evidence:
        return {"key": "unsupported_claims", "score": None, "comment": "no evidence given"}
    scenario = json.loads(next(SCENARIOS.glob(f"{inputs['scenario_id']}-*.json")).read_text())
    data = {k: v for k, v in scenario.items() if k not in ("metadata", "ground_truth")}
    r = _judge(Claims).invoke(CLAIMS_PROMPT.format(
        thresholds=THRESHOLDS, data=json.dumps(data, separators=(",", ":")),
        statements="\n".join(f"{i}. {s}" for i, s in enumerate(evidence))))
    bad = [c for c in r.claims if not c.supported]
    comment = "\n".join(f"#{c.index}: {evidence[c.index][:120]} -- {c.reason}" for c in bad
                        if c.index < len(evidence)) or "all supported"
    return {"key": "unsupported_claims", "score": len(bad), "comment": comment}


JUDGE = [evidence_coverage, unsupported_claims]
ALL = DETERMINISTIC + JUDGE


# --- running on saved result files --------------------------------------------

def ground_truth(sid: str) -> dict:
    """Always the current scenario, never the copy stored in an old result file."""
    path = next(SCENARIOS.glob(f"{sid}-*.json"))
    return json.loads(path.read_text())["ground_truth"]


def score_record(record: dict, evaluators=None) -> list[dict]:
    args = {"inputs": {"scenario_id": record["scenario_id"]},
            "outputs": record.get("result") or {},
            "reference_outputs": ground_truth(record["scenario_id"])}
    rows = []
    for ev in evaluators or DETERMINISTIC:
        r = ev(**{k: args[k] for k in inspect.signature(ev).parameters})
        rows.extend(r["results"] if "results" in r else [r])
    return rows


if __name__ == "__main__":
    judge = "--judge" in sys.argv
    for f in [a for a in sys.argv[1:] if a != "--judge"]:
        rec = json.loads(Path(f).read_text())
        print(f"\n{rec['scenario_id']}  {rec['config']}")
        for r in score_record(rec, ALL if judge else DETERMINISTIC):
            comment = str(r.get("comment", "")).replace("\n", "\n" + " " * 28)
            print(f"  {r['key']:18} {str(r['score']):6} {comment}")
