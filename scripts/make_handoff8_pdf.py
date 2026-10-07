#!/usr/bin/env python3
"""Build DWG_Handoff_8.pdf in the style of handoff #7: the cache-guard re-run after the query-only
question and the label corrections (DECISIONS.md 2026-10-07). Numbers from results/label-corrections/
and the states meta files. Fonts from $DWG_FONT_DIR (default /scratch/gilbreth/$USER/dwg-data/fonts).
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
    canvas.drawString(0.6 * inch, 0.4 * inch, "DWG handoff #8 · continuing from handoff #7 (commit 2ba0121)")
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



# ---------------------------------------------------------------- Page 1: cover + TL;DR + the command
story.append(para("Deciding Without Generating · handoff #8 · 2026-10-07", "kicker"))
story.append(Spacer(1, 2))
story.append(para("Handoff #8: re-run the cache guard", "title"))
story.append(para(
    "Since #7 the cache guard changed in two ways: deciders now compare the two queries only, and the vCache labels "
    "were corrected. Every cache-guard decider has to be run again. One command does it, on Gilbreth.",
    "subtitle"))
tldr = [
    "<b>What you do:</b> <font face=\"Courier\" size=9>git pull</font>, then "
    "<font face=\"Courier\" size=9>bash scripts/cacheguard_v2_submit.sh</font>. It queues 11 jobs (API deciders, Kev-4B, "
    "Qwen3-8B, floor retrain) and one analysis job that waits for them. Then commit and push the results.",
    "<b>Cost:</b> OpenRouter only (Jev, GPT-OSS-20B, GPT-5.6). The last full run was $23.7 with longer prompts; "
    "this one should be less. Hard caps: about $18 per dataset, $54 total.",
    "<b>Change 1, the question:</b> deciders no longer see the cached answer. They judge whether the new query and the "
    "cached query are the same request. That is now a stated assumption of the paper.",
    "<b>Change 2, the labels:</b> Claude Opus 5.5 re-judged all 5,200 LMArena + SearchQueries pairs blind, in two "
    "passes. 156 LMArena (6.0%) and 409 SearchQueries (15.7%) labels changed. GSM-Plus untouched.",
    "<b>Why it matters:</b> on the old runs, correcting the labels alone lifts every decider on SearchQueries from "
    "~71% to 82–84%. The 71% ceiling was the labels, not the models.",
]
story.append(box([para("TL;DR", "boxh")] + bullets(tldr, "boxbody"), YELLOW, YELLOW_LINE))
story.append(Spacer(1, 10))
story.append(para("Your first 5 minutes", "h2"))
story.append(code(
    f'git checkout main &amp;&amp; git pull  {C}# needs commit 6ffa76c or later</font><br/>'
    f'source scripts/env.sh &amp;&amp; python3 scripts/check_connectivity.py  {C}# OpenRouter reachable, key set</font><br/>'
    f'bash scripts/cacheguard_v2_submit.sh  {C}# queues everything, prints job ids</font><br/>'
    f'squeue -u $USER  {C}# watch; logs in results/logs/</font>'))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 2: what gets run
story.append(para("What the script submits", "h1"))
story.append(data_table(
    ["job", "per dataset (lmarena, searchqueries, gsmplus)", "where", "$"],
    [
        ["cacheguard_api.slurm", "Jev x5 (test) + x5 (dev), GPT-OSS-20B x5, GPT-5.6 x3, then analyze_cacheguard.py", "A100 node, API calls", "capped: Jev $1+$1, OSS $2, GPT-5.6 $14"],
        ["kev_replay.slurm", "Kev-4B x5 on test, energy measured (KEV_MODEL=kev-4b)", "A100, local", "0"],
        ["llm_local_replay.slurm", "Qwen3-8B x5 on test via vLLM, energy measured", "A100, local", "0"],
        ["cacheguard_floor.slurm (once)", "floor classifier retrained on the corrected dev labels, all 3 datasets", "A100", "0"],
        ["dwg-cacheguard-v2-analysis (once)", "waits for all the above; per-dataset tables, compare_cacheguard.py (paired CIs), figures 15–16", "A100", "0"],
    ],
    widths=[1.55 * inch, 2.95 * inch, 1.1 * inch, 1.3 * inch]))
story.append(Spacer(1, 8))
story.extend(bullets([
    "<b>Fresh start:</b> the old decider runs moved to <font face=\"Courier\" size=9>results/replay/cacheguard-&lt;dataset&gt;/"
    "v1-answer-question/</font>. The analysis reads only the parent folder, so they are not counted.",
    "<b>Resumable:</b> if a job dies (time limit, 402, network), run the same script again: finished calls are kept and "
    "only the missing ones run. To redo one dataset: <font face=\"Courier\" size=9>DATASETS=lmarena bash "
    "scripts/cacheguard_v2_submit.sh</font>.",
    "<b>Kept as they were:</b> cross-encoder scores, vCache scores and the measured GPT-5.6 regeneration cost. They "
    "do not depend on the question. The floor is retrained because its dev labels changed.",
    "<b>Local jobs</b> get 4 h each (<font face=\"Courier\" size=9>LOCAL_TIME=06:00:00 bash ...</font> to raise it). "
    "Last round Qwen3-8B took ~0.4 s and Kev ~0.1 s per decision, 10,000 decisions per dataset.",
]))
story.append(Spacer(1, 6))
story.append(para("When everything has finished", "h2"))
story.append(code(
    f'less results/replay/cacheguard-lmarena/report/summary.md  {C}# also searchqueries, gsmplus</font><br/>'
    f'less results/replay/cacheguard-paired.md  {C}# paired differences with CIs</font><br/>'
    f'grep -h "failures" results/logs/dwg-cacheguard-*.out | tail  {C}# failure counts should be ~0</font><br/>'
    f'git add results/replay/cacheguard-* results/replay/cacheguard-paired.md<br/>'
    f'git commit -m "Cache guard v2: query-only question on corrected labels" &amp;&amp; git push'))
story.append(para("Check before committing: every decider has its full count in each summary (Jev, GPT-OSS, Kev-4B, "
                  "Qwen3-8B: 10,000 decisions; GPT-5.6: 6,000), and the failures column is near zero.", "bodysmall"))
story.append(PageBreak())

# ---------------------------------------------------------------- Page 3: what changed and why
story.append(para("Change 1 · the cache guard decides on the queries only", "h1"))
story.append(para(
    "Deciders now see two things: the new query and the cached query. They answer whether these are the same request. "
    "If they are, the cache returns the stored answer as it is; nobody checks that answer. The paper states this as "
    "an assumption, for three reasons:"))
story.extend(bullets([
    "<b>Cost:</b> reading the stored answer costs most of what the cache saves (LMArena answers run to thousands of tokens).",
    "<b>Correctness belongs elsewhere:</b> to the model that wrote the answer, and to the cache's TTL. With a TTL fitted to "
    "the use case the answer is likely still right; with the wrong one even a perfect answer goes stale (\"today's "
    "highest temperature in London\" cached for a week is wrong the next day, whatever model wrote it).",
    "<b>Disagreement is not error:</b> a decider that finds a stored answer incomplete or badly formatted, even one written "
    "by the same or another frontier model, is two experts disagreeing, not a wrong cache hit.",
]))
story.append(para(
    "How we found it: under the old question (\"reuse only if it fully and correctly answers\"), GPT-5.6 said regenerate "
    "on 24% of LMArena pairs whose two prompts were identical. It was grading the stored answers, e.g. \"Abigail has 7 "
    "sisters and 9 brothers; how many sisters does each brother have?\" stored as 7 (correct: 8).", "bodysmall"))
story.append(para("Change 2 · corrected vCache labels", "h1"))
story.append(data_table(
    ["dataset", "pairs reviewed", "flip candidates", "changed", "to reuse", "to regenerate"],
    [["LMArena", "2,600", "174", "156 (6.0%)", "122", "34"],
     ["SearchQueries", "2,600", "465", "409 (15.7%)", "267", "142"]],
    widths=[1.3 * inch, 1.1 * inch, 1.1 * inch, 1.2 * inch, 1.0 * inch, 1.2 * inch]))
story.append(Spacer(1, 6))
story.extend(bullets([
    "<b>How:</b> a guideline written first; pass 1 judged every pair blind (no label, no similarity, no decider output); "
    "a separate blind pass 2 re-judged each high-confidence disagreement; a label changed only when both agreed.",
    "<b>Who:</b> Claude Opus 5.5, an LLM. No human changed a label. A human spot-check is still to do (below).",
    "<b>Why vCache's labels fail:</b> SearchQueries groups are a transitive closure of GPT-4.1-nano pair judgements "
    "(A~B and B~C make A~C, though A's answer was written for A; small differences add up; one wrong link merges whole "
    "groups). LMArena variants inherit their seed's label with no check that they still ask the same thing.",
    "<b>Examples:</b> \"count blank cells\" vs \"count non blank cells\" was <i>same</i>; \"best workout plans for women\" "
    "vs \"best workout plan for women\" was <i>different</i>; CompTIA SY0-501 vs SY0-701 was <i>same</i>.",
    "<b>Where it lives:</b> streams keep <font face=\"Courier\" size=9>reuse_correct_original</font> and "
    "<font face=\"Courier\" size=9>label_source</font>; every change with both passes' reasons is in "
    "<font face=\"Courier\" size=9>results/label-corrections/</font>, whose README is the paper write-up.",
]))
story.append(para("Preview: the old runs re-scored on the corrected labels (test accuracy)", "h2"))
story.append(data_table(
    ["decider", "SearchQueries: vCache -> corrected", "LMArena: vCache -> corrected"],
    [["Jev", "0.713 -> 0.836", "0.712 -> 0.747"],
     ["GPT-5.6", "0.710 -> 0.829", "0.706 -> 0.724"],
     ["GPT-OSS-20B", "0.717 -> 0.822", "0.773 -> 0.814"],
     ["Kev-4B", "0.707 -> 0.844", "0.869 -> 0.911"],
     ["Qwen3-8B", "0.721 -> 0.835", "0.856 -> 0.903"]],
    widths=[1.6 * inch, 2.6 * inch, 2.6 * inch]))
story.append(para("LMArena barely moves for Jev and GPT-5.6 because the old runs still graded the stored answers. "
                  "The re-run with the query-only question is what tests that.", "bodysmall"))

# ---------------------------------------------------------------- Page 4: gotchas + next
story.append(para("Gotchas", "h1"))
story.extend(bullets([
    "<b>vCache is scored on its own labels.</b> vCache can serve a different cached entry than the one we relabelled, so its "
    "correctness still comes from vCache's classes. Say so next to its numbers.",
    "<b>Do not re-run the label correction.</b> The streams in git are already corrected; "
    "<font face=\"Courier\" size=9>apply_cacheguard_label_corrections.py</font> is idempotent, but there is no need to run it.",
    "<b>GSM-Plus labels did not change</b> (our exact numeric answers), but its deciders are re-run because the question changed.",
    "<b>OpenRouter balance:</b> each job stops paid calls at its cap or at the first 402; top up and re-run the script to resume.",
    "<b>Kev and Qwen run one call at a time</b> on a GPU of their own, for the energy numbers. Do not raise their workers.",
    "<b>Two tests in tests/test_labels.py</b> fail on machines without the tau2 data files. That is unrelated to this change.",
]))
story.append(Spacer(1, 6))
story.append(para("What's next (after your run)", "h1"))
story.extend(bullets([
    "<b>Human spot-check of the corrected labels:</b> a person labels a random sample (e.g. 50 changed + 50 unchanged pairs "
    "per dataset) without seeing either label; report agreement with the corrected and with the original labels.",
    "<b>Update the paper numbers</b> (cache-guard tables, figures 15–16, paired claims) from the new reports.",
    "<b>Paper text:</b> the assumption above, and the label write-up in results/label-corrections/README.md "
    "(source and citations, how we found it, why vCache's method fails, how ours fixes it, who corrected).",
]))
story.append(Spacer(1, 6))
story.append(para("New and changed files", "h2"))
story.append(code(
    f"src/dwg/cacheguard.py &nbsp;{C}# query-only question</font><br/>"
    f"results/label-corrections/ &nbsp;{C}# GUIDELINE.md, README.md, pass1/pass2/corrections per dataset</font><br/>"
    f"scripts/apply_cacheguard_label_corrections.py &nbsp;{C}# applies the two-pass rule</font><br/>"
    f"scripts/cacheguard_v2_submit.sh &nbsp;{C}# this run</font><br/>"
    f"results/replay/cacheguard-*/v1-answer-question/ &nbsp;{C}# archived old runs</font><br/>"
    f"DECISIONS.md &nbsp;{C}# rows dated 2026-10-07</font>"))

doc = SimpleDocTemplate(
    os.path.join(ROOT, "DWG_Handoff_8.pdf"),
    pagesize=LETTER,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    topMargin=0.7 * inch, bottomMargin=0.65 * inch,
    title="DWG Handoff 8",
)
doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print("wrote DWG_Handoff_8.pdf")
