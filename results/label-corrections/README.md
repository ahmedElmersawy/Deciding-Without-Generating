# Cache-guard label corrections (vCache benchmarks)

What we changed in third-party labels, how, and by whom. Everything here is meant to be stated
in the paper (DECISIONS.md 2026-10-07).

## Source

- **SemBenchmarkLmArena** (`vCache/SemBenchmarkLmArena` on Hugging Face, Apache-2.0). 3,500 prompts
  sampled from the LM-Arena human-preference data; GPT-4.1-nano generated 1–23 "semantically
  similar variants" of each, ~60k prompts; a prompt's class (`ID_Set`) is the original it was
  generated from.
- **SemBenchmarkSearchQueries** (`vCache/SemBenchmarkSearchQueries`, Apache-2.0). 500k real search
  queries from ORCAS, embedded with gte-large-en-v1.5, k-means clustered (largest clusters kept,
  150k queries); within a cluster, a union-find guided by a GPT-4.1-nano judge of "do these two
  queries yield the same response" defines the class (`id_set`).
- Both released with: L. G. Schroeder, A. Desai, A. Cuadron, K. Chu, S. Liu, M. Zhao, S. Krusche,
  A. Kemper, M. Zaharia, J. E. Gonzalez. *vCache: Verified Semantic Prompt Caching.* ICLR 2026,
  arXiv:2502.03771. Also cite LM-Arena / Chatbot Arena (Chiang et al., 2024) and ORCAS
  (Craswell et al., 2020) as the underlying query sources.

Our cache-guard pair is (query, its nearest earlier prompt by GTE cosine); vCache's rule makes
reuse correct iff both share a class. LmArena prompts are stored as in the dataset (a few are cut
at ~600 characters there); deciders and reviewers saw the same text.

## How we found the problem

Every decider, the frontier GPT-5.6 included, topped out at 70–72% accuracy on SearchQueries and
LmArena, while the same deciders reached 93–97% on GSM-Plus, whose labels are exact numeric
answers we computed. A frontier model failing an easy "are these the same request?" question
pointed at the labels. We took the test pairs where the majority of Jev, GPT-5.6 and GPT-OSS-20B
disagreed with the label (SearchQueries 563 / 2,000, LmArena 496 / 2,000) and read random samples
of each direction:

- SearchQueries: about 3 in 4 sampled "different" labels and 2 in 5 sampled "same" labels were
  plainly wrong ("best workout plans for women" vs "best workout plan for women" labelled
  different; "count blank cells" vs "count non blank cells" labelled same).
- LmArena: 37 of 2,600 pairs had identical prompts yet were labelled "different", and some "same"
  labels joined a question with a changed version of it.
- The same reading surfaced a second, separate problem in our own setup (DECISIONS.md 2026-10-07):
  the old cache-guard question asked deciders to check the cached answer, and GPT-5.6 regenerated
  on 24% of identical-prompt LmArena pairs because it judged the stored answer wrong. That is fixed
  by isolating the decision to the two queries, not by relabelling.

## Why vCache's labelling method produces these errors

vCache does not judge the pairs a cache meets; it assigns each query a class and declares any two
queries in the same class a correct hit. Each dataset builds its classes differently, and each
way breaks for a reason.

**SearchQueries: transitive closure over pairwise LLM judgements.** Within each embedding cluster,
GPT-4.1-nano judges pairs ("do these two queries yield the same response?") and union-find merges
every judged-same pair into one class. Classes are therefore transitive closures: if A ~ B and
B ~ C, then A ~ C, though A and C may never have been compared. That is only valid if "same" is a
strict equivalence, and in practice it is not:

1. *Answers are specific to the query that produced them.* A cache serves the stored answer of the
   query it matched, written for that query's details. With B = "best workout plan",
   A = "best workout plan for women", C = "best workout plan for men", a tolerant judge can accept
   A ~ B and C ~ B (a general plan roughly serves both), but A's stored answer is a women's plan and
   is wrong for C. Two tolerable links do not compose into a correct third one.
2. *Tolerance accumulates along chains.* Each judgement allows a small difference, and the
   differences add up: a chain such as "count blank cells" ~ "count cells" ~ "count non blank
   cells" joins two queries that ask opposite things, though each neighbouring pair looks close.
   (This chain illustrates the mechanism; we did not trace this exact path through vCache's
   union-find, which is not released pair by pair.)
3. *One wrong link merges whole classes.* Union-find joins entire classes, so a single mistaken
   judgement between one member of class X and one member of class Y makes every member of X
   "same" as every member of Y, including pairs no model ever looked at. Errors are amplified, not
   just copied.

The reverse errors (true duplicates labelled different) come from the same construction: two
queries end up in different classes whenever the judge missed every link between their classes,
or they fell into different k-means clusters and were never compared at all.

**LmArena: class = "generated from the same seed".** GPT-4.1-nano wrote 1–23 "semantically similar
variants" of each seed prompt, and every variant inherits the seed's class without any check that
it still asks the same thing. Generation sometimes changed the question (a reversed premise,
"SY0-501" turned into "SY0-701", "count the Rs" turned into "count 'rs'", a puzzle's numbers
changed), yet the variant stays "same". Conversely, different seeds can yield near-identical or
identical variants (popular puzzles and instructions recur across LM-Arena), which land in
different classes and are labelled "different".

## How our labelling corrects the method

- **Judge the pair the cache actually meets, directly.** A label is a judgement of (new query,
  the cached query it would be served from), made from those two queries. No label is inferred
  from another label, so there is no transitivity and no error propagation between pairs. This
  matches how the cache works: it never serves a class, only one stored entry.
