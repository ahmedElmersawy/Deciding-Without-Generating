"""The router decision (PLAN.md decision point 1): send a prompt to the small model or the large one.
Same shape as dwg.cacheguard (question, options, render_state, reference, decider factories), so
replay_decisions.py --task router reuses the cache-guard path.

Deciders are told who the two models are: the decision is about *this* small model's ability, so
a decider that doesn't know which model it is would be guessing at general difficulty. They see
the prompt only, never the models' recorded answers or scores.
"""

from __future__ import annotations

from typing import Any

SMALL = "small"
LARGE = "large"

ROUTER_QUESTION = (
    "A router sends each prompt to one of two models: a small, cheap one (Mixtral-8x7B-Instruct, an "
    "open-weights 2023 mixture-of-experts chat model) or a large, expensive one (GPT-4, about 10-50x the "
    "cost). Route to the large model only if the small model is likely to get this prompt wrong and the "
    "large model to get it right; otherwise the small model is enough."
)

OPTIONS = {
    SMALL: "Send it to the small model (Mixtral-8x7B): it will answer correctly, or the large model would fail too.",
    LARGE: "Send it to the large model (GPT-4): the small model is likely to get it wrong and the large one right.",
}

ROUTER_SYSTEM = (
    "You are the router of an LLM service. You do NOT answer the prompt. You only decide which model "
    "should answer it, by calling `decide_next_action` once. " + ROUTER_QUESTION
)

MAX_PROMPT_CHARS = 3000  # a few RouterBench prompts are long passages; the head shows the task


def render_state(row: dict[str, Any]) -> str:
    prompt = row["query"].strip()
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS] + " [...]"
    return f"Prompt to route:\n{prompt}"


def reference(row: dict[str, Any]) -> str:
    return row["label"]


# Framing for the shared deciders (JevChoiceDecider(question=...), LLMChoiceDecider(system=...)).
QUESTION, SYSTEM, CHOICE_NAME = ROUTER_QUESTION, ROUTER_SYSTEM, "route"
