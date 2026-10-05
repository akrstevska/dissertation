"""Conditional edges. Decides where the pipeline goes after each agent.

Detection no longer ends the pipeline: a cleared trigger still has to be written down
as a no_fault diagnosis, so detection always flows into diagnosis.
"""


def after_diagnosis(state) -> str:
    d = state["diagnosis"]
    if d["confidence"] < 0.5:
        return "escalation"
    if d["affected_scope"] in ("olt", "router"):
        return "escalation"
    return "remediation"
