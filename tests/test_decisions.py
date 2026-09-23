import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage

from dwg.decisions import (
    RESPOND_TO_USER,
    JevChoiceDecider,
    LLMChoiceDecider,
    action_label,
    render_transcript,
)
from dwg.jev import ChoiceAnswer

OPTIONS = {"create_task": "Create a task.", RESPOND_TO_USER: "Reply to the user."}


def _tool_call_message():
    return AssistantMessage(
        role="assistant",
        content=None,
        tool_calls=[ToolCall(id="1", name="create_task", arguments={"title": "x"})],
    )


def test_render_transcript_shows_tool_calls_instead_of_none():
    text = render_transcript([UserMessage(role="user", content="hi"), _tool_call_message()])
    assert "user: hi" in text
    assert 'assistant: [tool call] create_task({"title": "x"})' in text
    assert "None" not in text


def test_action_label():
    assert action_label(_tool_call_message()) == "create_task"
    assert action_label(AssistantMessage(role="assistant", content="ok")) == RESPOND_TO_USER


def test_jev_choice_decider_reports_choice_confidence_and_cost():
    jev = MagicMock()
    jev.choice.return_value = ChoiceAnswer(
        choice="create_task",
        probabilities={"create_task": 0.9, RESPOND_TO_USER: 0.1},
        vendor_confidence=0.85,
        model="typesafe/jev-1.13",
        usage={"input_tokens": 100, "output_tokens": 5, "cost": 1e-5},
    )
    d = JevChoiceDecider(jev=jev).decide("state", OPTIONS)
    assert (d.choice, d.confidence, d.cost_usd, d.input_tokens) == ("create_task", 0.9, 1e-5, 100)
    assert d.latency_s >= 0
    assert jev.choice.call_args.kwargs["criteria"] == OPTIONS


def _fake_completion(action, confidence, cost=2e-5):
    call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps({"action": action, "confidence": confidence})))
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=12, cost=cost),
        model="openai/gpt-oss-20b",
    )


def test_llm_choice_decider_constrains_to_options_and_reads_openrouter_cost():
    with patch("litellm.completion", return_value=_fake_completion(RESPOND_TO_USER, 1.7)) as completion:
        d = LLMChoiceDecider(model="openrouter/openai/gpt-oss-20b").decide("state", OPTIONS)
    assert d.choice == RESPOND_TO_USER
    assert d.confidence == 1.0  # clipped into [0, 1]
    assert d.cost_usd == 2e-5 and d.input_tokens == 120
    kwargs = completion.call_args.kwargs
    assert kwargs["tools"][0]["function"]["parameters"]["properties"]["action"]["enum"] == list(OPTIONS)
    assert kwargs["messages"][1] == {"role": "user", "content": "state"}


def test_llm_choice_decider_rejects_out_of_set_answer():
    with patch("litellm.completion", return_value=_fake_completion("delete_everything", 0.5)):
        try:
            LLMChoiceDecider(model="m").decide("state", OPTIONS)
        except ValueError as exc:
            assert "delete_everything" in str(exc)
        else:
            raise AssertionError("expected ValueError")
