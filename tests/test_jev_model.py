import pytest
from smolagents.models import (
    ChatMessage,
    ChatMessageToolCall,
    ChatMessageToolCallFunction,
    MessageRole,
    Model,
)
from smolagents.monitoring import TokenUsage
from smolagents.tools import Tool

from dwg.jev import JevDecider
from dwg.jev_model import JevModel, JevModelError


class _FakeJevSession:
    def __init__(self, choice_answer: dict):
        self._choice_answer = choice_answer
        self.last_request = None

    def post(self, url, json, headers, timeout):
        self.last_request = {"url": url, "json": json}
        return _FakeResponse(200, self._choice_answer)


class _FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class _FakeFillerModel(Model):
    """A stand-in for LiteLLMModel's native tool-calling (tool_choice='required')."""

    def __init__(self, arguments: dict | None):
        super().__init__()
        self._arguments = arguments  # None simulates "produced no tool call"
        self.last_messages = None
        self.last_tools_to_call_from = None

    def generate(self, messages, stop_sequences=None, response_format=None, tools_to_call_from=None, **kw):
        self.last_messages = messages
        self.last_tools_to_call_from = tools_to_call_from
        tool_calls = None
        if self._arguments is not None:
            tool_name = tools_to_call_from[0].name
            tool_calls = [
                ChatMessageToolCall(
                    id="call_1",
                    type="function",
                    function=ChatMessageToolCallFunction(name=tool_name, arguments=self._arguments),
                )
            ]
        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_calls=tool_calls,
            raw={"fake": True},
            token_usage=TokenUsage(input_tokens=5, output_tokens=3),
        )


def _make_tool(name: str, description: str, inputs: dict) -> Tool:
    tool = Tool()
    tool.name = name
    tool.description = description
    tool.inputs = inputs
    tool.output_type = "string"
    return tool


def _jev_body(choice: str, options: list[str]):
    return {
        "model": "jev-1.13-test",
        "answers": {
            "tool_choice": {
                "type": "choice",
                "choice": choice,
                "probabilities": {o: (1.0 if o == choice else 0.0) for o in options},
                "confidence": 1.0,
            }
        },
        "usage": {"input_tokens": 100, "output_tokens": 10, "cost": 0.00001},
    }


def test_generate_fills_arguments_via_filler_model_for_chosen_tool():
    search_tool = _make_tool("search", "search the web", {"query": {"type": "string", "description": "the query"}})
    final_tool = _make_tool("final_answer", "give the final answer", {"answer": {"type": "any", "description": "x"}})

    jev = JevDecider(api_key="k", session=_FakeJevSession(_jev_body("search", ["search", "final_answer"])))
    filler = _FakeFillerModel(arguments={"query": "capital of France"})
    model = JevModel(jev=jev, filler_model=filler)

    result = model.generate(
        messages=[ChatMessage(role=MessageRole.USER, content="What's the capital of France?")],
        tools_to_call_from=[search_tool, final_tool],
    )

    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert call.function.name == "search"
    assert call.function.arguments == {"query": "capital of France"}
    # combined token usage: Jev (100/10) + filler (5/3)
    assert result.token_usage.input_tokens == 105
    assert result.token_usage.output_tokens == 13
    # filler must be constrained to ONLY the tool Jev picked, not free to choose another
    assert filler.last_tools_to_call_from == [search_tool]


def test_generate_skips_filler_when_tool_has_no_inputs():
    noop_tool = _make_tool("noop", "do nothing", {})
    jev = JevDecider(api_key="k", session=_FakeJevSession(_jev_body("noop", ["noop"])))
    filler = _FakeFillerModel(arguments={"should": "never be used"})
    model = JevModel(jev=jev, filler_model=filler)

    result = model.generate(
        messages=[ChatMessage(role=MessageRole.USER, content="do something")],
        tools_to_call_from=[noop_tool],
    )

    assert result.tool_calls[0].function.arguments == {}
    assert filler.last_messages is None  # never invoked


def test_unknown_choice_raises():
    tool = _make_tool("search", "search", {})
    jev = JevDecider(api_key="k", session=_FakeJevSession(_jev_body("not_a_real_tool", ["search"])))
    model = JevModel(jev=jev, filler_model=_FakeFillerModel(arguments={}))

    with pytest.raises(JevModelError, match="unknown tool"):
        model.generate(messages=[ChatMessage(role=MessageRole.USER, content="hi")], tools_to_call_from=[tool])


def test_no_tools_raises():
    model = JevModel(
        jev=JevDecider(api_key="k", session=_FakeJevSession({})), filler_model=_FakeFillerModel(arguments={})
    )
    with pytest.raises(JevModelError, match="tools_to_call_from was empty"):
        model.generate(messages=[ChatMessage(role=MessageRole.USER, content="hi")], tools_to_call_from=[])


def test_filler_producing_no_tool_call_raises():
    tool = _make_tool("search", "search", {"query": {"type": "string", "description": "q"}})
    jev = JevDecider(api_key="k", session=_FakeJevSession(_jev_body("search", ["search"])))
    model = JevModel(jev=jev, filler_model=_FakeFillerModel(arguments=None))

    with pytest.raises(JevModelError, match="produced no tool call"):
        model.generate(messages=[ChatMessage(role=MessageRole.USER, content="hi")], tools_to_call_from=[tool])
