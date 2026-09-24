#!/usr/bin/env python3
"""Build DWG_Handoff_3.pdf — same hand-drawn-marker visual style as the uploaded
DWG_Handoff_2_Gilbreth.pdf, covering everything done since then: G1 execution (Kev-4B/9B
on Gilbreth, energy validated), the post-experiment rigor review, the cascade decider
(design, build, live results), and the Airline benchmark (dry run, the funding saga,
partial results, mock-vs-airline generalization verdict).

Every number below is taken verbatim from this session's actual tool outputs — nothing
here is invented or re-derived; only the layout/prose is new.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable,
)

pdfmetrics.registerFont(TTFont("Kalam", "/tmp/dwg_fonts/Kalam-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Kalam-Bold", "/tmp/dwg_fonts/Kalam-Bold.ttf"))
pdfmetrics.registerFont(TTFont("PatrickHand", "/tmp/dwg_fonts/PatrickHand-Regular.ttf"))

BG = colors.HexColor("#FBF8EF")
INK = colors.HexColor("#1A1A1A")
INK2 = colors.HexColor("#4A4A46")
YELLOW = colors.HexColor("#FCE8A8")
YELLOW_LINE = colors.HexColor("#E0B93A")
BLUE = colors.HexColor("#DCEBFA")
BLUE_LINE = colors.HexColor("#3E7CB1")
GREEN = colors.HexColor("#DDF0E4")
GREEN_LINE = colors.HexColor("#3E9B6F")
PINK = colors.HexColor("#FBE1E1")
PINK_LINE = colors.HexColor("#C1544B")
PURPLE = colors.HexColor("#EAE1F7")
PURPLE_LINE = colors.HexColor("#7D5FD6")
GRAY_LINE = colors.HexColor("#CFCABF")
CODE_BG = colors.HexColor("#F1EEE3")

PAGE_W, PAGE_H = LETTER


def page_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFont("PatrickHand", 8.5)
    canvas.setFillColor(INK2)
    canvas.drawString(0.6 * inch, 0.4 * inch, "DWG handoff #3 · continuing from handoff #2 (Gilbreth track)")
    canvas.drawRightString(PAGE_W - 0.6 * inch, 0.4 * inch, f"page {doc.page}")
    canvas.restoreState()


styles = {
    "title": ParagraphStyle("title", fontName="Kalam-Bold", fontSize=30, leading=34, textColor=INK, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", fontName="PatrickHand", fontSize=12.5, leading=17, textColor=INK2, spaceAfter=10),
    "kicker": ParagraphStyle("kicker", fontName="PatrickHand", fontSize=10.5, leading=14, textColor=INK2),
    "h1": ParagraphStyle("h1", fontName="Kalam-Bold", fontSize=19, leading=23, textColor=INK, spaceBefore=18, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Kalam-Bold", fontSize=13.5, leading=17, textColor=INK, spaceBefore=4, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="PatrickHand", fontSize=11, leading=15.5, textColor=INK, spaceAfter=6),
    "bodysmall": ParagraphStyle("bodysmall", fontName="PatrickHand", fontSize=9.7, leading=13.5, textColor=INK2, spaceAfter=4),
    "bullet": ParagraphStyle("bullet", fontName="PatrickHand", fontSize=10.7, leading=15, textColor=INK, leftIndent=14, spaceAfter=4, bulletIndent=2),
    "boxh": ParagraphStyle("boxh", fontName="Kalam-Bold", fontSize=13, leading=16, textColor=INK, spaceAfter=3),
    "boxbody": ParagraphStyle("boxbody", fontName="PatrickHand", fontSize=10, leading=14, textColor=INK),
    "tablehdr": ParagraphStyle("tablehdr", fontName="Kalam-Bold", fontSize=9.3, leading=11.5, textColor=INK),
    "tablecell": ParagraphStyle("tablecell", fontName="PatrickHand", fontSize=9.3, leading=12, textColor=INK),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=8.3, leading=11.5, textColor=INK, backColor=CODE_BG),
}


def box(flowables, fill, line, pad=10):
    t = Table([[flowables]], colWidths=[6.9 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 1.1, line),
        ("LEFTPADDING", (0, 0), (-1, -1), pad), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def para(text, style="body"):
    return Paragraph(text, styles[style])


def bullets(items, style="bullet"):
    return [Paragraph(f"• {i}", styles[style]) for i in items]


def data_table(header, rows, widths=None, small=True):
    style_hdr = "tablehdr"
    style_cell = "tablecell"
    data = [[Paragraph(h, styles[style_hdr]) for h in header]]
    for r in rows:
        data.append([Paragraph(str(c), styles[style_cell]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE9D8")),
        ("GRID", (0, 0), (-1, -1), 0.6, GRAY_LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


story = []

# ---------------------------------------------------------------- Page 1: cover + TL;DR
story.append(para("Deciding Without Generating · handoff #3 · 2026-09-24", "kicker"))
story.append(Spacer(1, 2))
story.append(para("Handoff #3: G1, the cascade, and Airline", "title"))
story.append(para(
    "Everything since handoff #2 (commit <code>3130cb1</code>): Kev-4B/9B run for real on Gilbreth, "
    "a rigorous statistical audit, a live confidence-gated cascade decider, and a first (partial) "
    "run on the real Airline domain — including the funding wall we hit and what it taught us.",
    "subtitle"))

tldr_items = [
    "<b>G1 ran clean.</b> Kev-4B and Kev-9B replayed on the mock pilot with real, validated GPU energy — no fabricated numbers, one live SLURM bug found and fixed (<font face=\"Courier\" size=9>--exclusive</font> was silently grabbing both GPUs on a shared node).",
    "<b>A paired-bootstrap audit found the mock pilot's headline claim was overstated.</b> “Kev-4B ≈ Kev-9B” survived the test (not significant, CI touches 0) — but that null result turned out to be a mock-only artifact.",
    "<b>Built a live confidence-gated cascade</b> (Kev-4B → GPT-OSS-20B, threshold 0.9): +8.3pts over Kev-4B alone, not yet significant at n=65, real API errors handled and resumed cleanly.",
    "<b>Airline broke the mock-only story.</b> On 662 real Airline states, Kev-4B vs Kev-9B <b>reverses and becomes significant</b> (−12.2pts, p&lt;0.05) — the opposite of mock. Both models' accuracy collapses on Airline (Kev-4B 61.5%→28.9%, Kev-9B 63.1%→41.1%, both significant).",
    "<b>Ran out of real money mid-collection.</b> OpenRouter account hit $0 (of $5) after two real bugs — a 20 req/min new-account cap, then an uncapped 65536-token credit pre-check — both diagnosed and fixed, but Airline coverage stopped at 70% (105/150 episodes; tasks 38–49 have zero episodes). Jev, GPT-OSS-20B and the cascade on Airline are blocked until credits are added.",
]
story.append(box([para("TL;DR", "boxh")] + bullets(tldr_items, "boxbody"), YELLOW, YELLOW_LINE))
story.append(Spacer(1, 12))

story.append(para("Your first 5 minutes", "h2"))
story.append(box([Paragraph(
    'git pull  &nbsp;&nbsp;<font color="#8a8578"># gets the cascade code, the airline states/results, this PDF</font><br/>'
    'less results/replay/mock-pilot/post_experiment_analysis.json  <font color="#8a8578"># the significance tests</font><br/>'
    'less results/replay/airline/report/summary.md  &nbsp;&nbsp;<font color="#8a8578"># Kev-4B/9B on real Airline data</font><br/>'
    'less results/replay/compare-mock-pilot-vs-airline/comparison.md  <font color="#8a8578"># mock vs airline, side by side</font>',
    styles["code"])], CODE_BG, GRAY_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 2: G1 execution
story.append(para("1 · G1: Kev-4B and Kev-9B, for real, on Gilbreth", "h1"))
story.append(para(
    "Ran the two Slurm replay jobs the handoff #2 asked for, against the same 65-state mock pilot. "
    "Both completed with <b>validated</b> GPU energy (no <font face=\"Courier\" size=9>!! GPU energy not measured</font> "
    "anywhere in either log) and clean data — 325/325 calls each, 0 errors, prefix cache confirmed off.", "body"))

story.append(data_table(
    ["Decider", "Accuracy [95% CI]", "p50 / p95 latency", "J / decision (gross / net)"],
    [
        ["Jev (API)", "0.772 [0.668, 0.868]", "0.374 / 0.510 s", "n/a (hosted)"],
        ["GPT-OSS-20B (API)", "0.852 [0.778, 0.917]", "0.873 / 1.737 s", "n/a (hosted)"],
        ["Kev-0.8B (laptop)", "0.354 [0.246, 0.477]", "0.131 / 0.182 s", "not measured (invalid counter)"],
        ["Kev-4B (A100)", "0.615 [0.492, 0.738]", "0.086 / 0.101 s", "18.33 / 11.95"],
        ["Kev-9B (A100)", "0.631 [0.508, 0.754]", "0.093 / 0.120 s", "24.44 / 17.93"],
    ],
    widths=[1.55 * inch, 1.75 * inch, 1.55 * inch, 2.05 * inch],
))
story.append(Spacer(1, 10))

story.append(para("A real SLURM bug, found live", "h2"))
story.append(box([
    para(
        "<font face=\"Courier\" size=9>--exclusive</font> in <font face=\"Courier\" size=9>kev_replay.slurm</font> "
        "reserves every GPU on the node, not just the one requested — a 2-GPU node handed both cards to a job "
        "that asked for 1, burning 2 of the account's 3-GPU group cap and starving a labmate's queued job. "
        "Fixed: dropped <font face=\"Courier\" size=9>--exclusive</font>, kept <font face=\"Courier\" size=9>--gres=gpu:1</font> "
        "(SLURM's cgroup isolation already gives sole ownership of the one GPU, which is all the energy counter needs). "
        "Kev-9B's first attempt also OOM'd at <font face=\"Courier\" size=9>--mem=32G</font> (needs ~48G in fp32-before-cast); "
        "fixed by requesting 96G.",
        "boxbody"),
], PINK, PINK_LINE))

story.append(Spacer(1, 10))
story.append(para(
    "Full validation pass on the run: row counts match expected exactly (65 states × 5 repeats), "
    "no warmup-call leakage into the logged data, no cache contamination, no silently-skipped states.", "body"))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 3: rigor review
story.append(para("2 · The rigor pass: what actually holds up", "h1"))
story.append(para(
    "Built <font face=\"Courier\" size=9>post_experiment_analysis.py</font> — paired cluster-bootstrap "
    "significance tests, data-integrity checks, per-state cross-tabs, post-hoc calibration, and a cascade "
    "simulation — all computed from the raw <font face=\"Courier\" size=9>calls-*.jsonl</font>, not eyeballed "
    "off the summary tables.", "body"))

story.append(para("Significance, not just overlap", "h2"))
story.append(data_table(
    ["Comparison (mock, n=65 states)", "Diff", "95% CI", "Significant?"],
    [
        ["Kev-4B vs Kev-9B", "−1.5 pts", "[−4.6, +0.0]", "No"],
        ["Jev vs Kev-9B", "+14.2 pts", "[−1.5, +29.5]", "No (!)"],
        ["Jev vs GPT-OSS-20B", "−8.0 pts", "[−14.8, −1.8]", "Yes"],
    ],
    widths=[2.6 * inch, 1.2 * inch, 1.6 * inch, 1.5 * inch],
))
story.append(para(
    "The eye-catching “Jev beats Kev-9B by 14 points” framing from the pilot report does <b>not</b> "
    "survive a paired test at n=65 — direction is right, significance isn't there yet. Needs ~10× more "
    "states to nail down at ±5pt precision.", "bodysmall"))

story.append(Spacer(1, 8))
story.append(para("Calibration: temperature scaling actually works for Kev", "h2"))
story.append(data_table(
    ["Decider", "ECE before", "ECE after (held-out)", "Fitted T"],
    [
        ["Jev", "0.109", "0.148 (worse)", "0.7–1.6"],
        ["GPT-OSS-20B", "0.111", "0.057", "1.8–2.2"],
        ["Kev-4B", "0.307", "0.059", "5.5–6.0"],
        ["Kev-9B", "0.321", "0.080", "5.0–5.2"],
    ],
    widths=[1.5 * inch, 1.3 * inch, 1.8 * inch, 1.6 * inch],
))
story.append(para(
    "2-fold, state-level split (fit on one half, score on the other) — not graded on its own training data. "
    "Kev's confidence is dramatically overconfident and a single scalar fixes most of it; Jev is already well "
    "calibrated and scaling makes it slightly worse (its reliability curve isn't monotonic).", "bodysmall"))

story.append(Spacer(1, 8))
story.append(para("Error analysis: the same failure mode, at every Kev size", "h2"))
story.append(box([para(
    "<b>Kev-4B beats Kev-9B: 0 states. Kev-9B beats Kev-4B: 1 state.</b> Scaling 4B→9B unlocks essentially "
    "nothing state-by-state on mock — the clearest possible confirmation that the null result above is real, "
    "not just noise. <b>Jev beats both Kev models on 19 states</b>, clustered in tasks where Kev redundantly "
    "re-acts (<font face=\"Courier\" size=9>update_task_status</font>) after the task is already done — the "
    "exact same “called tool instead of replying” pattern flagged for Kev-0.8B in handoff #2, still present "
    "at 4B and 9B, just less often.", "boxbody"),
], BLUE, BLUE_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 4: cascade
story.append(para("3 · The cascade: built live, not just simulated", "h1"))
story.append(para(
    "Kev-4B decides first; below a confidence threshold, escalates to GPT-OSS-20B. Reuses the existing "
    "<font face=\"Courier\" size=9>Decider</font> interface (<font face=\"Courier\" size=9>CascadeDecider</font> "
    "works with any two deciders, not just this pair) — 3 new unit tests, all 29 project tests pass.", "body"))

story.append(para("One deliberate design call", "h2"))
story.append(box([para(
    "No live GPU energy metering on the cascade run itself. Wrapping the whole "
    "<font face=\"Courier\" size=9>decide()</font> call (Kev stage + a possibly multi-second network escalation) "
    "in the same NVML window used for pure-Kev runs would count the GPU's idle power during that wait as "
    "“decision energy.” Kev-4B's own validated 18.33 J/decision is reused post-hoc instead.", "boxbody"),
], PURPLE, PURPLE_LINE))

story.append(Spacer(1, 8))
story.append(para("Threshold sweep (simulated from replayed calls) → live run at t=0.9", "h2"))
story.append(para(
    "Pareto-optimal thresholds: 0.0, 0.5, 0.6, 0.9, 0.95, 1.0 (full escalation). Two different “optimal” "
    "answers depending on what you weight: the algorithmic pick (min distance-to-utopia) is <b>t=0.6</b> "
    "(conservative, +1.8pts, barely escalates); the best accuracy-for-cost trade — what actually got run live — "
    "is <b>t=0.9</b>.", "body"))

story.append(data_table(
    ["Decider (mock, n=65)", "Accuracy", "95% CI", "Median lat.", "p95 lat."],
    [
        ["Kev-4B", "61.5%", "[49.2, 73.8]", "86.0 ms", "100.6 ms"],
        ["Kev-9B", "63.1%", "[50.8, 75.4]", "92.8 ms", "120.0 ms"],
        ["Cascade (t=0.9, live)", "69.8%", "[59.1, 79.7]", "249.2 ms", "2004.8 ms"],
        ["Jev", "77.2%", "[66.8, 86.8]", "373.8 ms", "510.2 ms"],
        ["GPT-OSS-20B", "85.2%", "[77.8, 91.7]", "872.8 ms", "1736.6 ms"],
    ],
    widths=[1.9 * inch, 1.1 * inch, 1.5 * inch, 1.2 * inch, 1.2 * inch],
))
story.append(Spacer(1, 8))

story.append(para("Honest headline: the live gain isn't proven yet", "h2"))
story.append(box([para(
    "The live cascade's +8.3pt gain over Kev-4B alone does <b>not</b> clear significance at n=65 "
    "(diff +8.3pts, CI [−1.5, +18.5]). Only cascade-vs-GPT-OSS-20B is significant (cascade is still worse, "
    "as expected — diff −15.4pts, CI [−25.8, −4.9]). Two real API errors hit during the live run "
    "(OpenRouter occasionally returns no tool call for GPT-OSS-20B) — same pre-existing flakiness seen before, "
    "resumed cleanly to 325/325 clean rows.", "boxbody"),
], PINK, PINK_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 5: airline saga
story.append(para("4 · Airline: the funding saga", "h1"))
story.append(para(
    "Domain verified clean first (50/50 tasks, 14 tools, policy + eval fields all load). Model chosen: "
    "<font face=\"Courier\" size=9>openrouter/openai/gpt-5.6</font>. Dry run (5 tasks × 3 trials) succeeded "
    "15/15, $0.30 total — but that clean result turned out to be <b>not representative</b> of the full run.", "body"))

story.append(para("Three real bugs, each one diagnosed live from the actual error, not guessed", "h2"))
story.append(box([
    para("<b>1. OpenRouter 20 req/min new-account cap.</b>", "boxbody"),
    para(
        "First attempt (unthrottled, 4 workers): all 15 episodes failed. tau2's own 3-retry default can't "
        "outlast a hard per-minute quota under concurrent load. Fixed: a rate limiter monkey-patching the exact "
        "bound name tau2 uses internally (<font face=\"Courier\" size=9>tau2.utils.llm_utils.completion</font> — "
        "patching <font face=\"Courier\" size=9>litellm.completion</font> itself would NOT have worked, tau2 already "
        "copied the reference at import time).", "boxbody"),
    Spacer(1, 4),
    para("<b>2. Sustained load still degraded — 32% of the full 150-episode run failed (48 episodes),</b> "
         "concentrated as a solid failed tail (tasks 38–49, 12 tasks with ZERO episodes, not scattered noise).", "boxbody"),
    Spacer(1, 4),
    para("<b>3. Root cause: <font face=\"Courier\" size=9>max_tokens</font> was uncapped at 65536</b> (the model's "
         "own ceiling). OpenRouter pre-authorizes credits against that worst case on every call, before any tokens "
         "are generated or billed — <i>“you requested up to 65536 tokens, but can only afford 32405.”</i> "
         "Fixed with a max_tokens cap (4096) — the same monkeypatch mechanism as the rate limiter.", "boxbody"),
], BLUE, BLUE_LINE))

story.append(Spacer(1, 8))
story.append(box([para(
    "<b>The fix worked, but the account ran out of real money before the retry finished.</b> "
    "Balance check via OpenRouter's own <font face=\"Courier\" size=9>/credits</font> API: <b>$5.00 total, "
    "$5.00 used, $0 remaining.</b> Confirmed, not inferred. Every further OpenRouter call — including Jev, "
    "GPT-OSS-20B, and the cascade's escalation stage — is blocked until credits are added.", "boxbody"),
], PINK, PINK_LINE))

story.append(Spacer(1, 8))
story.append(para("What's actually usable right now", "h2"))
story.append(data_table(
    ["Metric", "Value"],
    [
        ["States collected (merged across all attempts)", "1,065"],
        ["Episodes covered", "105 / 150 (70%)"],
        ["Episodes with reward=1 (usable for replay labels)", "77"],
        ["Usable states for replay", "689"],
        ["Tasks with ZERO episodes", "38–49 (12 tasks)"],
    ],
    widths=[4.3 * inch, 2.6 * inch],
))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 6: airline results
story.append(para("5 · Airline results: does mock generalize? No.", "h1"))
story.append(para(
    "Kev-4B and Kev-9B replayed on all 689 usable Airline states (5 repeats each) — real, validated GPU energy "
    "again. 135/3445 calls per decider hit Kev's genuine 8192-token context limit on the longest Airline "
    "conversations (correctly excluded from accuracy, not silently dropped, and identical across both models "
    "since it's state-length-driven, not model-specific).", "body"))

story.append(para("Finding 1: the mock “no benefit from scaling” conclusion reverses", "h2"))
story.append(data_table(
    ["Comparison (Airline, n=662 states)", "Diff", "95% CI", "Significant?"],
    [["Kev-4B vs Kev-9B", "−12.2 pts", "[−15.6, −8.9]", "YES"]],
    widths=[2.9 * inch, 1.2 * inch, 1.7 * inch, 1.1 * inch],
))
story.append(para(
    "Kev-9B wins 108 states to Kev-4B's 27 (4:1). On mock this same comparison was <i>not</i> significant "
    "(CI touched 0). Airline — harder domain, far more data — reveals scaling really does help; mock was too "
    "small/easy to see it.", "bodysmall"))

story.append(Spacer(1, 8))
story.append(para("Finding 2: absolute accuracy collapses on the harder domain", "h2"))
story.append(data_table(
    ["Decider", "Mock acc.", "Airline acc.", "Diff", "95% CI", "Sig?"],
    [
        ["Kev-4B", "61.5%", "28.9%", "+32.7 pts", "[+20.0, +44.8]", "YES"],
        ["Kev-9B", "63.1%", "41.1%", "+22.0 pts", "[+9.2, +34.1]", "YES"],
    ],
    widths=[1.0 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch, 1.5 * inch, 0.7 * inch],
))
story.append(para(
    "Independent-sample bootstrap (different state universes, not paired). Mock's 5-tool toy domain was "
    "not predictive of real tool-selection difficulty at 14-tool scale with much longer contexts "
    "(3,099 vs 430 median input tokens).", "bodysmall"))

story.append(Spacer(1, 8))
story.append(para("Finding 3: a whole new failure mode appears", "h2"))
story.append(box([para(
    "<b>“Repeated tool call”</b> goes from nearly negligible on mock (1 instance total) to a major error "
    "category on Airline. Longer, multi-turn Airline conversations (up to 14 turns) create many more chances "
    "for Kev to redundantly re-invoke a tool it already called — a failure mode mock's short conversations "
    "structurally couldn't expose.", "boxbody"),
], GREEN, GREEN_LINE))

story.append(Spacer(1, 10))
story.append(box([para(
    "<b>Bottom line:</b> any paper claim built only on the mock pilot needs an explicit Airline (or harder-domain) "
    "caveat — especially “no benefit from scaling Kev,” which Airline actively contradicts. The energy/latency "
    "story (Kev-4B faster & lower-energy than Kev-9B) likely still holds directionally, but now trades against a "
    "real, significant accuracy cost mock hid. <b>Unresolved:</b> whether Jev and the cascade show the same "
    "generalization gap — needs OpenRouter funding to test.", "boxbody"),
], YELLOW, YELLOW_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 7: next steps
story.append(para("6 · What's next", "h1"))

story.append(para("Blocked on you", "h2"))
story.append(box([
    para("<b>Add OpenRouter credits</b> to unblock: the remaining 45 Airline episodes (tasks 38–49), "
         "plus Jev / GPT-OSS-20B / cascade replay on Airline — all currently impossible at $0 balance.", "boxbody"),
], PINK, PINK_LINE))

story.append(Spacer(1, 8))
story.append(para("Ready to run the moment funding lands", "h2"))
story.extend(bullets([
    "Complete Airline state collection for tasks 38–49 (script already fixed: rate-limited + max_tokens-capped).",
    "Replay Jev, GPT-OSS-20B, and the cascade (t=0.9) on the 689 (soon ~1,000+) Airline states.",
    "Extend the significance/comparison scripts (already airline-ready, crash-fixed for missing deciders) to the full 5-decider + cascade picture.",
    "Test whether the cascade's generalization gap matches Kev-4B/9B's — the paper's core mechanism, still unverified past mock.",
], "bullet"))

story.append(Spacer(1, 10))
story.append(para("New files this handoff", "h2"))
story.append(box([Paragraph(
    "src/dwg/decisions.py &nbsp;<font color=\"#8a8578\"># + CascadeDecider, Decision.escalated</font><br/>"
    "scripts/kev_cascade_replay.slurm, scripts/make_cascade_figure.py<br/>"
    "scripts/post_experiment_analysis.py &nbsp;<font color=\"#8a8578\"># significance, calibration, cascade sim</font><br/>"
    "scripts/make_paper_figures.py, scripts/montage_figures.py, scripts/compare_domains.py<br/>"
    "scripts/collect_decision_states.py &nbsp;<font color=\"#8a8578\"># + rate_limit_tau2_llm_calls, cap_max_tokens</font><br/>"
    "results/replay/{mock-pilot,airline}/paper_figures/, post_experiment_analysis.json<br/>"
    "results/replay/compare-mock-pilot-vs-airline/<br/>"
    "results/states/airline.jsonl &nbsp;<font color=\"#8a8578\"># 1,065 states, 105/150 episodes</font>",
    styles["code"])], CODE_BG, GRAY_LINE))

story.append(Spacer(1, 10))
story.append(para("Gotchas we hit this round", "h2"))
story.extend(bullets([
    "SLURM --exclusive on a shared multi-GPU node silently grabs every GPU, not just the one requested — check AllocTRES, not just your own --gres request.",
    "Gilbreth now requires an explicit --mem on every job (policy change since handoff #2's scripts were written).",
    "OpenRouter's credit pre-check is against max_tokens requested, not actual usage — always cap it explicitly for cost-sensitive collection runs.",
    "tau2 binds `from litellm import completion` at import time — patch tau2.utils.llm_utils.completion, not litellm.completion, or your monkeypatch silently does nothing.",
], "bullet"))

doc = SimpleDocTemplate(
    "/home/aelmersa/Deciding-Without-Generating/DWG_Handoff_3.pdf",
    pagesize=LETTER,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    topMargin=0.7 * inch, bottomMargin=0.65 * inch,
    title="DWG Handoff 3",
)
doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print("wrote DWG_Handoff_3.pdf")
