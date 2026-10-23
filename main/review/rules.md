# Review rules for "Deciding Without Generating" (v2)

v1 was 21 rules taken from reviewer guidelines and writing guides, plus the author's rules. Each v1 rule is sound
on its own, but applied together they compound. v2 is the result of checking every pair of rules for three
failure modes:

- **Repetition:** several rules ask for the same fact in different places. For example, A1, V1, R7 and R8 would
  put a gloss in the body, the caption and the next caption.
- **Overload:** stacked rules turn one sentence into a list of numbers. For example, R1, R2, R7 and R9 would give
  every comparison its CI, unit, N and magnitude.
- **Opposing pulls:** rules work against each other. R5 adds hedges while A4 and R10 remove vague words; A1 adds
  glosses while A1b forbids them; every addition competes with the page limit and with float placement.

v2 answers this with selection constraints that every change must pass, merged rules, and a single owner for
each whole-paper rule.

Scope tags:
- **LOCAL**: a section agent applies it to its own section.
- **GLOBAL**: one whole-paper agent applies it; section agents only report suspected violations.
- **VISUAL**: checked on rendered page screenshots.

Precedence: author rules (A) > selection constraints (S) > content rules (R) > layout rules (V).
Author rules still pass through S, so each change made for one is the smallest change that satisfies it.

## Selection constraints: a proposed change that fails any of these is dropped

- **S1 Necessity.** The change fixes a concrete violation of a named rule, and the report quotes the offending
  text. Changes of the kind "reads better" with no rule violated are not made.
- **S2 Length budget.** The main body currently ends on page 9, where the references start, and the MLSys limit
  is 10 pages. Net growth across the whole review stays under half a page. Where an addition can be paid for by a
  cut in the same paragraph, make the cut.
- **S3 Numbers.** No number changes unless it is checked against `results/` or `DECISIONS.md`. The report cites
  the source file for each changed number.
- **S4 Claim strength.** Wording that changes how strong a claim is changes only to fix an R1, R5 or R6
  violation.
- **S5 Say it once.** A definition, a disclosure or a CI appears in one place: the body or a caption. Everywhere
  else refers to it, for example "arms as in Table 3".

## Author rules

- **A1 Gloss what is specific to this paper, at first mention** (GLOBAL; owner: the terms agent).
  - Covers GSM-Plus, LMArena, SearchQueries, τ²-bench, vCache, RouterBench, APGR, Jev, Kev, the arms A–E and G.
  - A few words, at the first use in reading order. A reader must never need a citation to follow.
  - Captions do not repeat a gloss already given in the body (S5).
  - Section agents do not add glosses.
- **A1b Don't explain standard terms** (LOCAL). ECE, cross-encoders, NVML, cluster bootstrap, prefix caching,
  dev splits and similar get a name and, where useful, a citation.
- **A2 "Cost", not "dollars", in prose** (LOCAL). A `$` unit in tables is fine. In prose, reword `\$0.0016` as
  "a cost of …" where that is natural. "Price" means a vendor's list price only. A measured per-call amount is a
  cost, for example "48 times the price per decision" in the cache section.
- **A3 The label correction is a side finding** (GLOBAL; owner: the claims agent).
  - Not in the abstract or the contributions, and not in the intro's list of findings.
  - LMArena and SearchQueries are "two datasets released with vCache", never "the standard benchmarks".
  - The relabeling was done by Claude only. There is no human check: never write or imply one.
