#!/usr/bin/env python3
"""Build DWG_Handoff_6.pdf in the same hand-drawn-marker style as DWG_Handoff_5.pdf, covering
everything since handoff #5 (commit a080a1f): the Kev-4B cascade row finished, the live Jev ->
GPT-5.6 cascade, U4 (airline in-loop arms A-E with a frontier G) and U5 (paper figures), with
the paper figures embedded.

Numbers are copied from results/replay/airline/report/summary.md,
results/inloop/airline-frontier-gpt-5.6-sol/report/summary.md and DECISIONS.md; figures are the
PNGs those runs' figure scripts wrote (make_paper_figures.py, make_cascade_figure.py,
make_inloop_figures.py).

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
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image,
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
    canvas.drawString(0.6 * inch, 0.4 * inch, "DWG handoff #6 · continuing from handoff #5 (commit a080a1f)")
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

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ARM0_FIG = os.path.join(ROOT, "results/replay/airline/paper_figures")
LOOP_FIG = os.path.join(ROOT, "results/inloop/airline-frontier-gpt-5.6-sol/paper_figures")


def figure(path, width=6.9 * inch, max_height=None, caption=None):
    """A PNG at the page's text width (or less, to fit max_height), keeping its aspect ratio."""
    w, h = ImageReader(path).getSize()
    out_w, out_h = width, width * h / w
    if max_height and out_h > max_height:
        out_w, out_h = max_height * w / h, max_height
    img = Image(path, width=out_w, height=out_h)
    img.hAlign = "CENTER"
    parts = [img]
    if caption:
        parts += [Spacer(1, 2), para(caption, "bodysmall")]
    return KeepTogether(parts)


# ---------------------------------------------------------------- Page 1: cover + TL;DR
story.append(para("Deciding Without Generating · handoff #6 · 2026-10-04", "kicker"))
story.append(Spacer(1, 2))
story.append(para("Handoff #6: the in-loop results are in, and the single call wins", "title"))
story.append(para(
    "Everything since handoff #5 (commit <code>a080a1f</code>): the Kev-4B cascade row finished, the live Jev -&gt; GPT-5.6 "
    "cascade, U4 (all five in-loop arms with GPT-5.6 as G and as the user simulator) and U5 (the paper figures, embedded below).",
    "subtitle"))

tldr_items = [
    "<b>Live Jev -&gt; GPT-5.6 cascade (t = 0.65): strict 0.849</b> [0.828, 0.869], 16.7% escalated, 8.2e-4 $/decision. "
    "+3.5 pts over Jev, −3.6 under GPT-5.6 (both significant), at <b>21% of GPT-5.6's cost</b>. It matches the simulation (0.850).",
    "<b>U4 done</b> (50 tasks × 5 trials × 5 arms, $74). Reward: <b>B G-decides 0.796, C G-alone 0.792</b>, A Jev 0.744, D GPT-OSS 0.692, E Kev-4B 0.045.",
    "<b>The single call wins.</b> C, where G decides inside its own call, is the cheapest arm ($0.033 per success) and ties B. "
    "A separate decision step doesn't pay off against it with a frontier G.",
    "<b>Among separate deciders, Jev is by far the cheapest:</b> A − B = −5.2 pts reward (borderline), but <b>−$0.105 and −24 s per episode</b>. "
    "Jev's decision is 5% of the agent's $; GPT-5.6's is 75%.",
    "<b>U5 done:</b> figures 1–14 and the tables. <b>Open question for the advisor:</b> how to frame the paper, and whether to build router and cache-guard (page 7).",
]
story.append(box([para("TL;DR", "boxh")] + bullets(tldr_items, "boxbody"), YELLOW, YELLOW_LINE))
story.append(Spacer(1, 12))

