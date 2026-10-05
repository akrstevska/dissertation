"""Decides the corrective action from the diagnosis. No tools, recommends only."""
import json
from llm import ask_json
from prompts import REMEDIATION

STUB = False

REQUIRED = ["action", "automated", "reason", "instructions", "alternatives_considered"]


def remediation(state):
    if STUB:
        return {"remediation": {
            "action": "no_action", "automated": False, "reason": "stub",
            "instructions": "", "alternatives_considered": []}}

    out = ask_json(
        f"{REMEDIATION}\n\nDiagnosis:\n{json.dumps(state['diagnosis'], indent=2)}",
        REQUIRED)
    return {"remediation": out}
