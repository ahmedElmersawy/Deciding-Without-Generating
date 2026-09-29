#!/usr/bin/env python3
"""Build DWG_Handoff_4.pdf in the same hand-drawn-marker style as DWG_Handoff_3.pdf, covering
everything since handoff #3 (commit 4b82f58): the airline arm-0 sweep finished for every
decider we can afford, a round of accounting fixes (spending guard, infra vs. decider errors,
pooled energy, cascade $ and J), and the first in-loop run (arms B/C/E, all local).

Numbers are copied from results/replay/airline/report/summary.md,
results/replay/airline/post_experiment_analysis.json,
results/inloop/airline-local-qwen3-8b/report/summary.md and DECISIONS.md.

Fonts (Kalam, Patrick Hand; OFL, from github.com/google/fonts) are read from $DWG_FONT_DIR,
default /tmp/dwg_fonts.
"""

import os

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

FONT_DIR = os.environ.get("DWG_FONT_DIR", "/tmp/dwg_fonts")
pdfmetrics.registerFont(TTFont("Kalam", FONT_DIR + "/Kalam-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Kalam-Bold", FONT_DIR + "/Kalam-Bold.ttf"))
pdfmetrics.registerFont(TTFont("PatrickHand", FONT_DIR + "/PatrickHand-Regular.ttf"))

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
    canvas.drawString(0.6 * inch, 0.4 * inch, "DWG handoff #4 · continuing from handoff #3 (commit 4b82f58)")
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


def status_grid(header, rows, widths):
    """Like data_table, but a cell starting with DONE / PART / TODO gets a green / yellow / pink fill."""
    fills = {"DONE": (GREEN, GREEN_LINE), "PART": (YELLOW, YELLOW_LINE), "TODO": (PINK, PINK_LINE)}
    data = [[Paragraph(h, styles["tablehdr"]) for h in header]]
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE9D8")),
        ("GRID", (0, 0), (-1, -1), 0.6, GRAY_LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for ri, r in enumerate(rows, start=1):
        data.append([Paragraph(str(c), styles["tablecell"]) for c in r])
        for ci, c in enumerate(r):
            key = str(c).split(" ")[0].replace("<b>", "").replace("</b>", "")
            if key in fills:
                cmds.append(("BACKGROUND", (ci, ri), (ci, ri), fills[key][0]))
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(cmds))
    return t


def code(text):
    return box([Paragraph(text, styles["code"])], CODE_BG, GRAY_LINE)


C = '<font color="#8a8578">'
F = '<font face="Courier" size=9>'

# ---------------------------------------------------------------- Page 1: cover + TL;DR
story.append(para("Deciding Without Generating · handoff #4 · 2026-09-29", "kicker"))
story.append(Spacer(1, 2))
story.append(para("Handoff #4: airline arm 0 complete, first in-loop run", "title"))
story.append(para(
    "Everything since handoff #3 (commit <code>4b82f58</code>): every affordable decider replayed on all 1,076 "
    "airline states, a round of accounting fixes that changed some headline numbers, and the first real "
    "in-loop run (arms B, C, E on airline, all local, $0).",
    "subtitle"))

tldr_items = [
    "<b>Airline arm 0 is done for 7 deciders</b> (Jev, GPT-OSS-20B, Qwen3-8B local, Kev-0.8B/4B/9B, cascade), 1,076 states × 5 repeats. "
    "<b>Jev leads clearly: strict 0.814</b>, vs GPT-OSS-20B 0.672 and every local model at or below 0.40. Jev is also the fastest (p50 0.18 s) and cheapest API decider.",
    "<b>Every paired gap is now significant</b> on ~1,040 states: Jev − GPT-OSS +15.5 pts, Jev − Kev-9B +40.7 pts, Kev-9B − Kev-4B +8.0 pts. "
    "(Handoff #3's −12.2 pts for Kev-4B vs 9B was on 662 states; the direction held, the size shrank.)",
    "<b>First in-loop run (U4), airline, G = user = Qwen3-8B, 750 episodes, 0 errors.</b> Reward: "
    "<b>B 0.308</b> (G decides, then fills) &gt; <b>C 0.196</b> (G alone) &gt; <b>E 0.048</b> (Kev-4B decides). "
    "Kev fails in the loop the same way it fails in arm 0.",
    "<b>Accounting fixes changed numbers:</b> a spending guard after the account ran dry mid-run, errors split into "
    "decider failures vs infra, retries of decider failures stopped, energy pooled across resumes, and cascade $ and J corrected (mock cascade $ had been overstated 2.5×).",
    "<b>Still blocked on credits:</b> the frontier ceiling decider (U3), the remaining 4,005 cascade and 719 GPT-OSS calls, "
    "and arms A and D in the loop. Router and cache-guard decision points haven't been started.",
]
story.append(box([para("TL;DR", "boxh")] + bullets(tldr_items, "boxbody"), YELLOW, YELLOW_LINE))
story.append(Spacer(1, 12))