story.append(para("Your first 5 minutes", "h2"))
story.append(code(
    f'git fetch &amp;&amp; git checkout jev-cascade-gpt56-pilot  {C}# still on the branch, not main</font><br/>'
    f'less results/inloop/airline-frontier-gpt-5.6-sol/report/summary.md  {C}# U4: arms + paired diffs</font><br/>'
    f'ls results/replay/airline/paper_figures results/inloop/*/paper_figures  {C}# all figures</font><br/>'
    f'less DECISIONS.md  &nbsp;&nbsp;{C}# new rows dated 2026-10-02/03/04</font>'))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 2: progress
story.append(para("1 · Where we are", "h1"))
story.append(para("Experimental arms (agent control, tau2 airline)", "h2"))
story.append(status_grid(
    ["Arm", "What", "Status"],
    [
        ["<b>0</b>", "each decider -&gt; none (decision quality + cost)",
         "DONE — 9 rows incl. GPT-5.6, the live Jev cascade and the finished Kev-4B cascade"],
        ["<b>A</b>", "Jev (API) -&gt; G", "DONE — frontier G: 0.744"],
        ["<b>B</b>", "G choice call -&gt; G", "DONE — frontier G: 0.796 (local G: 0.308)"],
        ["<b>C</b>", "G, one call (production default)", "DONE — frontier G: 0.792 (local G: 0.196)"],
        ["<b>D</b>", "small LLM (GPT-OSS-20B) -&gt; G", "DONE — frontier G: 0.692"],
        ["<b>E</b>", "Kev-4B (local GPU) -&gt; G", "DONE — frontier G: 0.045 (local G: 0.048)"],
    ],
    widths=[0.55 * inch, 2.6 * inch, 3.75 * inch],
))
story.append(para("G = executor and user simulator = <font face=\"Courier\" size=9>openrouter/openai/gpt-5.6-sol</font>; "
                  "local-G runs (Qwen3-8B) are from handoff #4.", "bodysmall"))

story.append(Spacer(1, 10))
story.append(para("PLAN.md checklist", "h2"))
story.extend(bullets([
    "<b>Done:</b> G1–G4, U0–U3, and now <b>U4</b> (frontier-G in-loop) and <b>U5</b> (figures and tables).",
    "<b>Not started:</b> the paper's prose; router and cache-guard decision points; the floor classifier.",
    "<b>Housekeeping:</b> merge <font face=\"Courier\" size=9>jev-cascade-gpt56-pilot</font> into main.",
]))

story.append(Spacer(1, 10))
story.append(para("Spend this round (OpenRouter)", "h2"))
story.append(data_table(
    ["Run", "Job(s)", "Cost"],
    [
        ["Kev-4B cascade, last 4,005 calls", "11865682", "$0.63"],
        ["Live Jev -&gt; GPT-5.6 cascade, 5,380 calls", "11873642", "$4.39"],
        ["U4 pilot, 20 episodes", "11873846", "$0.89"],
        ["U4 full, 1,230 episodes", "11878151–53, 11878918, 11878944–46", "$73.18"],
        ["<b>Total</b>", "", "<b>$79.09</b>"],
    ],
    widths=[3.2 * inch, 2.5 * inch, 1.2 * inch],
))
story.append(para("Balance left ≈ $9. The 444 episodes refused by the key limit cost $0 (page 8).", "bodysmall"))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 3: arm 0 final
story.append(para("2 · Arm 0, final", "h1"))
story.append(data_table(
    ["Decider", "Strict [95% CI]", "Mean latency", "$ / decision", "ECE", "Failures"],
    [
        ["GPT-5.6-sol (ceiling) †", "0.885 [0.868, 0.901]", "4.90 s", "3.83e-3", "0.103", "0.1%"],
        ["<b>Jev -&gt; GPT-5.6, t=0.65 (live)</b>", "<b>0.849 [0.828, 0.869]</b>", "<b>0.63 s</b>", "<b>8.16e-4</b>", "0.063", "0.0%"],
        ["<b>Jev</b>", "<b>0.814 [0.791, 0.836]</b>", "<b>0.18 s</b>", "<b>1.73e-4</b>", "<b>0.029</b>", "0.0%"],
        ["GPT-OSS-20B", "0.670 [0.646, 0.693]", "1.99 s", "3.11e-4", "0.286", "10.9%"],
        ["Kev-4B -&gt; GPT-OSS, t=0.9", "0.647 [0.623, 0.672]", "3.94 s", "2.11e-4", "0.311", "11.3%"],
        ["Kev-9B / Qwen3-8B / Kev-4B / Kev-0.8B", "0.401 / 0.396 / 0.321 / 0.273", "0.24–0.72 s", "local", "—", "0–3.3%"],
    ],
    widths=[2.25 * inch, 1.7 * inch, 0.85 * inch, 0.85 * inch, 0.5 * inch, 0.75 * inch],
))
story.append(para("† Graded against its own reference actions, so an upper bound. "
                  "The Kev-4B cascade is now complete; it escalated every successful call in its final job.", "bodysmall"))
