"""The cache-guard decision (PLAN.md decision point 2): what every decider is asked, and how a
stream row (scripts/build_cacheguard_streams.py) becomes the state it sees.

A semantic cache returned the most similar earlier query; the decider says `reuse` (serve the
cached answer) or `regenerate`. Deciders see the two queries only: never the cached answer and
never the similarity score (which belongs to the threshold baseline and the threshold -> Jev
cascade, where it picks which queries reach Jev at all).

The decision is isolated to "is the new query the same request as the cached one?"
(DECISIONS.md 2026-10-07). Whether the stored answer is good is not part of it: reading the answer
would cost most of what the cache saves, answer quality is the job of the model that wrote it and
of the cache's TTL (a correct answer to a time-bound question goes stale whatever wrote it), and a
decider that dislikes an answer from another strong model is two experts disagreeing, not a wrong
cache hit.

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
    "A semantic cache matched the new query to a stored earlier query. Compare the two queries only: "
    "are they the same request, so that an answer written for the stored query also answers the new "
    "one? Reuse if they ask the same thing in different words; if they differ in anything that changes "
    "the answer (numbers, names, dates, direction, what is asked, required format or constraints), "
    "regenerate."
)

OPTIONS = {
    REUSE: "Serve the cached answer: the new query is the same request as the stored query.",
    REGENERATE: "Generate a fresh answer: the new query asks something different from the stored query.",
}

CACHE_GUARD_SYSTEM = (
    "You guard the semantic cache of an LLM service. You do NOT answer the query. You only decide "
    "whether the cached answer can be served for the new query, by calling `decide_next_action` "
    "once. " + CACHE_GUARD_QUESTION
)

# SearchQueries ships a placeholder instead of answers (correctness is by id_set alone).
_NO_ANSWER_MARKERS = ("not required for the benchmark",)


def has_answer(row: dict[str, Any]) -> bool:
    """Whether the dataset stores a real cached answer (used by the label audit, never shown to deciders)."""
    response = (row.get("cand_response") or "").strip()
    return bool(response) and not any(m in response.lower() for m in _NO_ANSWER_MARKERS)


def render_state(row: dict[str, Any]) -> str:
    """The text every decider sees for one stream row: the two queries, nothing else."""
    return f"New query:\n{row['query'].strip()}\n\nCached query:\n{row['cand_prompt'].strip()}"


def reference(row: dict[str, Any]) -> str:
    """The correct decision for a stream row."""
    return REUSE if row["reuse_correct"] else REGENERATE


# Framing for the shared deciders, under the names every decision-point module uses.
QUESTION, SYSTEM, CHOICE_NAME = CACHE_GUARD_QUESTION, CACHE_GUARD_SYSTEM, "cache_decision"


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
