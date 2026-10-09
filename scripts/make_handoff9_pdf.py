#!/usr/bin/env python3
"""Build DWG_Handoff_9.pdf in the style of handoff #8: results of the cache-guard v2 run (query-only
question, corrected labels; DECISIONS.md 2026-10-08). Numbers from results/replay/cacheguard-*/report/
summary.md and cacheguard-paired.md; figures from make_cacheguard_figures.py. Fonts from $DWG_FONT_DIR (default /scratch/gilbreth/$USER/dwg-data/fonts).
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
    canvas.drawString(0.6 * inch, 0.4 * inch, "DWG handoff #9 · continuing from handoff #8 (commit 8551693)")
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



# ---------------------------------------------------------------- Page 1: cover + TL;DR + headline table
story.append(para("Deciding Without Generating · handoff #9 · 2026-10-08", "kicker"))
story.append(Spacer(1, 2))
story.append(para("Handoff #9: cache guard v2 results", "title"))
story.append(para(
    "The re-run asked for in handoff #8 is finished: every cache-guard decider, on all three datasets, with the "
    "query-only question and the corrected labels. Results, figures 15–16 and the paired tests are committed to main.",
    "subtitle"))
tldr = [
    "<b>Headline:</b> Jev ties the free similarity threshold where similarity works (LMArena) and beats it where it "
    "does not: +27.2 points on GSM-Plus, +4.4 on SearchQueries (both significant).",
    "<b>Best overall:</b> the threshold -&gt; Jev cascade is best or tied-best on all three datasets "
    "(93.3 / 97.4 / 85.7%). On LMArena it asks Jev on only 3% of queries.",
    "<b>Jev vs frontier:</b> Jev matches GPT-5.6 on SearchQueries (85.6 vs 85.2, tie) and beats it on LMArena "
    "(96.3 vs 91.2) at about 1/50 of the price per decision. GPT-5.6 is ahead only on GSM-Plus (+2.6).",
    "<b>v1 was wrong:</b> handoff #7's \"the threshold wins on realistic traffic\" came from the old question (deciders "
    "graded the stored answer) and the noisy vCache labels. Do not use the handoff #7 cache-guard numbers.",
    "<b>Cost:</b> $21.1 on OpenRouter. Balance left is about $1. Nothing is running.",
]
story.append(box([para("TL;DR", "boxh")] + bullets(tldr, "boxbody"), YELLOW, YELLOW_LINE))
story.append(Spacer(1, 10))
story.append(para("Test accuracy (2,000 queries per dataset; 95% CI in the reports)", "h2"))
story.append(data_table(
    ["decider", "GSM-Plus", "LMArena", "SearchQueries", "$/decision"],
    [
        ["<b>Jev</b>", "93.3", "96.3", "85.6", "~2e-5"],
        ["<b>Threshold -&gt; Jev cascade</b>", "93.3", "<b>97.4</b>", "<b>85.7</b>", "&lt;= 2e-5"],
        ["GPT-5.6", "<b>96.0</b>", "91.2", "85.2", "~1e-3"],
        ["GPT-OSS-20B", "95.0", "93.3", "83.6", "~4e-5"],
        ["Kev-4B (local)", "88.1", "96.9", "85.4", "local"],
        ["Qwen3-8B (local)", "86.3", "95.7", "84.8", "local"],
        ["Similarity threshold (dev-tuned)", "66.1", "96.9", "81.2", "free"],
        ["Floor (trained on corrected dev)", "81.7", "95.7", "77.1", "free"],
        ["vCache (delta 0.05)", "66.1", "54.6", "50.3", "free"],
    ],
    widths=[2.4 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch, 1.3 * inch]))
story.append(para("Reuse is correct for 34% of GSM-Plus, 93% of LMArena and 58% of SearchQueries test queries, so "
                  "\"always reuse\" scores 34 / 93 / 58. vCache is scored on its own labels (it can serve a different "
                  "cached entry than the one we relabelled).", "bodysmall"))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 2: figure 16 + paired tests
story.append(para("Figure 16 · accuracy per dataset", "h1"))
story.append(figure(os.path.join(CG_FIG, "fig16_cacheguard_accuracy.png"), max_height=3.0 * inch,
                    caption="Bars are test accuracy; whiskers are 95% CIs clustered by class (a SearchQueries id_set or "
                            "a GSM-Plus seed question), so near-duplicate queries are not counted as independent."))
story.append(Spacer(1, 4))
story.extend(bullets([
    "<b>GSM-Plus</b> (math variants: a changed number changes the answer): similarity cannot see the difference, so the "
    "threshold and vCache never reuse (66.1% = always regenerate). Every model reading the queries does far better.",
    "<b>LMArena</b> (paraphrased chat prompts, 93% reusable): similarity already works; Jev, Kev and the threshold are within "
    "noise of each other. GPT-5.6 is the weakest LLM here because it regenerates too often (8.4% needless regenerations).",
    "<b>SearchQueries</b> (short web searches): all deciders reading the queries sit at 84–86%; the threshold is 81.2%, "
    "and gets there only by serving a wrong answer on 14.4% of queries (Jev: 3.8%).",
]))
story.append(para("Paired differences (same queries, bootstrap over classes)", "h2"))
story.append(data_table(
    ["dataset", "a - b", "accuracy diff [95% CI]", "wrong-reuse diff [95% CI]"],
    [
        ["GSM-Plus", "Jev - threshold", "<b>+27.2*</b> [+25.5, +29.1]", "+0.8* [+0.3, +1.4]"],
        ["GSM-Plus", "Jev - floor", "<b>+11.7*</b> [+10.1, +13.3]", "-1.7* [-2.5, -0.9]"],
        ["GSM-Plus", "Jev - Kev-4B", "+5.2* [+4.0, +6.6]", "-4.2* [-5.2, -3.2]"],
        ["GSM-Plus", "GPT-5.6 - Jev", "+2.6* [+1.9, +3.4]", "-0.3 [-0.6, +0.0]"],
        ["LMArena", "threshold - Jev", "+0.6 [-0.4, +1.6] (tie)", "+1.7* [+1.2, +2.3]"],
        ["LMArena", "cascade - threshold", "<b>+0.5*</b> [+0.2, +0.9]", "-0.4* [-0.6, -0.1]"],
        ["LMArena", "Kev-4B - Jev", "+0.6 [-0.3, +1.4] (tie)", "+0.7* [+0.3, +1.1]"],
        ["SearchQueries", "Jev - threshold", "<b>+4.4*</b> [+2.3, +6.4]", "<b>-10.6*</b> [-12.1, -9.1]"],
        ["SearchQueries", "Jev - floor", "+8.5* [+6.5, +10.5]", "-8.8* [-10.2, -7.3]"],
        ["SearchQueries", "GPT-5.6 - Jev", "-0.4 [-1.5, +0.8] (tie)", "-2.3* [-3.1, -1.6]"],
    ],
    widths=[1.2 * inch, 1.6 * inch, 2.05 * inch, 2.05 * inch]))
story.append(para("Points; * = the 95% CI excludes 0. A negative wrong-reuse difference means <i>a</i> serves fewer wrong "
                  "cached answers. Full table: results/replay/cacheguard-paired.md.", "bodysmall"))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 3: figure 15 + v1 vs v2
story.append(para("Figure 15 · how much is reused vs. how often it is wrong", "h1"))
story.append(figure(os.path.join(CG_FIG, "fig15_cacheguard_reuse_vs_error.png"), max_height=2.6 * inch,
                    caption="Each point is one decider; the lines are the similarity threshold and the cross-encoder at "
                            "every possible cut-off. Up and to the left is better: more cache hits, fewer wrong answers served. "
                            "The dotted line is the share of queries where reuse is correct."))
story.append(Spacer(1, 4))
story.extend(bullets([
    "<b>A point above the line beats every threshold setting</b>, not just the dev-tuned one. On GSM-Plus all query-reading "
    "deciders are far above it; on SearchQueries Jev, GPT-5.6 and GPT-OSS sit above it; on LMArena the LLM deciders sit above it "
    "at the low-error end.",
    "<b>vCache</b> (the star) is very cautious: it rarely serves a wrong answer but regenerates almost half the reusable "
    "queries on LMArena and SearchQueries, so its accuracy is the lowest.",
]))
story.append(para("What changed from v1 (handoff #7) to v2 (this run)", "h2"))
story.append(data_table(
    ["accuracy", "GSM-Plus v1 -&gt; v2", "LMArena v1 -&gt; v2", "SearchQueries v1 -&gt; v2"],
    [
        ["Jev", "93.3 -&gt; 93.3", "71.2 -&gt; <b>96.3</b>", "71.3 -&gt; <b>85.6</b>"],
        ["GPT-5.6", "96.9 -&gt; 96.0", "70.6 -&gt; 91.2", "71.0 -&gt; 85.2"],
        ["Threshold (dev-tuned)", "66.1 -&gt; 66.1", "92.9 -&gt; 96.9", "70.4 -&gt; 81.2"],
        ["Floor", "81.7 -&gt; 81.7", "90.9 -&gt; 95.7", "67.8 -&gt; 77.1"],
    ],
    widths=[1.6 * inch, 1.7 * inch, 1.7 * inch, 1.9 * inch]))
story.extend(bullets([
    "<b>Question (LMArena):</b> v1 asked whether the stored answer was fully correct, so Jev and GPT-5.6 refused to reuse "
    "answers they judged imperfect, even for identical prompts. Asking only \"same request?\" fixed that: +25 points for Jev.",
    "<b>Labels (SearchQueries, LMArena):</b> the corrected labels lift every method, the threshold included. Jev's lead over "
    "the threshold on SearchQueries is real under the corrected labels (+4.4*), and it was a tie (+0.9) under the old ones.",
    "<b>GSM-Plus</b> labels did not change and the old question rarely mattered there, so its numbers barely moved.",
]))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 4: run notes, status, next
story.append(para("What happened during the run", "h1"))
story.extend(bullets([
    "<b>Complete:</b> Jev, Kev-4B, Qwen3-8B 10,000 decisions per dataset (5 repeats x 2,000), GPT-5.6 6,000 (x3), "
    "GPT-OSS-20B 5x. Failures are at most 0.4% (GPT-OSS 25–41 per dataset, GPT-5.6 2 on SearchQueries); Jev has none.",
    "<b>Fix, 284ace2:</b> <font face=\"Courier\" size=9>cacheguard_api.slurm</font> now sets per-dataset $/call estimates. "
    "The archived v1 folders left no cost history, so the spending guard would have refused every job.",
    "<b>Credit:</b> GSM-Plus GPT-5.6 was refused by the guard at a $7.87 balance; it was re-run in two halves with "
    "<font face=\"Courier\" size=9>--limit</font> (the guard's split rule): $6.67, 0 errors.",
    "<b>Cluster:</b> Gilbreth maintenance stalled standby for days, so jobs moved to the group's normal QoS (A100-80GB, "
    "same hardware as before). The dependent analysis job was cancelled by the scheduler, so its commands were run by hand.",
    "<b>Jev overload:</b> 13 SearchQueries calls hit HTTP 529 (Jev overloaded). These were infra errors, retried on resume, "
    "and all succeeded.",
    "<b>Git:</b> a session restart replayed the last steps, which left two commits with the same message (7d077cd, 0bc01a3) "
    "and duplicate DECISIONS rows, later merged (88dde32). The data is not affected.",
]))
story.append(para("Where we are", "h2"))
story.append(status_grid(
    ["Step", "What", "Status"],
    [
        ["Agent control", "arm 0, U4 in-loop A–E, U5 figures 1–14", "DONE (handoffs #4–#6)"],
        ["Router", "R1–R6, rigor pass, figure 17", "DONE (handoff #7)"],
        ["Cache guard v2", "query-only question, corrected labels, all deciders, paired tests, figures 15–16", "DONE (this handoff)"],
        ["Label spot-check", "human check of a sample of the corrected labels", "TODO — needs a person"],
        ["Paper", "cache-guard tables, figures 15–16, claims and prose from these reports", "TODO"],
    ],
    widths=[1.3 * inch, 3.9 * inch, 1.7 * inch]))
story.append(Spacer(1, 6))
story.append(para("What's next", "h2"))
story.extend(bullets([
    "<b>Human spot-check:</b> a person (not an LLM) labels about 50 changed + 50 unchanged pairs per dataset (LMArena, "
    "SearchQueries) without seeing either label; report agreement with the corrected and with the original labels.",
    "<b>Paper:</b> replace every cache-guard number from handoff #7 with the v2 reports; state the query-only assumption "
    "(handoff #8, page 3) and the label write-up (results/label-corrections/README.md).",
    "<b>Credit:</b> load OpenRouter before any new paid run. Repeating this whole run costs about $21.",
]))
story.append(para("Where the results are", "h2"))
story.append(code(
    f"results/replay/cacheguard-&lt;dataset&gt;/report/summary.md &nbsp;{C}# per-dataset tables</font><br/>"
    f"results/replay/cacheguard-paired.md &nbsp;{C}# paired differences</font><br/>"
    f"results/replay/cacheguard-paper_figures/ &nbsp;{C}# fig15, fig16 (png + pdf), points.json</font><br/>"
    f"results/replay/cacheguard-*/v1-answer-question/ &nbsp;{C}# old runs, not used</font><br/>"
    f"DECISIONS.md &nbsp;{C}# row dated 2026-10-08</font>"))

doc = SimpleDocTemplate(
    os.path.join(ROOT, "DWG_Handoff_9.pdf"),
    pagesize=LETTER,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    topMargin=0.7 * inch, bottomMargin=0.65 * inch,
    title="DWG Handoff 9",
)
doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print("wrote DWG_Handoff_9.pdf")
