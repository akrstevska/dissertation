import json

def trigger_text(state) -> str:
    return f"Trigger: {state['trigger']}\nInput: {json.dumps(state['trigger_input'])}"

def with_trace(state, trace):
    return state.get("trace", []) + trace