- **Strict, written definition of "same request"** (`GUIDELINE.md`), fixed before any review:
  rewording is same; any change of entity, number, direction, task, scope or explicit output
  constraint is different. A strict definition is close to a true equivalence, so it does not
  drift the way a tolerant "similar enough" judgement does.
- **Blind, every pair, two passes, change only on agreement.** Pass 1 judged all 5,200 pairs
  without seeing the vCache label, the similarity or any decider's output; a separate blind pass 2
  re-judged every high-confidence disagreement; a label changed only when both agreed at high
  confidence. Reviewing every pair rather than only decider disagreements keeps the correction
  from steering toward any decider.
- **Traceable.** The vCache label is kept next to the corrected one, and each change records both
  passes' reasons and the corrector.

## What we did

1. **Guideline first.** `GUIDELINE.md`, written before any pair was reviewed, defines a correct
   cache hit from the two queries alone (no cached answer, no time-sensitivity: see DECISIONS.md
   2026-10-07).
2. **Pass 1, every pair, blind.** All 2,600 dev + test pairs of each dataset (5,200 total) were
   judged by Claude Opus 5.5 (`claude-opus-5-5`) instances that saw only the two queries: not the
   vCache label, not the similarity, not any decider's output. Output: `<dataset>-pass1.jsonl`.
3. **Pass 2, blind, on flip candidates.** A pair whose high-confidence pass-1 verdict disagreed
   with the vCache label was judged again by a separate Opus 5.5 instance, also blind.
   Output: `<dataset>-pass2.jsonl`.
4. **Change only on agreement.** A label changes only when pass 2 independently agrees with
   pass 1 at high confidence; low confidence anywhere keeps the vCache label.
   `scripts/apply_cacheguard_label_corrections.py` applies this to the streams.

**Who corrected:** an LLM (Claude Opus 5.5), not a human. No label was changed by hand. Reviewing
every pair blind (not only the pairs where our deciders disagreed with the label) keeps the
correction from being steered toward any decider; but the corrector is itself a frontier LLM, so
corrected labels may agree more with LLM deciders' notion of "same request" than human labels
would. A human spot-check of a random sample of changed and unchanged pairs is the planned
safeguard (see "Human check" below).

## Provenance in the data

- `results/states/cacheguard-<dataset>.jsonl`: `reuse_correct` is the label used everywhere;
  `reuse_correct_original` is vCache's; `label_source` is `vcache` or `corrected:claude-opus-5-5`.
- `<dataset>-corrections.jsonl`: one row per changed label, with both queries, both labels, both
  passes' reasons, `corrected_by`, `human_checked`.
- `.meta.json` of each stream: counts under `label_corrections`, base rates before and after.
- GSM-Plus labels are exact numeric answers we computed ourselves and are not corrected.

## Results

| dataset | pairs reviewed | flip candidates (pass 1) | changed (both passes agree) | → reuse | → regenerate |
|---|---|---|---|---|---|
| LmArena | 2,600 | 174 | 156 (6.0%) | 122 | 34 |
| SearchQueries | 2,600 | 465 | 409 (15.7%) | 267 | 142 |

All 37 LmArena pairs whose two prompts are identical (after stripping quotes and punctuation)
but carried a "regenerate" label are now "reuse".

## Examples of wrong vCache labels (corrected)

LmArena, labelled *same* by vCache, corrected to *different*:
- "Pens are more expensive than pencils. **Erasers are cheaper than pens.** … is 'Erasers are more
  expensive than pencils and pens' true?" vs "… **Erasers are more expensive than pens.** …"
  (premise reversed, the answer flips).
- "What topics are covered on the CompTIA Security+ **SY0-501** exam?" vs "… **SY0-701** exam?"
- "How many times does the letter combination **"rs"** occur in 'raspberry' …?" vs "How many
  **Rs** are in 'raspberry' …?"
- "Two days after the day before tomorrow is Wednesday. What day was it eight days ago?" vs "If
  the day after the day after tomorrow is a Wednesday, what day was it a week ago?"

LmArena, labelled *different* by vCache, corrected to *same*:
- "If Jennifer has 5 brothers and 1 sister, how many sisters will one of Jennifer's brothers
  have?" vs the identical prompt.
- "What are the top 2 pre-workout ingredients excluding caffeine and creatine, in 50 characters or
  less?" vs "Name the top 2 pre-workout ingredients excluding caffeine and creatine, in 50 characters
  or less."

SearchQueries, labelled *same* by vCache, corrected to *different*:
- "excel formula to count blank cells" vs "excel formula to count non blank cells"
- "block calls on cell phone" vs "block cell phone number when calling"
- "does thyroid cause weight gain" vs "can thyroid medication cause weight gain"

SearchQueries, labelled *different* by vCache, corrected to *same*:
- "credit one bank customer service number" vs "credit one bank customer service phone number"
- "cpt code for i and d abscess" vs "cpt code for i&d of abscess"
- "eglin federal credit union login" vs "eglin fed credit union login"

## Effect (preview, old answer-reading decider runs)

Test accuracy against vCache labels → corrected labels. SearchQueries: Jev 0.713 → 0.836, GPT-5.6
0.710 → 0.829, GPT-OSS-20B 0.717 → 0.822, Kev-4B 0.707 → 0.844, Qwen3-8B 0.721 → 0.835.
LmArena: Jev 0.712 → 0.747, GPT-5.6 0.706 → 0.724 (the rest of LmArena's gap was the old
question grading the stored answers; re-run with the query-only question pending).

## Human check

Not done yet. Plan: a human labels a random sample (e.g. 50 changed, 50 unchanged pairs per
dataset) blind to both labels; report agreement with the corrected and with the original labels.
