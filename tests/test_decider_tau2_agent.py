import importlib.util
from pathlib import Path
from unittest.mock import patch

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
from tau2.environment.tool import as_tool

from dwg.decider_tau2_agent import DeciderTau2Agent
from dwg.decisions import RESPOND_TO_USER, Decision, NoDecisionError


def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: first addend
        b: second addend
    """
    return a + b


class _FakeDecider:
    name = "fake"

    def __init__(self, choice=None, error=None):
        self.choice, self.error, self.seen = choice, error, []

    def decide(self, state, options):
        self.seen.append(options)
        if self.error:
            raise self.error
        return Decision(choice=self.choice, confidence=0.9, probabilities=None, latency_s=0.01,
                        cost_usd=1e-5, input_tokens=100, output_tokens=2, model="fake")


def _agent(decider):
    return DeciderTau2Agent(tools=[as_tool(add)], domain_policy="be nice", decider=decider, filler_llm="fake/g")


def _tool_msg():
    return AssistantMessage(role="assistant", content=None, cost=2e-5,
                            tool_calls=[ToolCall(id="c1", name="add", arguments={"a": 1, "b": 2})],
                            usage={"prompt_tokens": 20, "completion_tokens": 5})


def test_decider_picks_tool_and_g_is_constrained_to_it():
    agent = _agent(_FakeDecider("add"))
    with patch("dwg.decider_tau2_agent.generate", return_value=_tool_msg()) as gen:
        msg, _ = agent.generate_next_message(UserMessage.text("1+2?"), agent.get_init_state())
    kwargs = gen.call_args.kwargs
    assert [t.name for t in kwargs["tools"]] == ["add"] and kwargs["tool_choice"] == "required"
    step = agent.steps[0]
    assert step["choice"] == "add" and step["executed"] == "add" and not step["decider_failed"]
    assert step["decision_cost_usd"] == 1e-5 and step["exec_cost_usd"] == 2e-5
    assert abs(msg.cost - 3e-5) < 1e-12  # decision $ folded into tau2's agent cost
    assert RESPOND_TO_USER in agent.decider.seen[0]


def test_respond_choice_gives_g_no_tools():
    agent = _agent(_FakeDecider(RESPOND_TO_USER))
    reply = AssistantMessage(role="assistant", content="3", cost=1e-5, usage=None)
    with patch("dwg.decider_tau2_agent.generate", return_value=reply) as gen:
        agent.generate_next_message(UserMessage.text("1+2?"), agent.get_init_state())
    assert gen.call_args.kwargs["tools"] is None
    assert agent.steps[0]["executed"] == RESPOND_TO_USER


def test_decider_failure_falls_back_to_g_and_is_flagged():
    # a raised failure costs nothing; an invalid answer was still a billed call, so its $ is kept
    for decider, cost in ((_FakeDecider(error=NoDecisionError("no call")), 2e-5), (_FakeDecider("not_a_tool"), 3e-5)):
        agent = _agent(decider)
        with patch("dwg.decider_tau2_agent.generate", return_value=_tool_msg()) as gen:
            msg, _ = agent.generate_next_message(UserMessage.text("1+2?"), agent.get_init_state())
        assert gen.call_args.kwargs["call_name"] == "decider_fallback"
        assert [t.name for t in gen.call_args.kwargs["tools"]] == ["add"]
        assert agent.steps[0]["decider_failed"] and agent.steps[0]["choice"] is None
        assert abs(msg.cost - cost) < 1e-12


def _analyze():
    spec = importlib.util.spec_from_file_location("analyze_inloop", Path(__file__).parent.parent / "scripts" / "analyze_inloop.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pass_hat_k():
    m = _analyze()
    by_task = {"t1": [True, True, False, True], "t2": [False] * 4}
    assert m.pass_hat_k(by_task, 1) == (0.75 + 0) / 2
    assert m.pass_hat_k(by_task, 3) == (1 / 4 + 0) / 2  # C(3,3)/C(4,3)
    assert m.pass_hat_k(by_task, 4) == 0.0
