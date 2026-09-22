"""smolagents `Model` adapter for Jev — the `JevModel` from System1_Jev_Benchmark.pdf.

Jev is not autoregressive: it can only rank tools (incl. `final_answer`) as a typed
choice over the conversation so far — it cannot write text or fill in tool call
arguments. This adapter asks `JevDecider` which tool to call, then delegates ONLY
the argument-filling to a separate `filler_model` (any smolagents `Model`, e.g.
`LiteLLMModel`). See CHECKS.md #3/#4 for the original design and DECISIONS.md for
the resolved Jev integration.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

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

TOOL_CHOICE_QUESTION = "tool_choice"


class JevModelError(RuntimeError):
    """Raised when Jev's choice isn't a real tool, or the filler model's output isn't valid JSON."""


class JevModel(Model):
    """A smolagents `Model` where Jev picks the tool and `filler_model` fills its arguments."""

    def __init__(self, jev: JevDecider, filler_model: Model, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.jev = jev
        self.filler_model = filler_model

    def generate(
        self,
        messages: list[ChatMessage],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        **kwargs: Any,
    ) -> ChatMessage:
        if not tools_to_call_from:
            raise JevModelError("JevModel only supports tool-calling agents; tools_to_call_from was empty")

        tools_by_name = {tool.name: tool for tool in tools_to_call_from}
        answer = self.jev.choice(
            state=_render_transcript(messages),
            name=TOOL_CHOICE_QUESTION,
            instructions="Given the conversation so far, which tool should be called next?",
            criteria={name: (tool.description or "") for name, tool in tools_by_name.items()},
        )

        tool = tools_by_name.get(answer.choice)
        if tool is None:
            raise JevModelError(f"Jev chose an unknown tool {answer.choice!r}; available: {list(tools_by_name)}")

        arguments, filler_raw, filler_usage = self._fill_arguments(messages, tool)

        tool_call = ChatMessageToolCall(
            id=f"jev_{uuid.uuid4().hex[:8]}",
            type="function",
            function=ChatMessageToolCallFunction(name=tool.name, arguments=arguments),
        )
        jev_usage = self.jev.last_response["usage"]
        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_calls=[tool_call],
            raw={"jev": self.jev.last_response, "filler": filler_raw},
            token_usage=TokenUsage(
                input_tokens=jev_usage["input_tokens"] + filler_usage.input_tokens,
                output_tokens=jev_usage["output_tokens"] + filler_usage.output_tokens,
            ),
        )

    def _fill_arguments(
        self, messages: list[ChatMessage], tool: Tool
    ) -> tuple[dict[str, Any], Any, TokenUsage]:
        if not tool.inputs:
            return {}, None, TokenUsage(0, 0)

        # Constrain the filler to this ONE tool and let smolagents' own native tool-calling
        # (tool_choice="required" by default) produce the arguments — far more robust than
        # asking a chat model to freehand JSON in `content`, which several models mangle or
        # skip in favor of a native tool_call, leaving `content` empty.
        response = self.filler_model.generate(messages, tools_to_call_from=[tool])
        if not response.tool_calls:
            raise JevModelError(f"filler model produced no tool call for {tool.name!r}: {response.content!r}")
        return response.tool_calls[0].function.arguments, response.raw, response.token_usage or TokenUsage(0, 0)


def _render_transcript(messages: list[ChatMessage]) -> str:
    lines = []
    for message in messages:
        role = message.role.value if hasattr(message.role, "value") else message.role
        content = message.content if isinstance(message.content, str) else json.dumps(message.content)
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
