#!/usr/bin/env python3
"""Build DWG_Handoff_5.pdf in the same hand-drawn-marker style as DWG_Handoff_4.pdf, covering
everything since handoff #4 (commit 518ea11): GPT-5.6 as the airline ceiling decider (U3),
GPT-OSS-20B completed, the cascade rebuilt around Jev, and the scope decisions of 2026-10-01.

Numbers are copied from results/replay/airline/report/summary.md and DECISIONS.md; the cascade
sweep and held-out threshold were computed from the airline jev and gpt-5.6-sol calls files.

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
    canvas.drawString(0.6 * inch, 0.4 * inch, "DWG handoff #5 · continuing from handoff #4 (commit 518ea11)")
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
story.append(para("Deciding Without Generating · handoff #5 · 2026-10-02", "kicker"))
story.append(Spacer(1, 2))
story.append(para("Handoff #5: the frontier ceiling is in, and Jev now leads the cascade", "title"))
story.append(para(
    "Everything since handoff #4 (commit <code>518ea11</code>): GPT-5.6 replayed as the ceiling decider on all 1,076 airline "
    "states, GPT-OSS-20B finished, the cascade rebuilt around Jev, and a few project-level decisions about scope.",
    "subtitle"))

tldr_items = [
    "<b>U3 done: GPT-5.6 on airline arm 0</b> (5,380 calls, 0.1% failures, $20.57). <b>Strict 0.885</b> vs <b>Jev 0.814</b>: "
    "GPT-5.6 leads by +7.1 pts [+5.2, +9.1]. But Jev is <b>22× cheaper and 22× faster</b> (1.7e-4 vs 3.8e-3 $/decision; p50 0.18 s vs 3.9 s), "
    "and better calibrated (ECE 0.029 vs 0.103). The labels are GPT-5.6's own actions, so its 0.885 is an upper bound.",
    "<b>GPT-OSS-20B finished</b> (all 5,380): strict 0.670, 10.9% failures (replies without the forced tool call). Jev − GPT-OSS = +15.5 pts, significant.",
    "<b>The cascade's fast stage is now Jev, not Kev.</b> Kev only exists to ask whether an open model gets near Jev, so it never stands in for it. "
    "Simulated Jev -&gt; GPT-5.6 at <b>t = 0.65</b> (picked on held-out tasks): <b>0.854 held-out</b>, at about a quarter of GPT-5.6's cost.",
    "<b>Scope decisions:</b> airline is the only headline domain and runs at full planned scope; mock gets no new runs (it ranks GPT-OSS above Jev, "
    "the opposite of airline). Frontier model = GPT-5.6, pinned as <font face=\"Courier\" size=9>gpt-5.6-sol</font>.",
    "<b>Your job on Gilbreth:</b> finish the Kev-4B cascade comparison row (4,005 calls, ~$1.30). Command on page 5.",
]
story.append(box([para("TL;DR", "boxh")] + bullets(tldr_items, "boxbody"), YELLOW, YELLOW_LINE))
story.append(Spacer(1, 12))

story.append(para("Your first 5 minutes", "h2"))
story.append(code(
    f'git fetch &amp;&amp; git checkout jev-cascade-gpt56-pilot  {C}# this round is on a branch, not main yet</font><br/>'
    f'less results/replay/airline/report/summary.md  {C}# arm 0, now with GPT-5.6</font><br/>'
    f'less DECISIONS.md  &nbsp;&nbsp;{C}# new rows dated 2026-10-01/02</font><br/>'
    f'less PLAN.md  &nbsp;&nbsp;{C}# U3 now has its follow-up steps</font>'))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 2: progress
story.append(para("1 · Where we are", "h1"))
story.append(para("Experimental arms (agent control, tau2 airline)", "h2"))
story.append(status_grid(
    ["Arm", "What", "Status"],
    [
        ["<b>0</b>", "each decider -&gt; none (decision quality + cost)",
         "PART — 8 deciders complete incl. GPT-5.6; Kev-4B cascade 4,005 calls left (Gilbreth); live Jev cascade not run yet"],
        ["<b>A</b>", "Jev (API) -&gt; G", "TODO — frontier G = GPT-5.6; pilot first to price it"],
        ["<b>B</b>", "G choice call -&gt; G", "PART — done with local G (0.308); frontier-G run TODO"],
        ["<b>C</b>", "G, one call (production default)", "PART — done with local G (0.196); frontier-G run TODO"],
        ["<b>D</b>", "small LLM -&gt; G", "TODO"],
        ["<b>E</b>", "Kev (local GPU) -&gt; G", "PART — done with local G (0.048); frontier-G run TODO"],
    ],
    widths=[0.55 * inch, 2.6 * inch, 3.75 * inch],
))
story.append(para(
    "Arm 0 is nearly finished. The in-loop arms with GPT-5.6 as G and as the user simulator are the paper's headline "
    "and the biggest remaining cost.", "bodysmall"))

story.append(Spacer(1, 10))
story.append(para("PLAN.md checklist", "h2"))
story.extend(bullets([
    "<b>Done:</b> G1–G4, U0, U1, U2, and now <b>U3</b> (Jev, GPT-OSS-20B and GPT-5.6 on all 1,076 airline states).",
    "<b>Partial:</b> U4 (harness built; B/C/E run with local G; every frontier-G run and arms A/D still to do).",
    "<b>Not started:</b> U5 (paper tables and figures), router and cache-guard decision points.",
]))

story.append(Spacer(1, 10))
story.append(para("Decisions this round (rows in DECISIONS.md)", "h2"))
story.extend(bullets([
    "<b>Jev is the representative classifier.</b> Wherever one classifier stands for \"the classifier\" (the cascade's fast stage, a headline row), "
    "it's Jev. Kev appears only next to Jev, as the open-weights comparison. A Kev-only test answers nothing the paper asks.",
    "<b>Airline at full scope, no cost cuts</b> (no cheaper user simulator, no fewer arms or trials). Mock is a pilot/appendix point only.",
    "<b>Frontier = <font face=\"Courier\" size=9>openrouter/openai/gpt-5.6-sol</font>.</b> OpenRouter's <font face=\"Courier\" size=9>openai/gpt-5.6</font> "
    "is now an alias for it; other GPT-5.6 variants cost 0.1–2× as much, so it's pinned explicitly.",
    "<b>Cascade thresholds come from a sweep, not 0.9.</b> 0.9 was the vendor's starting advice for Jev, reused unchanged for Kev.",
]))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 3: airline arm 0
story.append(para("2 · Airline arm 0 with the ceiling", "h1"))
story.append(para(
    "1,076 states from reward=1 episodes, 5 repeats each. Each (state, repeat) counts once, as its first attempt that wasn't an infra error.", "body"))
story.append(data_table(
    ["Decider", "Strict [95% CI]", "Lenient", "p50 latency", "$ / decision", "ECE", "Failures"],
    [
        ["GPT-5.6-sol (API, ceiling) †", "0.885 [0.868, 0.901]", "0.897", "3.909 s", "3.83e-3", "0.103", "0.1%"],
        ["<b>Jev (API)</b>", "<b>0.814 [0.791, 0.836]</b>", "0.826", "<b>0.176 s</b>", "<b>1.73e-4</b>", "<b>0.029</b>", "0.0%"],
        ["GPT-OSS-20B (API)", "0.670 [0.646, 0.693]", "0.686", "1.299 s", "3.11e-4", "0.286", "10.9%"],
        ["Cascade Kev-4B -&gt; GPT-OSS, t=0.9 *", "0.669 [0.634, 0.704]", "0.685", "2.100 s", "3.28e-4", "0.287", "7.2%"],
        ["Kev-9B (A100)", "0.401 [0.371, 0.431]", "0.546", "0.548 s", "local", "—", "3.2%"],
        ["Qwen3-8B (A100, vLLM)", "0.396 [0.368, 0.425]", "0.442", "0.656 s", "local", "0.60", "0.0%"],
        ["Kev-4B (A100)", "0.321 [0.294, 0.350]", "0.445", "0.439 s", "local", "0.124", "3.2%"],
        ["Kev-0.8B (A100)", "0.273 [0.247, 0.300]", "0.418", "0.218 s", "local", "0.088", "3.3%"],
    ],
    widths=[1.95 * inch, 1.35 * inch, 0.6 * inch, 0.8 * inch, 0.8 * inch, 0.6 * inch, 0.8 * inch],
))
story.append(para(
    "† Graded against its own actions: the airline labels are GPT-5.6's reference trajectories, so 0.885 is an upper bound. "
    "* Incomplete: 4,005 calls still missing (729 of 1,076 states seen); finishing it is your Gilbreth job. "
    "Local deciders' latency and energy are unchanged from handoff #4.", "bodysmall"))

story.append(Spacer(1, 8))
story.append(para("Paired significance (cluster bootstrap over states)", "h2"))
story.append(data_table(
    ["Comparison (airline)", "States", "Diff", "95% CI", "Significant?"],
    [
        ["GPT-5.6 vs Jev", "1,076", "+7.1 pts", "[+5.2, +9.1]", "Yes"],
        ["Jev vs GPT-OSS-20B", "1,075", "+15.5 pts", "[+13.3, +17.7]", "Yes"],
        ["Jev vs Kev-9B", "1,042", "+40.7 pts", "[+37.4, +44.1]", "Yes"],
    ],
    widths=[2.2 * inch, 0.8 * inch, 1.1 * inch, 1.5 * inch, 1.3 * inch],
))

story.append(Spacer(1, 8))
story.append(box([para(
    "<b>Reading it:</b> the frontier model buys about 7 points over Jev, for 22× the cost and 22× the latency per decision. "
    "Jev is also the best calibrated decider here and the most consistent across repeats (0.985 vs GPT-5.6's 0.958). "
    "That trade-off is exactly what a cascade can exploit: let Jev decide when it's confident, and pay for GPT-5.6 only when it isn't.", "boxbody"),
], GREEN, GREEN_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 4: cascade
story.append(para("3 · The cascade, rebuilt around Jev", "h1"))
story.append(para(
    f"{F}replay_decisions.py --deciders cascade</font> now takes {F}--cascade-fast {{jev,kev}}</font>, default <b>jev</b>. "
    f"Runs are named {F}cascade-&lt;fast&gt;-t&lt;threshold&gt;</font> (e.g. {F}cascade-jev-t0.65</font>), and a Jev cascade needs no Kev server. "
    f"{F}kev_cascade_replay.slurm</font> passes {F}--cascade-fast kev</font>, so it stays the Kev comparison row.", "body"))

story.append(para("Why not Jev -&gt; GPT-OSS-20B?", "h2"))
story.append(box([para(
    "Escalating only helps toward a model that's stronger than the fast stage. On airline, GPT-OSS-20B is <i>weaker</i> than Jev "
    "(0.670 vs 0.814), so every escalation swaps a decision for a worse, costlier one. Simulated: 0.802 at t=0.6, 0.707 at t=0.9. "
    "The cascade escalates to GPT-5.6 instead.", "boxbody"),
], PINK, PINK_LINE))

story.append(Spacer(1, 8))
story.append(para("Jev -&gt; GPT-5.6, simulated from the two standalone runs", "h2"))
story.append(data_table(
    ["Threshold", "Sent to GPT-5.6", "Accuracy", "$ / decision", "Mean latency", "Live run ≈"],
    [
        ["0.6", "13%", "0.842", "6.7e-4", "0.87 s", "$3.60"],
        ["<b>0.65 (chosen)</b>", "17%", "0.850 (<b>0.854 held-out</b>)", "8.4e-4", "1.09 s", "$4.50"],
        ["0.7", "21%", "0.854", "9.7e-4", "1.29 s", "$5.20"],
        ["0.8", "31%", "0.870", "1.4e-3", "1.81 s", "$7.30"],
        ["0.9", "52%", "0.881", "2.2e-3", "2.84 s", "$11.60"],
        ["GPT-5.6 alone", "100%", "0.885", "3.8e-3", "4.90 s", "—"],
    ],
    widths=[1.3 * inch, 1.1 * inch, 1.2 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch],
))
story.append(para(
    "In-sample rows (threshold scored on the same states it is judged on); 0.65 also has its held-out score. "
    "<b>How 0.65 was chosen:</b> 40 random half/half splits by task; on one half, pick the Pareto point closest to utopia "
    f"(the same rule as {F}make_cascade_figure.py</font>), score it on the other half. "
    "0.65 won 23 of 40 folds (0.75 won 15) and is also the full-data pick. Held-out accuracy 0.854 (range 0.822–0.876).", "bodysmall"))

story.append(Spacer(1, 8))
story.append(box([para(
    "<b>Mock would have told the wrong story.</b> On mock, GPT-OSS beats Jev (0.855 vs 0.772) and the Kev-4B cascade looks viable "
    "(0.680 at t=0.9, sometimes not escalating). On airline the ranking flips and the Kev-4B cascade escalates ~98% of calls, "
    "making it GPT-OSS plus Kev's cost. Worth one appendix paragraph: easy benchmarks flatter weak designs.", "boxbody"),
], PURPLE, PURPLE_LINE))

story.append(PageBreak())

# ---------------------------------------------------------------- Page 5: next steps
story.append(para("4 · What's next", "h1"))

story.append(para("Your job on Gilbreth: finish the Kev-4B cascade (comparison row)", "h2"))
story.append(box([
    para("Needs the Kev-4B server on an A100, so it can't run on the laptop. It resumes past the 3,169 calls already done. "
         "Escalations bill the OpenRouter key in Gilbreth's <font face=\"Courier\" size=9>.env</font>: ~$1.30.", "boxbody"),
    Spacer(1, 4),
    Paragraph('git fetch &amp;&amp; git checkout jev-cascade-gpt56-pilot<br/>'
              'sbatch --mem=32G --export=ALL,STATES=results/states/airline.jsonl,RUN=results/replay/airline,THRESHOLD=0.9 \\<br/>'
              '&nbsp;&nbsp;&nbsp;&nbsp;scripts/kev_cascade_replay.slurm', styles["code"]),
    Spacer(1, 4),
    para("Then commit and push only <font face=\"Courier\" size=9>calls-cascade-kev-4b-t0.9.jsonl</font> and "
         "<font face=\"Courier\" size=9>meta-cascade-kev-4b-t0.9.json</font>. Nobody else writes those files, so there's nothing to merge.", "boxbody"),
], BLUE, BLUE_LINE))

story.append(Spacer(1, 8))
story.append(para("Next paid steps (laptop, OpenRouter balance ~$29)", "h2"))
story.extend(bullets([
    f"<b>Live Jev -&gt; GPT-5.6 cascade at t=0.65</b>, ~$4.50: {F}--deciders cascade --cascade-threshold 0.65 --llm-model openrouter/openai/gpt-5.6-sol --provider-sort price</font>.",
    "<b>U4 with a frontier G:</b> arms A–E, GPT-5.6 as G and as the user simulator, 50 tasks × 5 trials. Pilot a few episodes first to measure $/episode; "
    "this will need a new top-up.",
    "<b>U5:</b> paper tables and figures. The figure scripts' label tables don't know GPT-5.6 or the Jev cascade yet.",
]))

story.append(Spacer(1, 6))
story.append(para("Gotchas we hit this round", "h2"))
story.extend(bullets([
    "<b>$/call moved 2× during the run.</b> The first 500 GPT-5.6 calls averaged $0.0083 (cache cold), the whole run $0.0038. "
    "Check the real $/call after a few hundred calls rather than trusting a pilot of 25.",
    "<b>The spending guard wants 1.25× the estimate in the account.</b> When that doesn't fit, split the states file and run the halves one after another "
    "with half the cap each, rather than weakening the guard.",
    f"<b>A subset run used to shrink the run's {F}n_states</font></b> (a 5-state pilot set airline to 5). Fixed: it now only grows.",
    f"<b>Locally, tests need {F}TAU2_DATA_DIR</font></b> pointing at the tau2 data (e.g. ~/tau2-bench/data); without it two label tests fail.",
]))

story.append(Spacer(1, 6))
story.append(para("Changed files this handoff", "h2"))
story.append(code(
    f"scripts/replay_decisions.py &nbsp;{C}# --cascade-fast, n_states only grows</font><br/>"
    f"scripts/kev_cascade_replay.slurm &nbsp;{C}# passes --cascade-fast kev</font><br/>"
    f"results/replay/airline/calls-llm_openrouter_openai_gpt-5.6-sol.jsonl &nbsp;{C}# U3</font><br/>"
    f"results/replay/airline/calls-llm_openrouter_openai_gpt-oss-20b.jsonl &nbsp;{C}# completed</font><br/>"
    f"results/replay/airline/report/ &nbsp;{C}# regenerated</font><br/>"
    f"DECISIONS.md, PLAN.md, scripts/make_handoff5_pdf.py"))

doc = SimpleDocTemplate(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DWG_Handoff_5.pdf"),
    pagesize=LETTER,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    topMargin=0.7 * inch, bottomMargin=0.65 * inch,
    title="DWG Handoff 5",
)
doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print("wrote DWG_Handoff_5.pdf")