story.append(Spacer(1, 6))
story.append(figure(os.path.join(ARM0_FIG, "fig1_pareto_accuracy_latency.png"), max_height=4.6 * inch,
                    caption="Figure 1 now uses <b>mean</b> latency: on the median, the cascade (5 of 6 calls never escalate) "
                            "showed as faster than Jev on run-to-run noise. The frontier is Jev -&gt; cascade -&gt; GPT-5.6."))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 4: live cascade
story.append(para("3 · The live Jev -&gt; GPT-5.6 cascade", "h1"))
story.append(data_table(
    ["t = 0.65", "Accuracy", "Sent to GPT-5.6", "$ / decision", "Mean latency"],
    [
        ["Simulated (from the standalone runs)", "0.850 (0.854 held-out)", "16.7%", "8.36e-4", "1.09 s"],
        ["<b>Live run</b> (job 11873642)", "<b>0.849</b>", "<b>16.7%</b>", "<b>8.16e-4</b>", "<b>0.63 s</b>"],
    ],
    widths=[2.3 * inch, 1.4 * inch, 1.1 * inch, 1.0 * inch, 1.1 * inch],
))
story.append(para("Paired over 1,076 states: cascade − Jev <b>+3.5 pts</b> [+2.2, +4.9]; cascade − GPT-5.6 <b>−3.6 pts</b> [−5.0, −2.2]. "
                  "Accuracy and cost match the simulation; the live run was faster because its escalated GPT-5.6 calls ran faster "
                  "than in the standalone replay.", "body"))
story.append(figure(os.path.join(ARM0_FIG, "fig10_cascade_threshold_sweep.png"), max_height=5.6 * inch,
                    caption="Figure 10. The dotted line is the threshold in use (0.65, chosen on held-out tasks). "
                            "The simulation now includes Jev's own $ per call."))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 5: U4 results
story.append(para("4 · U4: the five arms in the loop", "h1"))
story.append(para("Airline, 50 tasks × 5 trials per arm, same user-simulator seed per (task, trial) across arms. "
                  "G and the user simulator are GPT-5.6-sol.", "body"))
story.append(data_table(
    ["Arm", "Reward [95% CI]", "pass^5", "Agent $ / episode", "Agent $ / success", "Decision share of $", "Wall s / ep"],
    [
        ["B: G decides -&gt; G", "0.796 [0.696, 0.888]", "0.660", "$0.140", "$0.176", "74.5%", "65.6"],
        ["<b>C: G alone (1 call)</b>", "<b>0.792 [0.696, 0.884]</b>", "0.640", "<b>$0.026</b>", "<b>$0.033</b>", "0%", "<b>37.3</b>"],
        ["<b>A: Jev -&gt; G</b>", "<b>0.744 [0.636, 0.844]</b>", "0.600", "$0.036", "$0.048", "<b>5.3%</b>", "41.4"],
        ["D: GPT-OSS-20B -&gt; G", "0.692 [0.572, 0.804]", "0.540", "$0.030", "$0.043", "4.9%", "59.8"],
        ["E: Kev-4B -&gt; G", "0.045 [0.012, 0.089]", "—", "$0.022", "$0.476", "0% (local)", "31.5"],
    ],
    widths=[1.5 * inch, 1.4 * inch, 0.55 * inch, 0.85 * inch, 0.85 * inch, 0.9 * inch, 0.75 * inch],
))
story.append(para("Agent $ = decision + execution; the user simulator's $ is reported apart. "
                  "Arm E: 244 episodes plus 6 where G returned an empty message (counted as errors).", "bodysmall"))
