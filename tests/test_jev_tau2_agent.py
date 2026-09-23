from unittest.mock import patch

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
from tau2.environment.tool import as_tool

from dwg.jev import JevDecider
from dwg.jev_tau2_agent import RESPOND_TO_USER, JevTau2Agent


def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: first addend
        b: second addend
    """
    return a + b


class _FakeJevSession:
    def __init__(self, choice: str, options: list[str]):
        self._choice = choice
        self._options = options

    def post(self, url, json, headers, timeout):
        return _FakeResponse(
            {
                "model": "jev-1.13-test",
                "answers": {
                    "tool_choice": {
                        "type": "choice",
                        "choice": self._choice,
                        "probabilities": {o: (1.0 if o == self._choice else 0.0) for o in self._options},
                        "confidence": 1.0,
                    }
                },
                "usage": {"input_tokens": 100, "output_tokens": 10, "cost": 0.00001},
            }
        )


class _FakeResponse:
    def __init__(self, body):
        self.status_code = 200
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


def _make_agent(choice: str, tools) -> JevTau2Agent:
    options = [t.name for t in tools] + [RESPOND_TO_USER]
    jev = JevDecider(api_key="k", session=_FakeJevSession(choice, options))
    return JevTau2Agent(tools=tools, domain_policy="be nice", jev=jev, filler_llm="fake/model")


def test_jev_chooses_tool_and_filler_fills_arguments():
    tool = as_tool(add)
    agent = _make_agent(choice="add", tools=[tool])
    state = agent.get_init_state()

    filler_response = AssistantMessage(
        role="assistant",
        content=None,
        tool_calls=[ToolCall(id="c1", name="add", arguments={"a": 47, "b": 89})],
        cost=0.00002,
        usage={"prompt_tokens": 20, "completion_tokens": 5},
    )
    with patch("dwg.jev_tau2_agent.generate", return_value=filler_response) as mock_generate:
        result, state = agent.generate_next_message(UserMessage.text("what's 47 + 89?"), state)

    # filler was constrained to exactly the tool Jev picked
    _, kwargs = mock_generate.call_args
    assert [t.name for t in kwargs["tools"]] == ["add"]
    assert kwargs["tool_choice"] == "required"

    assert result.tool_calls[0].name == "add"
    assert result.tool_calls[0].arguments == {"a": 47, "b": 89}
    # Jev's usage/cost folded into the assistant message
    assert result.cost == 0.00002 + 0.00001
    assert result.usage == {"prompt_tokens": 20 + 100, "completion_tokens": 5 + 10}


def test_jev_chooses_respond_to_user_skips_tools():
    tool = as_tool(add)
    agent = _make_agent(choice=RESPOND_TO_USER, tools=[tool])
    state = agent.get_init_state()

    filler_response = AssistantMessage(role="assistant", content="Sure, happy to help!", cost=0.00001, usage=None)
    with patch("dwg.jev_tau2_agent.generate", return_value=filler_response) as mock_generate:
        result, state = agent.generate_next_message(UserMessage.text("hi"), state)

    _, kwargs = mock_generate.call_args
    assert kwargs["tools"] is None
    assert result.content == "Sure, happy to help!"
    assert result.tool_calls is None
    # usage was None on the filler response; Jev's usage becomes the whole thing
    assert result.usage == {"prompt_tokens": 100, "completion_tokens": 10}
