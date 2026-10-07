"""Model wrapper and structured output. Built before the agents on purpose."""
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL", "claude-haiku-4-5-20251001")
# gpt-6-luna rejects temperature; langchain_openai already drops it for gpt-5 models,
# so every tested model runs at its default
NO_TEMPERATURE = {"gpt-6-luna"}


def get_llm(tools=None, temperature=0.0):
    if MODEL.startswith("gpt"):
        from langchain_openai import ChatOpenAI
        # this model only accepts function tools over /v1/responses
        llm = ChatOpenAI(model=MODEL, use_responses_api=True,
                         temperature=None if MODEL in NO_TEMPERATURE else temperature)
    else:
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=MODEL, temperature=temperature, max_tokens=2000)
    return llm.bind_tools(tools) if tools else llm


def text_of(reply) -> str:
    """Responses-API replies carry content as a list of blocks, not a string."""
    c = reply.content
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict))
    return c or ""


def extract_json(text: str) -> dict:
    """Pull a JSON object out of a model response."""
    text = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    depth, start = 0, None
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    raise ValueError(f"no JSON in response: {text[:200]}")


def ask_json(prompt: str, required: list[str], attempts: int = 3) -> dict:
    """Ask for JSON, repair on failure. Returns a dict with all required keys."""
    llm = get_llm()
    msg = prompt
    last = ""
    for _ in range(attempts):
        last = text_of(llm.invoke(msg))
        try:
            out = extract_json(last)
        except ValueError as e:
            msg = f"{prompt}\n\nYour last reply was not valid JSON ({e}). Reply with the JSON object only."
            continue
        missing = [k for k in required if k not in out]
        if not missing:
            return out
        msg = f"{prompt}\n\nYour last reply was missing: {missing}. Reply with the complete JSON object only."
    raise ValueError(f"failed after {attempts} attempts: {last[:300]}")


def _clip(s: str, limit: int = 4000) -> str:
    """Never cut a value in half silently: a halved number reads as a real reading."""
    return s if len(s) <= limit else f"{s[:limit]} ...[truncated, {len(s)} chars total]"


def run_agent(system: str, task: str, tools: list, required: list[str],
              max_calls: int = 6) -> tuple[dict, list]:
    """Tool-calling loop. Returns (parsed output, trace)."""
    from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

    by_name = {t.name: t for t in tools}
    llm = get_llm(tools)
    messages = [SystemMessage(system), HumanMessage(task)]
    trace = []

    for _ in range(max_calls):
        reply = llm.invoke(messages)
        messages.append(reply)
        if not reply.tool_calls:
            break
        for call in reply.tool_calls:
            result = by_name[call["name"]].invoke(call["args"])
            trace.append({"tool": call["name"], "args": call["args"], "result": result})
            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    final = "\n".join(text_of(m) for m in messages[-2:] if getattr(m, "content", None))
    try:
        out = extract_json(final)
        if all(k in out for k in required):
            return out, trace
    except ValueError:
        pass

    context = "\n".join(f"{t['tool']}({t['args']}) -> {_clip(t['result'])}" for t in trace)
    out = ask_json(
        f"{system}\n\nTask: {task}\n\nData gathered:\n{context}\n\nReply with the JSON object only.",
        required)
    return out, trace