story.append(Spacer(1, 4))
story.append(figure(os.path.join(LOOP_FIG, "fig12_inloop_cost_vs_reward.png"), max_height=4.3 * inch))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 6: paired + where the money goes
story.append(para("5 · Paired arm differences", "h1"))
story.append(data_table(
    ["Comparison", "Reward diff [95% CI]", "Agent $ / episode diff", "Wall s / episode diff"],
    [
        ["A − B: Jev vs G deciding (same executor)", "<b>−0.052</b> [−0.108, −0.004] *", "<b>−$0.105</b> *", "<b>−24.2 s</b> *"],
        ["A − C: Jev + G vs the single call", "−0.048 [−0.108, +0.008]", "+$0.009 *", "+4.1 s *"],
        ["B − C: G deciding separately vs single call", "+0.004 [−0.028, +0.040]", "+$0.114 *", "+28.3 s *"],
        ["D − A: GPT-OSS vs Jev deciding", "−0.052 [−0.124, +0.020]", "−$0.006 *", "+18.4 s *"],
        ["E − A: Kev-4B vs Jev deciding", "−0.701 [−0.801, −0.595] *", "−$0.014 *", "−9.9 s *"],
    ],
    widths=[2.5 * inch, 1.75 * inch, 1.35 * inch, 1.3 * inch],
))
story.append(para("Per-task mean difference over the same (task, trial) pairs, 95% bootstrap CI over 50 tasks; * = CI excludes 0. "
                  "A − B's CI only just excludes 0 (it touched 0 on a partial-data run), so call it borderline.", "bodysmall"))
story.append(Spacer(1, 6))
story.append(box([para(
    "<b>Reading it honestly:</b> with a frontier G, splitting <i>decide</i> from <i>execute</i> doesn't beat letting G decide in its own call. "
    "C ties B on reward at a fifth of the cost, and is cheaper than A, because the split adds a call every turn. "
    "<b>Where Jev wins</b> is against a separate frontier decision step: A − B saves $0.105 and 24 s per episode for about 5 pts of reward, "
    "the same gap arm 0 shows (Jev 0.814 vs GPT-5.6 0.885 per decision). The arm-0 cascade closes half that gap, but it hasn't been run in the loop.",
    "boxbody")], GREEN, GREEN_LINE))
story.append(Spacer(1, 6))
story.append(figure(os.path.join(LOOP_FIG, "fig14_inloop_cost_breakdown.png"), max_height=3.3 * inch))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 7: reliability + the advisor question
story.append(para("6 · Reliability, and the question for the advisor", "h1"))
story.append(figure(os.path.join(LOOP_FIG, "fig13_inloop_pass_k.png"), max_height=3.6 * inch,
                    caption="pass^k keeps the same ranking at every k: B ≈ C &gt; A &gt; D, with Kev-4B near 0."))
