"""tau2-bench-native agent adapter for Jev.

tau2-bench (github.com/sierra-research/tau2-bench) has its own agent protocol
(`HalfDuplexAgent`), separate from smolagents — so `dwg.jev_model.JevModel` (built
for smolagents' `ToolCallingAgent`) can't be plugged into a tau2 domain directly.
This is the same design reimplemented against tau2's own `Message`/`Tool` types and
its `generate()` helper: Jev decides whether to respond to the user or call a tool
(and which one), then `filler_llm` (any LiteLLM model id, via tau2's own `generate()`)
produces the actual text or tool-call arguments. See DECISIONS.md (2026-09-22) and
`src/dwg/jev_model.py` for the smolagents version of this same pattern.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from tau2.agent.base_agent import (
    HalfDuplexAgent,
    ValidAgentInputMessage,
    is_valid_agent_history_message,
)
from tau2.data_model.message import (
    APICompatibleMessage,
    AssistantMessage,
    Message,
    MultiToolMessage,
    SystemMessage,
)
from tau2.environment.tool import Tool
from tau2.utils.llm_utils import generate

from dwg.decisions import DECISION_QUESTION, RESPOND_TO_USER, decision_options, render_transcript
from dwg.jev import JevDecider

__all__ = ["JevTau2Agent", "JevTau2AgentState", "RESPOND_TO_USER"]

AGENT_INSTRUCTION = """
You are a customer service agent that helps the user according to the <policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only.
""".strip()

SYSTEM_PROMPT = """
<instructions>
{agent_instruction}
</instructions>
<policy>
{domain_policy}
</policy>
""".strip()


class JevTau2AgentState(BaseModel):
    """The state of the agent."""

    system_messages: list[SystemMessage]
    messages: list[APICompatibleMessage]


class JevTau2Agent(HalfDuplexAgent[JevTau2AgentState]):
    """Jev decides respond-vs-tool-call (and which tool); `filler_llm` fills it in."""

    def __init__(
        self,
        tools: list[Tool],
        domain_policy: str,
        jev: JevDecider,
        filler_llm: str,
        filler_llm_args: Optional[dict] = None,
    ):
        super().__init__(tools=tools, domain_policy=domain_policy)
        self.jev = jev
        self.filler_llm = filler_llm
        self.filler_llm_args = filler_llm_args or {}

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            agent_instruction=AGENT_INSTRUCTION, domain_policy=self.domain_policy
        )

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> JevTau2AgentState:
        if message_history is None:
            message_history = []
        assert all(is_valid_agent_history_message(m) for m in message_history), (
            "Message history must contain only AssistantMessage, UserMessage, or ToolMessage to Agent."
        )
        return JevTau2AgentState(
            system_messages=[SystemMessage(role="system", content=self.system_prompt)],
            messages=message_history,
        )

    def generate_next_message(
        self, message: ValidAgentInputMessage, state: JevTau2AgentState
    ) -> tuple[AssistantMessage, JevTau2AgentState]:
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)
        messages = state.system_messages + state.messages

        tools_by_name = {tool.name: tool for tool in self.tools}
        answer = self.jev.choice(
            state=render_transcript(messages),
            name="tool_choice",
            instructions=DECISION_QUESTION,
            criteria=decision_options(self.tools),
        )

        if answer.choice == RESPOND_TO_USER:
            assistant_message = generate(
                model=self.filler_llm,
                tools=None,
                messages=messages,
                call_name="jev_filler_respond",
                **self.filler_llm_args,
            )
        else:
            tool = tools_by_name.get(answer.choice)
            if tool is None:
                raise ValueError(
                    f"Jev chose an unknown tool {answer.choice!r}; available: {list(tools_by_name)}"
                )
            assistant_message = generate(
                model=self.filler_llm,
                tools=[tool],
                tool_choice="required",
                messages=messages,
                call_name="jev_filler_toolcall",
                **self.filler_llm_args,
            )

        _fold_in_jev_cost(assistant_message, self.jev.last_response["usage"])
        state.messages.append(assistant_message)
        return assistant_message, state


def _fold_in_jev_cost(message: AssistantMessage, jev_usage: dict) -> None:
    """Add Jev's own token usage/cost into the assistant message so tau2's cost accounting sees it."""
    message.cost = (message.cost or 0.0) + jev_usage.get("cost", 0.0)
    if message.usage is not None:
        message.usage["completion_tokens"] += jev_usage["output_tokens"]
        message.usage["prompt_tokens"] += jev_usage["input_tokens"]
    else:
        message.usage = {
            "completion_tokens": jev_usage["output_tokens"],
            "prompt_tokens": jev_usage["input_tokens"],
        }
