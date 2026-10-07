# Cache-guard label-correction guideline

Written before any pair was reviewed (2026-10-07). Applies to the vCache benchmarks
SemBenchmarkLmArena and SemBenchmarkSearchQueries as used in our cache-guard streams
(`results/states/cacheguard-{lmarena,searchqueries}.jsonl`, all dev + test rows).

## What a label means

A pair is (new query, cached query). The label says whether serving the cached query's answer for
the new query is a correct cache hit, judged **from the two queries alone**:

- **same** (`reuse_correct = true`): one good answer written for the cached query would be a
  correct and complete answer to the new query.
- **different** (`reuse_correct = false`): it would not.

The cached answer is never looked at. Whether a stored answer is good is a property of the model
that wrote it and of the cache's TTL, not of the cache decision (see DECISIONS.md 2026-10-07).
Time sensitivity is also out of scope: "today's weather in London" vs the same query is **same**;
staleness is the TTL's job.

## Same

- Rewording, synonyms, word order, singular/plural, typos, casing, punctuation, filler or
  politeness ("please", "think step by step", "be precise").
- A reworded prompt that keeps every entity, number, condition, direction and constraint.
- LmArena wrapper text such as "Here is a reworded version of the prompt:" around otherwise the
  same request: judge the request inside it.
- Search queries with the same information need, where the same results page serves both
  ("cook lobster tails at home" / "cooking lobster tails at home").

## Different

- A different entity, product, place, person, version or number ("blue mountain" vs "blue
  wilderness" dog food; "count blank cells" vs "count non blank cells").
- Negation or reversed direction or relation ("erasers are cheaper than pens" vs "more expensive").
- A different task on the same material ("paraphrase the joke" vs "explain the joke"; "tax rates"
  vs "tax form").
- One query asks for strictly more or something more specific that an answer to the other would
  not give ("cheap flights from Denver to Las Vegas" vs "cheap flights to Las Vegas").
- An explicit output constraint present in one and not satisfiable by default by an answer to the
  other: language, length limit that differs, required format ("answer yes or no", "A/B/C"),
  number of items.
- A changed puzzle or problem setup, even slightly (boat capacity, counts, who is related to whom).

## Procedure

1. Pass 1: every pair is judged blind (no original label, no similarity score, no decider output),
   giving `same` / `different`, a confidence (`high` / `low`) and, for `different`, a short reason.
2. A label is a flip candidate when pass 1 disagrees with the original label with high confidence.
3. Pass 2: each flip candidate is judged again, blind, by a separate reviewer instance.
4. The label is changed only when pass 2 independently agrees with pass 1 with high confidence.
   Otherwise the original label stays. Unsure means no change.

Reviewer: Claude Opus 5.5 (`claude-opus-5-5`), an LLM; no human corrected these labels. A human
spot-check of a random sample of changed and unchanged labels is planned (README.md, "Human check").
