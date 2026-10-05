"""The cache-guard decision (PLAN.md decision point 2): what every decider is asked, and how a
stream row (scripts/build_cacheguard_streams.py) becomes the state it sees.

A semantic cache returned the most similar earlier query; the decider says `reuse` (serve the
cached answer) or `regenerate`. Deciders see the two queries and, where the dataset has one, the
cached answer; never the similarity score, which belongs to the threshold baseline and the
threshold -> Jev cascade (the cascade uses it to pick which queries reach Jev at all).

Same `Decider` interface as agent control: `decide(state, options)` with options name ->
description. Jev / Kev get CACHE_GUARD_QUESTION as the choice's instructions, LLM deciders get
CACHE_GUARD_SYSTEM as the system prompt (`JevChoiceDecider(question=...)`,
`LLMChoiceDecider(system=...)`).
"""

from __future__ import annotations

from typing import Any

REUSE = "reuse"
REGENERATE = "regenerate"

CACHE_GUARD_QUESTION = (
    "A semantic cache matched the new query to a stored earlier query. Can the stored answer be "
    "returned as the answer to the new query, unchanged? Reuse only if it fully and correctly "
    "answers the new query; if the queries differ in anything that changes the answer (numbers, "
    "names, dates, direction, what is asked), regenerate."
)

OPTIONS = {
    REUSE: "Serve the cached answer: it fully and correctly answers the new query as it is.",
    REGENERATE: "Generate a fresh answer: the cached answer would be wrong, incomplete, or answer a different question.",
}

CACHE_GUARD_SYSTEM = (
    "You guard the semantic cache of an LLM service. You do NOT answer the query. You only decide "
    "whether the cached answer can be served for the new query, by calling `decide_next_action` "
    "once. " + CACHE_GUARD_QUESTION
)

# Long cached answers (LmArena chat replies run to several thousand characters) are cut here so
# a decider's cost doesn't scale with answer length; the head of an answer shows what it answers.
MAX_ANSWER_CHARS = 2000

# SearchQueries ships a placeholder instead of answers (correctness is by id_set alone).
_NO_ANSWER_MARKERS = ("not required for the benchmark",)


def has_answer(row: dict[str, Any]) -> bool:
    response = (row.get("cand_response") or "").strip()
    return bool(response) and not any(m in response.lower() for m in _NO_ANSWER_MARKERS)


def render_state(row: dict[str, Any]) -> str:
    """The text every decider sees for one stream row."""
    parts = [f"New query:\n{row['query'].strip()}", f"Cached query:\n{row['cand_prompt'].strip()}"]
    if has_answer(row):
        answer = row["cand_response"].strip()
        if len(answer) > MAX_ANSWER_CHARS:
            answer = answer[:MAX_ANSWER_CHARS] + " [...]"
        parts.append(f"Cached answer:\n{answer}")
    return "\n\n".join(parts)


def reference(row: dict[str, Any]) -> str:
    """The correct decision for a stream row."""
    return REUSE if row["reuse_correct"] else REGENERATE


def jev_decider(**kwargs):
    """Jev asked the cache-guard question (kwargs as JevChoiceDecider)."""
    from dwg.decisions import JevChoiceDecider

    return JevChoiceDecider(question=CACHE_GUARD_QUESTION, choice_name="cache_decision", **kwargs)


def kev_decider(**kwargs):
    from dwg.decisions import make_kev_decider

    return make_kev_decider(question=CACHE_GUARD_QUESTION, choice_name="cache_decision", **kwargs)


def llm_decider(model: str, **kwargs):
    """An LLM asked the cache-guard question as a constrained tool call (kwargs as LLMChoiceDecider)."""
    from dwg.decisions import LLMChoiceDecider

    return LLMChoiceDecider(model, system=CACHE_GUARD_SYSTEM, **kwargs)
