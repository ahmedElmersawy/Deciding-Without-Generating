#!/usr/bin/env python3
"""Build DWG_Handoff_7.pdf in the same hand-drawn-marker style as DWG_Handoff_6.pdf. Part I explains
the whole project in plain language (what is measured, the three decision points, the thesis);
Part II is the usual handoff since #6 (commit fbf9d90 / 3223b3f): cache guard and router, built and
run end to end, with paired significance.

Numbers are copied from results/replay/cacheguard-*/report/summary.md, cacheguard-paired.md,
results/replay/router-routerbench/report/summary.md and DECISIONS.md; figures are the PNGs the
figure scripts wrote. Fonts from $DWG_FONT_DIR (default /scratch/gilbreth/$USER/dwg-data/fonts).
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

FONT_DIR = os.environ.get("DWG_FONT_DIR", f"/scratch/gilbreth/{os.environ.get('USER', 'user')}/dwg-data/fonts")
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
    canvas.drawString(0.6 * inch, 0.4 * inch, "DWG handoff #7 · continuing from handoff #6 (commit 3223b3f)")
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
CG_FIG = os.path.join(ROOT, "results/replay/cacheguard-paper_figures")
RT_FIG = os.path.join(ROOT, "results/replay/router-paper_figures")


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


# =============================================================== PART I: the project explained
# ---------------------------------------------------------------- Page 1: cover + TL;DR
story.append(para("Deciding Without Generating · handoff #7 · 2026-10-05", "kicker"))
story.append(Spacer(1, 2))
story.append(para("Handoff #7: three decision points, one answer", "title"))
story.append(para(
    "Every experiment is now run: agent control (handoffs #4–#6), and since #6 the cache guard and the router, "
    "built and run end to end. Part I explains the whole project from scratch; Part II is the usual handoff.",
    "subtitle"))
tldr = [
    "<b>The question:</b> can a cheap model that only <i>decides</i> (Jev, about $0.00002 per decision) save money "
    "against a frontier model (GPT-5.6) that generates everything?",
    "<b>The answer, across three decision points:</b> a standalone decider pays off when its decision "
    "<b>replaces</b> generation <b>and</b> it can see something the cheap alternative can't. Not when generation "
    "happens anyway, and not when the knowledge it needs isn't in its input.",
    "<b>Agent control:</b> no. GPT-5.6 deciding inside its own single call is cheapest (reward 0.79 vs Jev+G 0.74).",
    "<b>Cache guard:</b> yes, where it matters. On GSM-Plus Jev is right 93.3% vs 66% for every similarity method, "
    "and cuts cost 28% where they cut nothing. A GPT-5.6 guard costs <b>more</b> than not caching (136%).",
    "<b>Router:</b> barely. A router trained on the small model's own record recovers 65% of the quality gap "
    "vs Jev's 61% (random mix 50%); GPT-5.6 is at chance (53%).",
    "<b>Open:</b> your 100-case label audit (cache guard), and whether to run one more agent-control experiment.",
]
story.append(box([para("TL;DR", "boxh")] + bullets(tldr, "boxbody"), YELLOW, YELLOW_LINE))
story.append(Spacer(1, 10))
story.append(para("Your first 5 minutes", "h2"))
story.append(code(
    f'git checkout main &amp;&amp; git pull  {C}# everything is on main</font><br/>'
    f'less results/replay/cacheguard-paired.md  {C}# cache-guard claims, paired CIs</font><br/>'
    f'less results/replay/router-routerbench/report/summary.md  {C}# router table + CIs</font><br/>'
    f'less DECISIONS.md  &nbsp;&nbsp;{C}# rows dated 2026-10-05</font>'))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 2: what the project asks
story.append(para("Part I · The project, explained", "h1"))
story.append(para("What we are testing", "h2"))
story.append(para(
    "LLM systems make many small decisions before (or instead of) generating text: which tool to call, whether a "
    "cached answer can be reused, which model should answer. Today these are usually made by the big model itself, "
    "which is slow and expensive. <b>Jev</b> (TypeSafe, via OpenRouter) is a model built only to <i>decide</i>: it "
    "returns a choice and a probability, never text. The project asks when that is worth it.", "body"))
story.append(para("The deciders (the same set at every decision point)", "h2"))
story.append(data_table(
    ["Decider", "What it is", "Role"],
    [
        ["<b>Jev</b>", "Decision-only model, API (~$0.00002 per decision, ~0.15 s)", "under test"],
        ["Kev-4B", "Open-weights Jev-like model, run on our A100", "open stand-in (not Jev)"],
        ["GPT-5.6", "Frontier LLM asked the same question as a forced choice", "ceiling"],
        ["GPT-OSS-20B / Qwen3-8B", "Small LLMs (API / our A100)", "cheap-LLM baseline"],
        ["Floor", "Small classifier trained on the task's own labelled data", "\"train your own\""],
        ["Task baselines", "Similarity threshold, vCache, always-small/large, random mix", "what people use today"],
    ],
    widths=[1.6 * inch, 3.6 * inch, 1.7 * inch],
))
story.append(Spacer(1, 8))
story.append(para("The three decision points", "h2"))
story.append(data_table(
    ["Decision point", "The decision", "Data"],
    [
        ["<b>Agent control</b>", "Which tool should an agent call next (or reply)?", "tau2-bench airline, 50 tasks"],
        ["<b>Cache guard</b>", "Can a cached answer be served for this new query?", "GSM-Plus, vCache LMArena + SearchQueries"],
        ["<b>Router</b>", "Small model (Mixtral) or large model (GPT-4)?", "RouterBench, 1,998 prompts"],
    ],
    widths=[1.5 * inch, 3.2 * inch, 2.2 * inch],
))
story.append(Spacer(1, 8))
story.append(para("How we measure", "h2"))
story.extend(bullets([
    "<b>Decision-only replay:</b> every decider answers the same saved situations, 3–5 times each, graded against "
    "a known right answer. Accuracy, $ per decision, latency, and GPU energy for local models.",
    "<b>In the loop</b> (agent control only): full episodes where the decision is acted on, graded by the benchmark.",
    "<b>Fair comparisons:</b> every number has a 95% bootstrap CI; claims are paired differences on the same items; "
    "anything tuned (thresholds, cascades, classifiers) is tuned on a separate dev split, never on test.",
]))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 3: agent control
story.append(para("Decision point 3 · Agent control", "h1"))
story.append(para(
    "An airline-support agent (tau2-bench) must pick its next action at each turn. Arm 0 replays 1,076 saved "
    "states; arms A–E run full episodes with GPT-5.6 as the executor G and the simulated customer.", "body"))
story.append(data_table(
    ["", "Jev", "GPT-5.6", "Jev -&gt; GPT-5.6 cascade", "GPT-OSS-20B", "Kev-4B"],
    [["Arm 0 accuracy", "81.4%", "88.5%†", "84.9%", "67.0%", "32.1%"],
     ["$ / decision", "1.7e-4", "3.8e-3", "8.2e-4", "3.1e-4", "local"]],
    widths=[1.3 * inch, 0.9 * inch, 0.9 * inch, 1.5 * inch, 1.1 * inch, 1.0 * inch],
))
story.append(para("† graded against its own reference actions: an upper bound.", "bodysmall"))
story.append(data_table(
    ["In the loop (250 episodes each)", "A: Jev -&gt; G", "B: G decides -&gt; G", "C: G alone", "D: GPT-OSS -&gt; G", "E: Kev -&gt; G"],
    [["Reward", "0.744", "0.796", "0.792", "0.692", "0.045"],
     ["Agent $ / success", "$0.048", "$0.176", "<b>$0.033</b>", "$0.043", "$0.476"]],
    widths=[1.7 * inch, 0.9 * inch, 1.2 * inch, 0.9 * inch, 1.2 * inch, 0.9 * inch],
))
story.append(Spacer(1, 6))
story.append(box([para(
    "<b>Why no win here:</b> the tool choice comes right before generation that happens anyway (G still writes the "
    "tool's arguments), so a separate decider only adds a step. Jev is far cheaper than G deciding separately "
    "(A − B: −$0.105 and −24 s per episode, −5.2 pts reward), but G's own single call (C) is cheaper still.", "boxbody")],
    PINK, PINK_LINE))
story.append(Spacer(1, 4))
story.append(figure(os.path.join(LOOP_FIG, "fig12_inloop_cost_vs_reward.png"), max_height=3.2 * inch))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 4: cache guard
story.append(para("Decision point 2 · Cache guard", "h1"))
story.append(para(
    "A semantic cache found an earlier query similar to the new one: <b>reuse</b> its answer, or <b>regenerate</b>? "
    "Here the decision <i>replaces</i> generation: a right reuse skips the model call. 2,000 test queries per dataset.", "body"))
story.append(data_table(
    ["Accuracy", "GSM-Plus<br/>(number changed?)", "LMArena<br/>(chat rewordings)", "SearchQueries<br/>(real searches)"],
    [
        ["<b>Jev</b>", "<b>93.3%</b>", "71.2%", "71.3%"],
        ["<b>Threshold -&gt; Jev cascade</b>", "<b>93.3%</b>", "<b>92.6%</b>", "70.2%"],
        ["GPT-5.6", "96.9%", "70.6%", "71.0%"],
        ["Similarity threshold (dev-tuned)", "66.1%", "<b>93.0%</b>", "70.3%"],
        ["vCache (delta = 0.05)", "66.1%", "58.6%", "54.0%"],
        ["Floor (trained on dev)", "81.7%", "90.9%", "67.8%"],
    ],
    widths=[2.4 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch],
))
story.append(Spacer(1, 6))
story.append(box([para(
    "<b>Reading it:</b> on GSM-Plus a changed number barely changes the wording, so every similarity method can only "
    "refuse to reuse (66% = never reuse); Jev reads the question and catches it (+27 pts, paired). On LMArena "
    "rewordings really are similar, so the free threshold wins; the cascade (threshold first, Jev only when unsure) "
    "ties it and keeps Jev's GSM-Plus win: the best design overall. SearchQueries: every decider sits at 70–72%, "
    "GPT-5.6 included, which points at noisy labels (your audit).", "boxbody")], GREEN, GREEN_LINE))
story.append(Spacer(1, 4))
story.append(data_table(
    ["$ per query vs no cache", "GSM-Plus (no cache $0.0016)", "LMArena (no cache $0.0084)"],
    [["Jev", "<b>72%</b>", "32%"], ["Threshold -&gt; Jev", "<b>72%</b>", "<b>6%</b>"], ["Threshold", "100%", "<b>5%</b>"],
     ["GPT-5.6 as the guard", "<b>136%</b> (worse than no cache)", "55%"]],
    widths=[2.4 * inch, 2.25 * inch, 2.25 * inch],
))
story.append(PageBreak())
story.append(figure(os.path.join(CG_FIG, "fig15_cacheguard_reuse_vs_error.png"), max_height=3.6 * inch,
                    caption="Figure 15. Up and to the left is better. On GSM-Plus every LLM decider sits far above the "
                            "similarity curves; on SearchQueries everything sits on the threshold curve."))
story.append(Spacer(1, 6))
story.append(figure(os.path.join(CG_FIG, "fig16_cacheguard_accuracy.png"), max_height=3.4 * inch))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 6: router
story.append(para("Decision point 1 · Router", "h1"))
story.append(para(
    "Send each prompt to the small model (Mixtral-8x7B) or the large one (GPT-4, 10–50× the cost)? RouterBench "
    "records both models' graded answers, so only the decisions are paid. Always-small scores 0.589, always-large "
    "0.792; 28% of prompts need the large model. <b>APGR</b> = share of that gap a router recovers, averaged over "
    "every budget; a random mix scores 0.5.", "body"))
story.append(data_table(
    ["Router", "APGR [95% CI]", "− Jev [95% CI]", "Own choice: sent large"],
    [
        ["Floor (trained on 20k RouterBench prompts)", "<b>0.649</b> [0.621, 0.678]", "+0.040 [+0.001, +0.070]", "3.9%"],
        ["<b>Jev</b>", "<b>0.609</b> [0.585, 0.642]", "—", "0%"],
        ["Kev-4B", "0.582 [0.553, 0.609]", "−0.027 [−0.055, −0.007]", "0%"],
        ["GPT-OSS-20B", "0.546 [0.516, 0.576]", "−0.063 [−0.102, −0.034]", "4.7%"],
        ["GPT-5.6", "0.529 [0.510, 0.568]", "−0.080 [−0.106, −0.045]", "2.3%"],
        ["Qwen3-8B", "0.531 [0.488, 0.540]", "−0.078 [−0.130, −0.067]", "20.6%"],
    ],
    widths=[2.6 * inch, 1.6 * inch, 1.6 * inch, 1.1 * inch],
))
story.append(Spacer(1, 6))
story.append(box([para(
    "<b>Why no clear win:</b> routing asks \"will <i>this</i> small model get this right?\", and that depends on "
    "Mixtral's particular weaknesses, which are not visible in the prompt. Only a router trained on Mixtral's own "
    "record does better than Jev, and only just (+0.04, CI barely above 0). Jev is the best <i>untrained</i> router "
    "(8 pts ahead of GPT-5.6), but its own choice is always \"small\": using it needs a threshold tuned on dev.",
    "boxbody")], BLUE, BLUE_LINE))
story.append(Spacer(1, 4))
story.append(figure(os.path.join(RT_FIG, "fig17_router_pgr.png"), max_height=3.6 * inch))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 7: the thesis
story.append(para("Putting it together", "h1"))
story.append(data_table(
    ["Decision point", "Decision replaces generation?", "Decider sees what the cheap option can't?", "Pays off?"],
    [
        ["Agent control", "No: G generates anyway", "—", "No (G's single call cheapest)"],
        ["Cache guard: GSM-Plus", "Yes", "Yes: the changed number", "<b>Yes</b> (93% vs 66%; −28% cost)"],
        ["Cache guard: LMArena", "Yes", "No: similarity already sees it", "Threshold wins; cascade ties it"],
        ["Router", "Yes", "No: Mixtral's weaknesses aren't in the prompt", "Barely (trained router best)"],
    ],
    widths=[1.6 * inch, 1.7 * inch, 2.1 * inch, 1.5 * inch],
))
story.append(Spacer(1, 8))
story.append(box([para(
    "<b>The thesis:</b> a cheap standalone decider pays off when its decision <b>replaces</b> generation <b>and</b> it "
    "can see something the cheap alternative cannot. Two corollaries: (1) a frontier model is a poor decider for "
    "these jobs: as a cache guard it costs more than answering, and as a router it is at chance; (2) the best "
    "deployment is a <b>cascade</b>: the free rule decides the clear cases, the decider only the ambiguous ones.",
    "boxbody")], YELLOW, YELLOW_LINE))
story.append(Spacer(1, 8))
story.append(para("Caveats the paper must state", "h2"))
story.extend(bullets([
    "Kev is an open reproduction of the System One idea, not Jev's weights.",
    "GPT-5.6's agent-control accuracy is graded against its own trajectories (an upper bound).",
    "LMArena and SearchQueries labels were made by GPT-4.1-nano; scores there are provisional until the label audit.",
    "RouterBench's models are from 2023; the router predicts <i>their</i> recorded correctness.",
    "Local deciders count as $0 per decision; their cost is GPU energy (reported separately).",
]))
story.append(PageBreak())

# =============================================================== PART II: the usual handoff
def report_table(path: str, heading: str):
    """Rows of the markdown table under `heading` in a report, as lists of cells (header first)."""
    lines = open(os.path.join(ROOT, path)).read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(heading))
    rows = []
    for l in lines[start + 1:]:  # only the first table under the heading: stop at its end
        if l.startswith("|"):
            rows.append(l)
        elif rows:
            break
    rows = [r for r in rows if not set(r.replace("|", "").strip()) <= set("-")]
    # The handwriting font has no arrow glyph: write arrows as "->", like the rest of the handoff.
    return [[c.strip().replace("−", "-").replace("→", "-&gt;") for c in r.strip("|").split("|")] for r in rows]


# ---------------------------------------------------------------- Page 8: where we are
story.append(para("Part II · Handoff since #6", "h1"))
story.append(para("Where we are", "h2"))
story.append(status_grid(
    ["Step", "What", "Status"],
    [
        ["Agent control", "arm 0, U4 in-loop A–E, U5 figures 1–14", "DONE (handoffs #4–#6)"],
        ["CG1–CG6, CG8", "cache-guard streams, question, harness, baselines, full run, regeneration cost, figs 15–16", "DONE"],
        ["CG7", "label audit of 100 cases (results/replay/cacheguard-label-audit.csv)", "TODO — needs your hand verdicts"],
        ["R1–R6", "router stream, question, harness, floor, full run, fig 17", "DONE"],
        ["Rigor pass", "router APGR CIs + dev-tuned operating points; cache-guard paired CIs", "DONE"],
        ["Paper prose", "from figures 1–17 and DECISIONS.md", "TODO"],
    ],
    widths=[1.3 * inch, 3.9 * inch, 1.7 * inch],
))
story.append(Spacer(1, 8))
story.append(para("Spend since #6 (OpenRouter)", "h2"))
story.append(data_table(
    ["Run", "Cost"],
    [["Cache guard: pilot + full decisions (3 datasets)", "$24.5"], ["Cache guard: regeneration cost (CG6)", "$2.0"],
     ["Router: pilot + full + dev runs", "~$8.4"], ["<b>Total</b>", "<b>~$35</b>"]],
    widths=[5.0 * inch, 1.9 * inch],
))
story.append(para("Balance left ≈ $21. Local runs (Kev-4B, Qwen3-8B, floor, cross-encoder, vCache) cost GPU time only.", "bodysmall"))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 9: significance
story.append(para("Significance (the claims, paired)", "h1"))
story.append(para("Cache guard: paired differences on the same 2,000 test queries, bootstrap over answer classes; "
                  "* = 95% CI excludes 0.", "body"))
for ds in ("gsmplus", "lmarena", "searchqueries"):
    t = report_table("results/replay/cacheguard-paired.md", f"## {ds}")
    story.append(para({"gsmplus": "GSM-Plus", "lmarena": "LMArena", "searchqueries": "SearchQueries"}[ds], "h2"))
    story.append(data_table(t[0], t[1:], widths=[2.3 * inch, 0.8 * inch, 1.9 * inch, 1.9 * inch]))
story.append(Spacer(1, 10))
story.append(para("Router: a deployable operating point", "h1"))
story.append(para("Each router's threshold on P(large) is set on the <b>dev</b> split so ~30% of prompts go to GPT-4 "
                  "(28% truly need it), then applied unchanged to test. Gain is over a random mix sending the same share.", "body"))
t = report_table("results/replay/router-routerbench/report/summary.md", "## Dev-tuned operating point")
story.append(data_table(t[0], t[1:], widths=[1.6 * inch, 0.8 * inch, 0.9 * inch, 1.4 * inch, 1.4 * inch, 0.8 * inch]))
story.append(Spacer(1, 8))
story.append(para("Router: APGR with paired differences", "h2"))
t = report_table("results/replay/router-routerbench/report/summary.md", "## APGR with 95% CI")
story.append(data_table(t[0], t[1:], widths=[1.6 * inch, 1.35 * inch, 1.35 * inch, 1.3 * inch, 1.3 * inch]))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 11: next + gotchas
story.append(para("What's next", "h1"))
story.extend(bullets([
    "<b>Label audit (CG7, you, ~1 h):</b> fill <font face=\"Courier\" size=9>your_verdict</font> for the 100 cases, "
    "ideally before reading the two \"says\" columns. Then: label error rate and corrected LMArena / SearchQueries scores.",
    "<b>Optional experiment (~$15–20):</b> the in-loop Jev -&gt; GPT-5.6 cascade for agent control (arm 0 says it recovers "
    "half of Jev's gap; in the loop it might close A's 5-pt deficit at near C's cost). Needs a small cascade arm in "
    "<font face=\"Courier\" size=9>run_inloop.py</font>.",
    "<b>Paper prose</b> from figures 1–17, the significance tables and DECISIONS.md.",
]))
story.append(Spacer(1, 6))
story.append(para("Gotchas we hit this round", "h2"))
story.extend(bullets([
    "<b>GTE-large-en-v1.5 under transformers 5</b> needs three shims (build from config, restore rope_scaling, supply "
    "get_extended_attention_mask); our embeddings are checked functionally against vCache's (99.7% same-class NN both).",
    "<b>vCache's code is CC BY-NC-ND:</b> we drive it unmodified from its own env "
    "(<font face=\"Courier\" size=9>/scratch/.../dwg-data/vcache_env</font>), never copy it.",
    "<b>RouterBench ships pickles:</b> inspected with pickletools (pandas/numpy only) before loading once; kept as parquet.",
    "<b>Labels can cap scores:</b> on SearchQueries every decider, GPT-5.6 included, hits 70–72%; the first audit cases "
    "show GPT-4.1-nano artifacts and plain label errors.",
    "<b>A frontier model is a self-defeating guard:</b> asking GPT-5.6 \"reuse?\" costs more than answering.",
    "<b>Session restarts</b> can re-run committed work; check <font face=\"Courier\" size=9>git log</font> first.",
]))
story.append(Spacer(1, 6))
story.append(para("New files this round", "h2"))
story.append(code(
    f"src/dwg/cacheguard.py, src/dwg/router.py &nbsp;{C}# the two decision points' questions</font><br/>"
    f"scripts/build_cacheguard_streams.py, build_router_streams.py &nbsp;{C}# data</font><br/>"
    f"scripts/replay_decisions.py --task cacheguard|router &nbsp;{C}# the deciders</font><br/>"
    f"scripts/cacheguard_{{crossencoder,floor,vcache,regen_cost,audit}}.py, router_floor.py &nbsp;{C}# baselines</font><br/>"
    f"scripts/analyze_cacheguard.py, compare_cacheguard.py, analyze_router.py &nbsp;{C}# analysis</font><br/>"
    f"scripts/make_cacheguard_figures.py &nbsp;{C}# figs 15-16 (fig 17 in analyze_router.py)</font><br/>"
    f"results/states/cacheguard-*.jsonl, router-routerbench.jsonl; results/replay/cacheguard-*, router-*"))

doc = SimpleDocTemplate(
    os.path.join(ROOT, "DWG_Handoff_7.pdf"),
    pagesize=LETTER,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    topMargin=0.7 * inch, bottomMargin=0.65 * inch,
    title="DWG Handoff 7",
)
doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print("wrote DWG_Handoff_7.pdf")
