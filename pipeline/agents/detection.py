"""Screens stored state for anomalies. Stops the pipeline if nothing is wrong."""
import tools
from llm import run_agent
from prompts import DETECTION
from .common import trigger_text, with_trace

STUB = False

REQUIRED = ["status", "signals", "preliminary_severity", "affected_scope",
            "affected_lineids", "summary"]


def detection(state):
    if STUB:
        return {"detection": {
            "status": "anomaly_detected", "signals": [], "preliminary_severity": "Warning",
            "affected_scope": "single_customer",
            "affected_lineids": [state["trigger_input"].get("lineid", "")],
            "olt_id": None, "interface": None, "summary": "stub"}}

    out, trace = run_agent(DETECTION, trigger_text(state),
                           tools.DETECTION_TOOLS, REQUIRED, max_calls=8)
    out.setdefault("olt_id", None)
    out.setdefault("interface", None)
    return {"detection": out, "trace": with_trace(state, trace)}