story.append(para("Your first 5 minutes", "h2"))
story.append(code(
    f'git pull  &nbsp;&nbsp;{C}# airline replay files for every decider, in-loop harness, this PDF</font><br/>'
    f'less results/replay/airline/report/summary.md  {C}# arm 0, all 7 deciders</font><br/>'
    f'less DECISIONS.md  &nbsp;&nbsp;{C}# 13 new rows dated 2026-09-25/26: every fix and why</font><br/>'
    f'less PLAN.md  &nbsp;&nbsp;{C}# G1–G4, U1, U2 ticked; U3/U4 partial</font>'))
story.append(Spacer(1, 6))
story.append(para(
    f"In-loop results (<font face=\"Courier\" size=9>results/inloop/</font>) are <b>git-ignored</b> "
    f"(<font face=\"Courier\" size=9>.gitignore</font> shares only states and replay). They're on Gilbreth scratch in the repo "
    f"checkout. The numbers are copied into DECISIONS.md and into this PDF.", "bodysmall"))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 2: progress
story.append(para("1 · Where we are", "h1"))
story.append(para("Decision points × deciders", "h2"))
story.append(status_grid(
    ["", "Ceiling (frontier LLM)", "Baseline (Qwen3-8B)", "Floor (classifier)", "Jev (under test)"],
    [
        ["<b>Router</b>", "TODO", "TODO", "TODO", "TODO"],
        ["<b>Cache guard</b>", "TODO", "TODO", "TODO", "TODO"],
        ["<b>Agent control</b>",
         "PART — gpt-5.6 generated the airline states; not yet replayed as a decider (U3)",
         "DONE — arm 0 on mock + airline; G in the in-loop run",
         "TODO — Kev-0.8B is the cheapest local point, but it's not a classifier",
         "DONE — arm 0 on mock + airline"],
    ],
    widths=[1.05 * inch, 1.55 * inch, 1.45 * inch, 1.45 * inch, 1.4 * inch],
))
story.append(para("Agent control is the only decision point with data: 2 of 12 cells done, 1 partial.", "bodysmall"))

story.append(Spacer(1, 10))
story.append(para("Experimental arms (agent control, tau2 airline)", "h2"))
story.append(status_grid(
    ["Arm", "What", "Status"],
    [
        ["<b>0</b>", "each decider -&gt; none (decision quality + cost)", "PART — 7 deciders done; frontier LLM missing; cascade 4,005 calls and GPT-OSS 719 still to run"],
        ["<b>A</b>", "Jev (API) -&gt; G", "TODO — one-task vertical slice only; the full run needs credits"],
        ["<b>B</b>", "G choice call -&gt; G", "DONE — reward 0.308, local G = Qwen3-8B"],
        ["<b>C</b>", "G, one call (production default)", "DONE — reward 0.196, local G"],
        ["<b>D</b>", "small LLM -&gt; G", "TODO — needs credits"],
        ["<b>E</b>", "Kev (local GPU) -&gt; G", "DONE — reward 0.048, local G"],
    ],
    widths=[0.55 * inch, 2.6 * inch, 3.75 * inch],
))
story.append(para(
    "B/C/E were run with a free local G (Qwen3-8B). The planned runs with a frontier model as G, which the paper's "
    "headline needs, haven't happened.", "bodysmall"))

story.append(Spacer(1, 10))
story.append(para("PLAN.md checklist", "h2"))
story.extend(bullets([
    "<b>Done:</b> G1 (Kev-4B/9B mock), G2 (compute-node egress, from existing evidence), G3 (Qwen3-8B local), G4 (airline repeats + Kev-0.8B), U0, U1 (lenient labels), U2 (airline states).",
    "<b>Partial:</b> U3 (Jev + GPT-OSS-20B on airline; the frontier LLM is missing), U4 (harness built, B/C/E run with local G; A/D and frontier-G runs not done).",
    "<b>Not started:</b> U5 (paper tables and figures from all arms).",
]))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 3: airline arm 0
story.append(para("2 · Airline arm 0: every affordable decider", "h1"))
story.append(para(
    "1,076 states from reward=1 episodes (the 689 in handoff #3, plus the fill run for tasks 38–49), 5 repeats each. "
    "Each (state, repeat) counts once, as its first attempt that wasn't an infra error.", "body"))
