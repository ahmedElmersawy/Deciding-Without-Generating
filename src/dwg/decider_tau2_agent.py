"""tau2-bench agent where any decider picks the action and a generator LLM G carries it out
(PLAN.md U4, arms A/B/D/E).

`JevTau2Agent` generalized: the decider is anything with `.decide(state, options) ->
Decision` (`dwg.decisions`: Jev, an LLM asked the same constrained question, Kev, a
cascade), so every arm runs the identical loop and differs only in who decides:

    arm A: JevChoiceDecider            + G executes
    arm B: LLMChoiceDecider(model=G)   + G executes   (G decides in a separate, constrained call)
    arm D: LLMChoiceDecider(small LLM) + G executes
    arm E: Kev                         + G executes
    arm C (no split) is tau2's own `LLMAgent`, timed by `TimedLLMAgent` below.

Every agent turn is logged in `self.steps` with the decision and the execution kept apart
(latency, $, tokens, GPU energy), so the decision share of an episode's cost can be reported.

If the decider fails (no valid decision, e.g. `NoDecisionError`, Kev's "branch too long"),
G decides that turn itself, unconstrained, and the step is flagged `decider_failed`. Raising
instead would end the episode on the decider's failure, which measures crash handling rather
than decision quality; the fallback rate is reported per arm instead, so a decider that
leans on it can't hide it.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from tau2.agent.llm_agent import LLMAgent
from tau2.data_model.message import AssistantMessage, MultiToolMessage
from tau2.utils.llm_utils import generate

from dwg.decisions import RESPOND_TO_USER, action_label, decision_options, render_transcript
from dwg.jev_tau2_agent import JevTau2Agent, JevTau2AgentState

__all__ = ["DeciderTau2Agent", "TimedLLMAgent"]


def _tokens(message: AssistantMessage) -> tuple[Optional[int], Optional[int]]:
    usage = message.usage or {}
    return usage.get("prompt_tokens"), usage.get("completion_tokens")


class DeciderTau2Agent(JevTau2Agent):
    """`decider` chooses respond-vs-which-tool; `filler_llm` (G) writes the message or arguments."""

    def __init__(self, tools, domain_policy: str, decider, filler_llm: str,
                 filler_llm_args: Optional[dict] = None) -> None:
        # JevTau2Agent's prompt/state handling is reused as is; only the decision step differs.
        super().__init__(tools=tools, domain_policy=domain_policy, jev=None, filler_llm=filler_llm,
                         filler_llm_args=filler_llm_args)
        self.decider = decider
        self.options = decision_options(self.tools)
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.steps: list[dict[str, Any]] = []

    def generate_next_message(self, message, state: JevTau2AgentState):
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)
        messages = state.system_messages + state.messages

        step: dict[str, Any] = {"turn": len(self.steps), "decider": self.decider.name, "decider_failed": False}
        t0 = time.perf_counter()
        try:
            decision = self.decider.decide(render_transcript(messages), self.options)
            step.update(
                choice=decision.choice,
                confidence=decision.confidence,
                decision_latency_s=decision.latency_s,
                decision_cost_usd=decision.cost_usd,
                decision_input_tokens=decision.input_tokens,
                decision_output_tokens=decision.output_tokens,
                decision_energy_j=decision.energy_j,
                escalated=decision.escalated,
            )
            choice = decision.choice
            if choice != RESPOND_TO_USER and choice not in self.tools_by_name:
                raise ValueError(f"decider chose {choice!r}, not one of the options")
        except Exception as exc:  # the decider's failure, not the episode's: G decides this turn
            step.update(decider_failed=True, decider_error=repr(exc)[:300],
                        decision_latency_s=time.perf_counter() - t0, choice=None)
            choice = None

        if choice == RESPOND_TO_USER:
            kwargs = dict(tools=None, call_name="decider_filler_respond")
        elif choice is not None:
            kwargs = dict(tools=[self.tools_by_name[choice]], tool_choice="required",
                          call_name="decider_filler_toolcall")
        else:  # fallback: G picks and fills the action itself, as tau2's LLMAgent would
            kwargs = dict(tools=self.tools or None, call_name="decider_fallback")
        t1 = time.perf_counter()
        assistant_message = generate(model=self.filler_llm, messages=messages, **kwargs, **self.filler_llm_args)
        exec_in, exec_out = _tokens(assistant_message)
        step.update(
            executed=action_label(assistant_message),
            exec_latency_s=time.perf_counter() - t1,
            exec_cost_usd=assistant_message.cost,
            exec_input_tokens=exec_in,
            exec_output_tokens=exec_out,
        )
        self.steps.append(step)

        # tau2 sums AssistantMessage.cost into the episode's agent cost: fold the decision in.
        if step.get("decision_cost_usd"):
            assistant_message.cost = (assistant_message.cost or 0.0) + step["decision_cost_usd"]
        state.messages.append(assistant_message)
        return assistant_message, state


class TimedLLMAgent(LLMAgent):
    """Arm C: tau2's own single-call agent (G decides and executes at once), with the same
    per-turn log as `DeciderTau2Agent`. The decision isn't separable here, so the whole call
    counts as execution and the decision share is zero by construction."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.steps: list[dict[str, Any]] = []

    def generate_next_message(self, message, state):
        t0 = time.perf_counter()
        assistant_message, state = super().generate_next_message(message, state)
        exec_in, exec_out = _tokens(assistant_message)
        self.steps.append({
            "turn": len(self.steps), "decider": None, "decider_failed": False,
            "choice": None, "executed": action_label(assistant_message),
            "decision_latency_s": 0.0, "decision_cost_usd": 0.0,
            "exec_latency_s": time.perf_counter() - t0, "exec_cost_usd": assistant_message.cost,
            "exec_input_tokens": exec_in, "exec_output_tokens": exec_out,
        })
        return assistant_message, state