- **A4 Content, not vague words** (LOCAL; merges v1's A4 and R9).
  - A vague phrase ("a few bits", "some cases") is replaced by what it hides.
  - A magnitude word ("wide margin", "almost nothing", "far behind") has its number in the same sentence or the
    next one.
  - A superlative ("best", "only", "every") must hold against every decider listed in the table.
  - A bold lead-in may stay qualitative when the number follows in the next sentence.
- **A5 Jev is the representative decision model** (GLOBAL; owner: the claims agent). Every claim about "the
  decision model" means Jev. Kev appears only alongside Jev.

## Content rules

- **R1 Comparisons carry their interval where the result is reported** (LOCAL).
  - In results sections, a comparison between two deciders gives its paired 95% CI in the sentence or in the
    table it cites.
  - The abstract, intro, discussion and conclusion give headline numbers only, without repeating CIs (S5).
  - Everywhere, "tied" is used only if the CI contains 0, and "significant" or "at the edge of significance"
    must match the CI.
- **R2 Units and denominators** (LOCAL; merges v1's R2 and R7).
  - Accuracy differences are in points, not %.
  - Every cost, latency, energy or ratio says what it is per: decision, query, episode or success, and median or
    mean.
  - State this once per paragraph or in the table it comes from, not in every sentence.
  - N, the number of repeats and what the CI is computed over are stated once per table or figure, in the
    caption or in the section's setup (S5).
- **R3 One value per number** (GLOBAL; owner: the numbers agent).
  - Each headline number has the same value and rounding in the abstract, intro, body, tables, captions,
    discussion and conclusion.
  - Every number in the prose can be traced to a table cell or results file. Derived numbers (ratios,
    differences) are recomputed.
  - Rounding or precision changes (V5) are made by this agent across the whole paper at once, never by a
    section agent.
- **R4 One term per concept** (GLOBAL; owner: the terms agent).
  - Flag a synonym that is used without being equated to the term first used, and one term used for two
    things (for example "classifier" for both Jev and the trained baseline).
  - Deliberate distinctions stay, such as price (list price) vs cost (measured). Ask before merging two terms.
- **R5 Measured vs expected** (LOCAL).
  - A claim that goes beyond what was run (other decision points, other domains, newer router models, other
    Jev versions) or explains a mechanism without a measurement is worded as an expectation.
  - Measured results are stated plainly, without added hedges. Do not hedge to be safe.
- **R6 The abstract and contributions match the evidence** (GLOBAL; owner: the claims agent). Every claim in the
  abstract, the intro findings and the contributions maps to a section, table or figure, at the strength that
  evidence supports.
- **R7 Fairness disclosed once, where the comparison is first made** (LOCAL; v1's R8).
  - Rows that aren't like-for-like (vCache as a whole system, GPT-5.6 graded on its own trajectories, Kev
    over-length failures, crashed episodes counted as failures) are disclosed once, usually in the table caption.
  - Where the same comparison comes up again, refer back instead of repeating the disclosure.
- **R8 Paragraphs open with their point** (LOCAL; v1's R10, reduced).
  - The first sentence or bold lead-in states what the paragraph's numbers show and matches them.
  - Sentence-level reordering (main verb early, new information last) is used only on a sentence a reader would
    have to read twice. A citation at the end of a sentence is normal and not a violation.

## Layout rules (checked on page screenshots)

- **V1 Captions explain what the figure or table itself encodes.**
  - Its columns, symbols, marks (†, G, Δ), axes, the meaning of error bars, and which direction is better.
  - Terms defined in the body or in another caption are referenced, not repeated (S5).
  - There is no checklist that every caption must cover.
- **V2 Floats sit near their first reference, in order, and every float is referenced.** Flag a float more than
  one page after its first reference, or before it.
- **V3 Figures are readable at print size.**
  - Tick and legend text is no smaller than about the caption font.
  - Lines and markers can be told apart in grayscale.
  - Log axes are labeled as log.
  - The `\resultfig` trim leaves no leftover title strip and cuts nothing.
- **V4 Nothing runs into the margins or the gutter.** No section heading is stranded at the bottom of a column.
  Also check the `.log` for `Overfull \hbox` (> 1pt).
- **V5 Consistent number formatting.**
  - Within a table column and for the same quantity across tables: decimals, leading zeros (".744" vs "0.600"),
    the style of small costs, thousands separators, and placeholders.
  - This is reported by the visual agents and fixed by the numbers agent (R3).

## Who applies what

| Stage | Agent | Rules |
|---|---|---|
| 2 Structure and flow | 1 agent (whole paper and screenshots) | R6, R8 at section level, S2 |
| 3 Whole-paper checks | terms agent | A1, R4 |
|  | claims agent | A3, A5, R6 |
|  | numbers agent | R3, V5 (fixes) |
| 4 Per section | one agent per section (or merged short sections) | A1b, A2, A4, R1, R2, R5, R7, R8 |
| Every stage | visual agent (rebuild and screenshots) | V1–V5 |
| Every change | whoever applies it | S1–S5 |
