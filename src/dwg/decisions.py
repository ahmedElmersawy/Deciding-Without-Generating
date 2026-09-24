"""Decision-only interface for the agent-control decision point (arm 0, DECISIONS.md 2026-09-23).

Every decider answers the same question — "what should the agent do next: respond to the
user, or call tool X?" — over the SAME rendered state string, and returns a `Decision`
carrying the choice, a confidence, and its own latency/cost. Nothing is executed: no reply
text and no tool arguments are generated, so what gets measured is the cost of deciding only.

Fairness choices (logged in DECISIONS.md):
- Identical input: every decider sees `render_transcript(messages)` — the LLM decider gets it
  as one user message, not tau2's native multi-turn/tool-call format, so neither side gets a
  richer view of the state.
- Confidence: Jev's is `probabilities[choice]`; the LLM's is verbalized (it reports a number
  in the constrained decision call). Verbalized confidence is the standard LLM baseline and is
  known to be overconfident — the calibration comparison should say so.
- Latency is client-side wall clock around one HTTP round trip (network included, identical
  for both since both go through OpenRouter). Local System One servers (Kev) also report
  server-side compute time, so API/network overhead can be separated from model time.
- Energy (J) is measured only for local deciders, via `dwg.energy` (whole-GPU, serialized).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

from dwg.jev import JevDecider

RESPOND_TO_USER = "respond_to_user"
RESPOND_DESCRIPTION = "Send a text message directly to the user instead of calling a tool."

DECISION_QUESTION = (
    "Given the conversation so far and the domain policy, should the agent respond "
    "directly to the user, or call one of the tools?"
)


@dataclass
class Decision:
    choice: str
    confidence: Optional[float]
    probabilities: Optional[dict[str, float]]
    latency_s: float
    cost_usd: Optional[float]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    model: str
    server_latency_s: Optional[float] = None  # model-side time, when the server reports it
    energy_j: Optional[float] = None  # gross GPU energy over the call; local deciders only
    escalated: bool = False  # CascadeDecider only: whether the second stage was called

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decision_options(tools) -> dict[str, str]:
    """Option name -> description, for tau2 `Tool`s plus the respond-to-user option."""
    options = {tool.name: tool.openai_schema["function"]["description"] for tool in tools}
    options[RESPOND_TO_USER] = RESPOND_DESCRIPTION
    return options


def render_transcript(messages) -> str:
    """Flatten tau2 messages into the state string every decider sees.

    Tool calls are rendered explicitly — an assistant turn that only calls a tool has
    `content=None`, and dropping its calls would hide what the agent already did.
    """
    lines = []
    for message in messages:
        role = message.role.value if hasattr(message.role, "value") else message.role
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                lines.append(f"{role}: [tool call] {call.name}({json.dumps(call.arguments, sort_keys=True)})")
            if message.content:
                lines.append(f"{role}: {message.content}")
        else:
            lines.append(f"{role}: {message.content}")
    return "\n".join(lines)


def action_label(message) -> str:
    """The decision an assistant message embodies: its first tool's name, or respond_to_user."""
    if getattr(message, "tool_calls", None):
        return message.tool_calls[0].name
    return RESPOND_TO_USER


class JevChoiceDecider:
    """A System One model answers one typed `choice` question over the rendered state.

    Jev through OpenRouter by default; any System One-compatible server (e.g. local Kev, see
    `make_kev_decider`) via a configured `JevDecider`. With `energy_meter`, each call's GPU
    energy is read off NVML's counter — the caller must serialize calls (see `dwg.energy`).
    """

    def __init__(self, jev: Optional[JevDecider] = None, name: str = "jev", energy_meter=None) -> None:
        self.jev = jev or JevDecider()
        self.name = name
        self.energy_meter = energy_meter

    def decide(self, state: str, options: dict[str, str]) -> Decision:
        e0 = self.energy_meter.read_mj() if self.energy_meter else None
        t0 = time.perf_counter()
        answer = self.jev.choice(state=state, name="next_action", instructions=DECISION_QUESTION, criteria=options)
        latency = time.perf_counter() - t0
        energy_j = (self.energy_meter.read_mj() - e0) / 1000.0 if self.energy_meter else None
        server_ms = (self.jev.last_response or {}).get("latency_ms")
        return Decision(
            choice=answer.choice,
            confidence=answer.confidence,
            probabilities=answer.probabilities,
            latency_s=latency,
            cost_usd=answer.usage.get("cost"),
            input_tokens=answer.usage.get("input_tokens"),
            output_tokens=answer.usage.get("output_tokens"),
            model=answer.model,
            server_latency_s=None if server_ms is None else server_ms / 1000.0,
            energy_j=energy_j,
        )


def make_kev_decider(
    base_url: str = "http://127.0.0.1:8009",
    name: str = "kev",
    energy_meter=None,
    timeout: float = 120.0,
) -> JevChoiceDecider:
    """Kev (github.com/jaredpalmer/kev), an open-weights System One reproduction served locally.

    Same wire format as Jev, so the same client and the same question — only the endpoint
    differs. No API cost; latency and (with `energy_meter`) GPU energy are the cost.
    """
    client = JevDecider(base_url=base_url, path="/v1/systemone", model="kev-latest",
                        require_api_key=False, api_key="", timeout=timeout)
    return JevChoiceDecider(jev=client, name=name, energy_meter=energy_meter)