story.append(Spacer(1, 8))
story.append(box([
    para("Decide before building more", "boxh"),
    para("The project's premise was that a cheap decider saves money against the frontier model doing everything. "
         "U4 says that holds against a <i>separate</i> frontier decision step (A vs B), but not against the frontier model's own single call (C). "
         "Three ways forward, best discussed with the advisor:", "boxbody"),
] + bullets([
    "<b>Frame the paper around this result</b> (agent control only): the numbers and figures exist; what's left is prose.",
    "<b>Test the in-loop cascade first</b> (~$15–20 plus a little code): Jev decides, and GPT-5.6 decides below t = 0.65. "
    "If it closes A's 5-pt gap at near C's cost, Jev has a clear role.",
    "<b>Keep the full scope:</b> build router and cache-guard (no harness or dataset yet; ~$50–75 API plus 1–2 weeks each).",
], "boxbody"), PURPLE, PURPLE_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 8: next + gotchas
story.append(para("7 · What's next", "h1"))
story.extend(bullets([
    "<b>Advisor meeting:</b> paper framing and scope (page 7).",
    "<b>Merge the branch</b> <font face=\"Courier\" size=9>jev-cascade-gpt56-pilot</font> into main.",
    "<b>Paper prose</b> from figures 1–14 and the tables. State plainly: Kev is not Jev; GPT-5.6's arm-0 accuracy is an upper bound; "
    "airline is the only headline domain.",
    "<b>Credit:</b> ~$9 left. Load ~$25 only for the in-loop cascade; ~$75 for router + cache-guard once built.",
]))

story.append(Spacer(1, 6))
story.append(para("Gotchas we hit this round", "h2"))
story.extend(bullets([
    "<b>OpenRouter keys have their own spend limit</b>, separate from the account balance (Settings &gt; API Keys). "
    "Its refusal (\"Key limit exceeded\", HTTP 403) wasn't recognized, so 444 episodes failed instantly. "
    f"Fixed in {F}dwg/errors.py</font>: it now stops paid calls and is retried on resume. Raise the key limit before big runs.",
    "<b>davisjam's normal-QoS GPU cap is 3× A100-80GB and 0 for every other card</b>; standby doesn't count against it. "
    f"A job moved to standby after submitting must also drop the group GRES: {F}scontrol update JobId=&lt;id&gt; TresPerNode=gres/gpu:1</font>.",
    "<b>All gilbreth-k nodes failed every job launch</b> after a reboot on 2026-10-03 and recovered on 10-04. "
    f"{F}sacct -D</font> shows the node of each failed launch.",
    f"<b>{F}results/inloop/</font> wasn't in git</b> ({F}.gitignore</font> only whitelisted states and replay). Now it is.",
    "<b>Arm B costs more than its pilot said</b> ($0.15 vs $0.10 per episode): a 4-task pilot underestimates. Give per-arm caps headroom.",
]))

story.append(Spacer(1, 6))
story.append(para("Changed files this handoff", "h2"))
story.append(code(
    f"scripts/jev_cascade_replay.slurm, scripts/inloop_frontier.slurm &nbsp;{C}# new: live cascade, frontier-G in-loop</font><br/>"
    f"scripts/make_inloop_figures.py &nbsp;{C}# new: figs 11-14</font><br/>"
    f"scripts/make_paper_figures.py, make_cascade_figure.py, post_experiment_analysis.py &nbsp;{C}# GPT-5.6, Jev cascade</font><br/>"
    f"scripts/analyze_inloop.py &nbsp;{C}# paired arm differences</font><br/>"
    f"src/dwg/errors.py, tests/test_analyze.py &nbsp;{C}# key limit = billing error</font><br/>"
    f"results/inloop/airline-frontier-gpt-5.6-sol/, results/replay/airline/ &nbsp;{C}# data + figures</font><br/>"
    f".gitignore, DECISIONS.md, PLAN.md, scripts/make_handoff6_pdf.py"))

doc = SimpleDocTemplate(
    os.path.join(ROOT, "DWG_Handoff_6.pdf"),
    pagesize=LETTER,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    topMargin=0.7 * inch, bottomMargin=0.65 * inch,
    title="DWG Handoff 6",
)
doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print("wrote DWG_Handoff_6.pdf")
