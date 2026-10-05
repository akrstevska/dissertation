from langgraph.graph import StateGraph, END
from state import PipelineState
from routing import after_diagnosis
from agents import detection, diagnosis, remediation, escalation


def build():
    g = StateGraph(PipelineState)
    g.add_node("detection", detection)
    g.add_node("diagnosis", diagnosis)
    g.add_node("remediation", remediation)
    g.add_node("escalation", escalation)

    g.set_entry_point("detection")
    g.add_edge("detection", "diagnosis")
    g.add_conditional_edges("diagnosis", after_diagnosis,
                            {"remediation": "remediation", "escalation": "escalation"})
    g.add_edge("remediation", "escalation")
    g.add_edge("escalation", END)
    return g.compile()


pipeline = build()
