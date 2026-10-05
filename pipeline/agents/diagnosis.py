"""Verifies stored state against live probes and telemetry. Owns the hard reasoning."""
import json
import tools
from llm import run_agent
from prompts import DIAGNOSIS
from .common import trigger_text, with_trace

STUB = False

REQUIRED = ["fault_type", "root_cause", "confidence", "affected_scope",
            "affected_lineids", "evidence"]


def diagnosis(state):
    if STUB:
        return {"diagnosis": {
            "fault_type": "no_fault", "root_cause": "stub", "confidence": 0.5,
            "affected_scope": "single_customer", "affected_lineids": [],
            "evidence": [], "cached_vs_live_discrepancy": False,
            "discrepancy_detail": None}}

    task = (f"{trigger_text(state)}\n\n"
            f"Detection findings:\n{json.dumps(state['detection'], indent=2)}")
    out, trace = run_agent(DIAGNOSIS, task, tools.DIAGNOSIS_TOOLS,
                           REQUIRED, max_calls=6)
    out.setdefault("cached_vs_live_discrepancy", False)
    out.setdefault("discrepancy_detail", None)
    return {"diagnosis": out, "trace": with_trace(state, trace)}
