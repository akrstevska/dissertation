"""Produces the incident record from accumulated state. No tools."""
import json
from llm import ask_json
from prompts import ESCALATION

STUB = False

REQUIRED = ["priority", "category", "requires_human_review", "summary",
            "affected_customer_count", "service_impact"]


def escalation(state):
    if STUB:
        return {"escalation": {
            "priority": "Warning", "category": "monitoring",
            "requires_human_review": False, "review_reason": None,
            "summary": "stub", "affected_customer_count": 0, "service_impact": False}}

    payload = {k: state.get(k) for k in ("detection", "diagnosis", "remediation")}
    out = ask_json(f"{ESCALATION}\n\nPipeline output:\n{json.dumps(payload, indent=2)}",
                   REQUIRED)
    out.setdefault("review_reason", None)
    return {"escalation": out}