story.append(data_table(
    ["Decider", "Strict [95% CI]", "Lenient", "p50 latency", "$ / decision", "J / dec. (gross)", "Failures"],
    [
        ["Jev (API)", "0.814 [0.791, 0.836]", "0.826", "0.176 s", "1.73e-4", "hosted", "0.0%"],
        ["Cascade Kev-4B -&gt; GPT-OSS, t=0.9 *", "0.669 [0.634, 0.704]", "0.685", "2.100 s", "3.28e-4", "132 (Kev stage)", "7.2%"],
        ["GPT-OSS-20B (API) *", "0.672 [0.647, 0.696]", "0.688", "1.161 s", "3.32e-4", "hosted", "9.2%"],
        ["Kev-9B (A100)", "0.401 [0.371, 0.431]", "0.546", "0.548 s", "local", "170.5", "3.2%"],
        ["Qwen3-8B (A100, vLLM)", "0.396 [0.368, 0.425]", "0.442", "0.656 s", "local", "211.2", "0.0%"],
        ["Kev-4B (A100)", "0.321 [0.294, 0.350]", "0.445", "0.439 s", "local", "132.4", "3.2%"],
        ["Kev-0.8B (A100)", "0.273 [0.247, 0.300]", "0.418", "0.218 s", "local", "47.2", "3.3%"],
    ],
    widths=[1.75 * inch, 1.35 * inch, 0.6 * inch, 0.8 * inch, 0.8 * inch, 0.9 * inch, 0.7 * inch],
))
story.append(para(
    "* Incomplete. The OpenRouter balance ran out mid-run: the cascade has 4,005 calls still missing (729 of 1,076 states seen), "
    "GPT-OSS-20B has 719. Kev failures are its hard 8,192-token input limit on the longest states (\"branch too long\"), which counts as a coverage gap. "
    "GPT-OSS failures are replies that came back without the forced tool call.", "bodysmall"))

story.append(Spacer(1, 8))
story.append(para("Paired significance (cluster bootstrap over states)", "h2"))
story.append(data_table(
    ["Comparison (airline)", "States", "Diff", "95% CI", "Significant?"],
    [
        ["Jev vs GPT-OSS-20B", "1,073", "+15.5 pts", "[+13.2, +17.8]", "Yes"],
        ["Jev vs Kev-9B", "1,042", "+40.7 pts", "[+37.4, +44.1]", "Yes"],
        ["Kev-9B vs Kev-4B", "1,042", "+8.0 pts", "[+5.0, +10.8]", "Yes"],
        ["Cascade vs Kev-4B", "729", "+32.7 pts", "[+28.4, +37.2]", "Yes (incomplete run)"],
    ],
    widths=[2.2 * inch, 0.8 * inch, 1.1 * inch, 1.5 * inch, 1.3 * inch],
))

