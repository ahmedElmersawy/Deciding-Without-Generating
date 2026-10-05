"""Cache-guard decision (dwg.cacheguard): state rendering, labels, and that the agent-control
defaults of the shared deciders are unchanged."""

from dwg import cacheguard as cg

# Hand-made cases, one per kind of decision the benchmarks contain (PLAN.md CG2). Also used by
# the live smoke run (scripts/smoke_cacheguard.py) to see each decider answer them sensibly.
HAND_CASES = [
    dict(name="paraphrase", query="How do I reverse a list in Python?", cand_prompt="What's the way to reverse a Python list?",
         cand_response="Use list.reverse() to reverse in place, or reversed(lst) / lst[::-1] for a reversed copy.", reuse_correct=True),
    dict(name="number changed", query="What is 15% of 90?", cand_prompt="What is 15% of 80?",
         cand_response="15% of 80 is 12.", reuse_correct=False),
    dict(name="direction swapped", query="Cheapest flights from Florida to New York", cand_prompt="Cheapest flights from New York to Florida",
         cand_response="Spirit and Frontier usually have the lowest fares from New York to Florida.", reuse_correct=False),
    dict(name="distractor added", query="Tom has 3 apples and buys 2 more. His sister is 7. How many apples does Tom have?",
         cand_prompt="Tom has 3 apples and buys 2 more. How many apples does Tom have?", cand_response="5", reuse_correct=True),
    dict(name="different question, same topic", query="Who wrote Pride and Prejudice?", cand_prompt="When was Pride and Prejudice published?",
         cand_response="It was published in 1813.", reuse_correct=False),
    dict(name="search, no answer", query="cost of kitchen countertops installed", cand_prompt="kitchen countertop installation price",
         cand_response="Not required for the benchmark because of the id_set", reuse_correct=True),
]


def test_render_state_shows_both_queries_and_answer():
    s = cg.render_state(HAND_CASES[1])
    assert "New query:\nWhat is 15% of 90?" in s and "Cached query:\nWhat is 15% of 80?" in s
    assert "Cached answer:\n15% of 80 is 12." in s
    assert "similar" not in s.lower().split("cached answer")[0].replace("semantic", "")  # no similarity score leaks in


def test_render_state_skips_placeholder_answers_and_truncates_long_ones():
    assert "Cached answer" not in cg.render_state(HAND_CASES[-1])
    long = dict(HAND_CASES[0], cand_response="x" * (cg.MAX_ANSWER_CHARS + 500))
    s = cg.render_state(long)
    assert s.endswith(" [...]") and len(s.split("Cached answer:\n")[1]) == cg.MAX_ANSWER_CHARS + len(" [...]")


def test_reference_and_options():
    assert [cg.reference(c) for c in HAND_CASES[:3]] == [cg.REUSE, cg.REGENERATE, cg.REGENERATE]
    assert set(cg.OPTIONS) == {cg.REUSE, cg.REGENERATE}


def test_agent_control_defaults_unchanged():
    from dwg.decisions import DECISION_QUESTION, LLM_DECIDER_SYSTEM, JevChoiceDecider, LLMChoiceDecider

    jev = JevChoiceDecider(jev=object())
    assert jev.question == DECISION_QUESTION and jev.choice_name == "next_action"
    assert LLMChoiceDecider("openrouter/openai/gpt-oss-20b").system == LLM_DECIDER_SYSTEM
    guard = cg.llm_decider("openrouter/openai/gpt-oss-20b")
    assert guard.system == cg.CACHE_GUARD_SYSTEM