LLM_DECIDER_SYSTEM = (
    "You are the controller of a customer-service agent. You do NOT write the agent's reply or "
    "tool arguments. You only choose the agent's next action by calling `decide_next_action` "
    "once. " + DECISION_QUESTION
)


class LLMChoiceDecider:
    """A generative LLM asked the same decision as a single constrained tool call.

    The action is an enum over the options, so the model cannot answer outside them; it
    also reports a verbalized confidence in [0, 1].
    """

    def __init__(self, model: str, name: Optional[str] = None, **completion_args: Any) -> None:
        self.model = model
        self.name = name or f"llm:{model}"
        self.completion_args = completion_args

    def decide(self, state: str, options: dict[str, str]) -> Decision:
        import litellm

        option_list = "\n".join(f"- {name}: {desc}" for name, desc in options.items())
        tool = {
            "type": "function",
            "function": {
                "name": "decide_next_action",
                "description": "Choose the agent's next action.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": list(options),
                            "description": f"The next action. Options:\n{option_list}",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Probability in [0, 1] that this action is the correct next step.",
                        },
                    },
                    "required": ["action", "confidence"],
                },
            },
        }
        t0 = time.perf_counter()
        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": LLM_DECIDER_SYSTEM},
                {"role": "user", "content": state},
            ],
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": "decide_next_action"}},
            # Ask OpenRouter for its own per-call $ cost — the same source Jev's cost comes from.
            extra_body={"usage": {"include": True}},
            **self.completion_args,
        )
        latency = time.perf_counter() - t0

        call = response.choices[0].message.tool_calls[0]
        args = json.loads(call.function.arguments)
        choice = args["action"]
        if choice not in options:
            raise ValueError(f"LLM decider returned {choice!r}, not one of {list(options)}")
        confidence = args.get("confidence")
        usage = response.usage
        return Decision(
            choice=choice,
            confidence=None if confidence is None else min(max(float(confidence), 0.0), 1.0),
            probabilities=None,
            latency_s=latency,
            cost_usd=_openrouter_cost(response),
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            model=response.model or self.model,
        )


class CascadeDecider:
    """Confidence-gated cascade: `fast` answers first; `escalate` is only called when
    `fast`'s own confidence falls below `threshold` (Phase D/2, DECISIONS.md 2026-09-23).

    Reuses the plain `Decider` interface (`.decide(state, options) -> Decision`) for both
    stages, so any combination works — not just Kev-4B -> GPT-OSS-20B. `fast` always runs,
    so its cost/latency/energy are paid on every call; `escalate`'s are added only when it
    runs. Deliberately does NOT attach an NVML energy meter to `fast` here: wrapping a live
    GPU-energy window around a call that may include a slow network round trip to `escalate`
    would count the GPU's idle power during that wait as "decision energy," silently
    inflating the number. The fast stage's per-decision GPU energy is instead the SAME
    already-validated figure from that decider's own standalone replay run (e.g. Kev-4B's
    18.33 J/decision from results/replay/mock-pilot) — attached post-hoc in analysis, not
    re-measured here.
    """

    def __init__(self, fast, escalate, threshold: float, name: Optional[str] = None) -> None:
        self.fast = fast
        self.escalate = escalate
        self.threshold = threshold
        fast_name = getattr(fast, "name", "fast")
        escalate_name = getattr(escalate, "name", "escalate")
        self.name = name or f"cascade-{fast_name}-to-{escalate_name}-t{threshold:g}"

    def decide(self, state: str, options: dict[str, str]) -> Decision:
        d1 = self.fast.decide(state, options)
        if d1.confidence is not None and d1.confidence >= self.threshold:
            d1.escalated = False
            return d1
        d2 = self.escalate.decide(state, options)
        cost = None
        if d1.cost_usd is not None or d2.cost_usd is not None:
            cost = (d1.cost_usd or 0.0) + (d2.cost_usd or 0.0)
        tokens_in = None
        if d1.input_tokens is not None or d2.input_tokens is not None:
            tokens_in = (d1.input_tokens or 0) + (d2.input_tokens or 0)
        tokens_out = None
        if d1.output_tokens is not None or d2.output_tokens is not None:
            tokens_out = (d1.output_tokens or 0) + (d2.output_tokens or 0)
        return Decision(
            choice=d2.choice,
            confidence=d2.confidence,
            probabilities=d2.probabilities,
            latency_s=d1.latency_s + d2.latency_s,  # both stages run, back to back
            cost_usd=cost,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            model=f"{d1.model}->{d2.model}",
            server_latency_s=None,
            energy_j=None,  # attached post-hoc from the fast decider's own standalone run
            escalated=True,
        )


def _openrouter_cost(response) -> Optional[float]:
    """OpenRouter's reported $ cost if present, else LiteLLM's price-map estimate."""
    cost = getattr(response.usage, "cost", None)
    if cost is not None:
        return float(cost)
    try:
        import litellm

        return float(litellm.completion_cost(completion_response=response))
    except Exception:
        return None