story.append(Spacer(1, 8))
story.append(box([para(
    "<b>Reading it:</b> on airline, Jev is the best decider by a wide margin: more accurate than GPT-OSS-20B, 6.6× faster, 1.9× cheaper, "
    "and the best calibrated (ECE 0.029). The local models tell a separate energy story. Kev-0.8B gives the most accuracy per joule "
    "(0.58 %/J vs Kev-4B 0.24), and Qwen3-8B costs the most energy for accuracy similar to Kev-9B. "
    "Qwen3-8B (thinking off) is badly overconfident: ECE 0.60 with mean confidence 0.996. Its errors are real judgment errors, "
    "e.g. 508 <font face=\"Courier\" size=9>cancel_reservation</font> choices, often before any lookup.", "boxbody"),
], GREEN, GREEN_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 4: fixes
story.append(para("3 · Accounting fixes (some moved numbers)", "h1"))
story.append(para(
    "Found in a full review of the uncommitted work before the next paid run. Each has a dated row in DECISIONS.md with the reasoning.", "body"))

story.append(para("The account ran dry mid-run, again", "h2"))
story.append(box([para(
    "The airline replay was launched with ~$2.80 left for ~$4.50 of calls, and nothing checked the balance. It ended at $10.15 used of $10: "
    "719 GPT-OSS and 1,794 cascade calls failed with 402 <font face=\"Courier\" size=9>in_flight_budget_exhausted</font>. "
    "<b>Fix:</b> <font face=\"Courier\" size=9>replay_decisions.py</font> now estimates the run's $ from earlier calls, refuses to start above "
    "<font face=\"Courier\" size=9>--max-usd</font> or the live balance (×1.25 + $0.25 headroom, because OpenRouter pre-authorizes in-flight requests), "
    "and stops on the first 402. <font face=\"Courier\" size=9>--dry-run</font> prints the estimate only.", "boxbody"),
], PINK, PINK_LINE))

story.append(Spacer(1, 8))
story.append(para("Errors: decider failures vs infra", "h2"))
story.extend(bullets([
    "New <font face=\"Courier\" size=9>src/dwg/errors.py</font>. Infra errors (402, 429, provider 5xx, network) are retried on resume and never count against a decider. "
    "Decider failures (no tool call, malformed JSON, input too long) are final.",
    "<b>Before this, resume retried every errored row</b>, so a stochastic decider could re-roll its own failures until one succeeded, which inflated accuracy. "
    "The old <font face=\"Courier\" size=9>\"402\" in error</font> check would also have stopped all paid calls on a Kev \"branch too long: 4020 tokens\" message.",
    "Each (decider, state, repeat) counts once, as its first non-infra attempt. Mock numbers moved by ≤3 calls.",
]))

story.append(Spacer(1, 4))
story.append(para("Cost and energy", "h2"))
story.extend(bullets([
    "<b>Cascade $:</b> a non-escalated call now costs $0 instead of \"unknown\". Mock cascade had been reported at 8.8e-5 $/decision; the true figure is 3.5e-5 (2.5× lower). "
    "Airline is unaffected: Kev-4B never reaches 0.9 confidence there, so every call escalates.",
    "<b>Cascade J</b> now comes from the same run's Kev-4B (132 J on airline), not the hard-coded mock value of 18.33 J.",
    "<b>Energy blocks are pooled across resumes.</b> Airline Kev-4B 133.4 -&gt; 132.4 J, Kev-9B 177.3 -&gt; 170.5 J.",
    "<b>Price routing:</b> airline GPT-OSS calls were billed ~2.7–3.4× list price (likely pricier upstreams). Each call now records its <font face=\"Courier\" size=9>provider</font>. "
    "Use <font face=\"Courier\" size=9>--provider-sort price</font> from the start of new runs; don't switch partway through.",
    "<b>Lenient accuracy (U1)</b> also accepts a READ lookup before a WRITE reference. Mock: Jev 0.772 -&gt; 0.877, GPT-OSS 0.852 -&gt; 0.932.",
]))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 5: in-loop
story.append(para("4 · In the loop: arms B, C, E on airline", "h1"))
story.append(para(
    f"New harness: {F}DeciderTau2Agent</font> (the decider picks the tool, G fills in the arguments; arms A/B/D/E share one loop) and tau2's "
    f"{F}LLMAgent</font> for arm C. Trial t uses seed 2000+t in every arm. If the decider fails, G decides that turn, and the turn is logged as a fallback. "
    f"Job 11823642: 50 tasks × 5 trials × 3 arms = 750 episodes, 0 errors. G and the user simulator are both Qwen3-8B (thinking off), $0.", "body"))

story.append(data_table(
    ["Arm", "Reward [95% CI]", "pass^1", "pass^5", "turns / ep.", "decision share of latency", "fallback"],
    [
        ["B: G decides + G fills", "0.308 [0.196, 0.428]", "0.308", "0.200", "7.0", "32.7%", "0.0%"],
        ["C: G alone", "0.196 [0.116, 0.284]", "0.196", "0.060", "11.5", "0%", "—"],
        ["E: Kev-4B decides + G", "0.048 [0.012, 0.092]", "0.048", "0.000", "10.2", "70.4%", "2.5%"],
    ],
    widths=[1.55 * inch, 1.4 * inch, 0.6 * inch, 0.6 * inch, 0.75 * inch, 1.2 * inch, 0.8 * inch],
))
story.append(Spacer(1, 8))

story.append(box([
    para("<b>Why E collapses: Kev's behavior, not a harness bug</b>", "boxbody"),
    para(
        "106 of 250 E episodes end <font face=\"Courier\" size=9>too_many_errors</font> (B: 0, C: 15). In 92 of them, Kev picks "
        "<font face=\"Courier\" size=9>get_user_details</font> before the user has given an ID, and keeps picking it. G, forced to call the chosen tool, "
        "fills in <font face=\"Courier\" size=9>sara_doe_496</font>, the example ID in tau2's own tool docstring. The log has 563 \"User sara_doe_496 not found\" errors. "
        "This matches arm 0, where Kev-4B is weak on airline.", "boxbody"),
], PINK, PINK_LINE))

story.append(Spacer(1, 8))
story.append(box([para(
    "<b>B beats C:</b> with an 8B G, separating the decision from the execution helps rather than hurts: +11 pts reward and fewer turns. "
    "Whether that holds with a frontier G is the open question the paid runs answer.", "boxbody"),
], GREEN, GREEN_LINE))

story.append(Spacer(1, 8))
story.append(box([para(
    "<b>Don't quote in-loop latency as model latency.</b> Kev's in-loop p50 is 4.8 s/decision vs ~0.2–0.6 s in arm 0, "
    "because 8 concurrent episodes queue on a one-request-at-a-time Kev server that shares the GPU with vLLM. "
    "Energy isn't measured in the loop at all. Take latency and J per decision from arm 0; in the loop, report reward, turns and cost shares.", "boxbody"),
], PURPLE, PURPLE_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 6: next steps
story.append(para("5 · What's next", "h1"))

story.append(para("Blocked on you", "h2"))
story.append(box([
    para("<b>Add OpenRouter credits, then pick the frontier model for the ceiling decider (U3).</b> Before launching anything, run "
         "<font face=\"Courier\" size=9>replay_decisions.py --dry-run</font>: the spending guard will refuse any run the balance can't cover.", "boxbody"),
], PINK, PINK_LINE))

story.append(Spacer(1, 8))
story.append(para("Ready to run once credits land", "h2"))
story.extend(bullets([
    "Finish the airline cascade (4,005 calls) and GPT-OSS-20B (719). Keep default routing for these two: they started on it.",
    "U3: the frontier LLM on the 1,076 airline states, 5 repeats, with <font face=\"Courier\" size=9>--provider-sort price</font>.",
    "U4 paid: arms A–E with a frontier G, 50 tasks × ≥5 trials. That's the paper's headline comparison.",
    "Optional, free: Qwen3-8B with thinking on (vLLM <font face=\"Courier\" size=9>--reasoning-parser qwen3</font>) as a second baseline setting.",
]))

story.append(Spacer(1, 6))
story.append(para("Not started", "h2"))
story.extend(bullets([
    "Router and cache-guard decision points (8 of the 12 grid cells).",
    "A real floor decider (a classifier) for agent control.",
    "U5: paper tables and figures across all arms.",
]))

story.append(Spacer(1, 8))
story.append(para("New files this handoff", "h2"))
story.append(code(
    f"src/dwg/decider_tau2_agent.py &nbsp;{C}# DeciderTau2Agent, TimedLLMAgent (arms A/B/D/E)</font><br/>"
    f"scripts/run_inloop.py, scripts/analyze_inloop.py, scripts/inloop_local.slurm<br/>"
    f"src/dwg/errors.py &nbsp;{C}# is_infra_error, is_out_of_credits</font><br/>"
    f"src/dwg/labels.py &nbsp;{C}# strict + lenient accuracy</font><br/>"
    f"src/dwg/billing.py, src/dwg/tau2_llm.py<br/>"
    f"scripts/llm_local_replay.slurm &nbsp;{C}# Qwen3-8B on vLLM, with energy</font><br/>"
    f"results/states/airline-fill.jsonl &nbsp;{C}# tasks 38–49 top-up</font><br/>"
    f"results/replay/airline/calls-*.jsonl &nbsp;{C}# jev, gpt-oss-20b, qwen3-8b, kev-0.8b, cascade</font>"))

story.append(Spacer(1, 8))
story.append(para("Gotchas we hit this round", "h2"))
story.extend(bullets([
    "OpenRouter pre-authorizes in-flight requests, so a run can hit 402 before the balance reads $0. Budget with headroom.",
    "Never retry a decider's own failures on resume: it silently inflates accuracy. Retry infra errors only.",
    "Match error codes only where they're reported as a status (<font face=\"Courier\" size=9>\"code\":402</font>), never as any number in a message.",
    "Redirected stdout is block-buffered, so a multi-hour job's log stayed empty until exit. <font face=\"Courier\" size=9>env.sh</font> now sets PYTHONUNBUFFERED=1.",
    "Kev's first call after load took 8.3 s vs ~0.2 s steady. Free deciders get warmup calls before timing starts.",
]))

doc = SimpleDocTemplate(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DWG_Handoff_4.pdf"),
    pagesize=LETTER,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    topMargin=0.7 * inch, bottomMargin=0.65 * inch,
    title="DWG Handoff 4",
)
doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print("wrote DWG_Handoff_4.pdf")
