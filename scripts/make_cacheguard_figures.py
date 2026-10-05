#!/usr/bin/env python3
"""Cache-guard paper figures (PLAN.md CG8): for each dataset, how much a decider reuses vs. how
often it serves a wrong answer, plus accuracy and cost side by side.

Fig 15 (one panel per dataset): x = wrong-reuse rate (share of all queries served a wrong
cached answer), y = reuse rate (share of queries answered from the cache). Up and to the left
is better. The similarity threshold and the cross-encoder are curves (their tau swept over the
test split); every other decider is one point: Jev, the LLMs and Kev averaged over repeats,
vCache at its delta, the floor at 0.5, the threshold -> Jev cascade at its dev-tuned band.
Fig 16: accuracy with 95% CI per decider and dataset, $/decision on a second figure (no dual
axes). Reads the same files as analyze_cacheguard.py and reuses its helpers, so numbers match
report/summary.md.

Colors follow make_paper_figures.py (Jev blue, GPT-5.6 gold, GPT-OSS orange, Qwen3 dark orange,
Kev green, Jev cascade magenta); baselines are greys and purple. Every point is labelled.

Usage: python3 scripts/make_cacheguard_figures.py   ->  results/replay/cacheguard-paper_figures/
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_cacheguard as ac  # noqa: E402
from dwg.runfiles import load_outcomes  # noqa: E402
from dwg.stats import bootstrap_ci  # noqa: E402

DATASETS = [("gsmplus", "GSM-Plus"), ("lmarena", "LMArena"), ("searchqueries", "SearchQueries")]
INK, INK_2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
POINT = {  # decider key -> (label, color)
    "jev": ("Jev", "#2a78d6"),
    "llm:openrouter/openai/gpt-5.6-sol": ("GPT-5.6", "#c9a000"),
    "llm:openrouter/openai/gpt-oss-20b": ("GPT-OSS-20B", "#eb6834"),
    "llm:local/qwen3-8b": ("Qwen3-8B", "#a8431c"),
    "kev-4b": ("Kev-4B", "#1baf7a"),
    "cascade": ("Threshold→Jev", "#cf3f8a"),
    "floor": ("Floor (trained)", "#7d5fd6"),
    "vcache": ("vCache δ=0.05", "#4a4946"),
    "threshold": ("Threshold (dev-tuned)", "#8a8984"),
}
# Marker shape per decider too, so identity never rests on color alone (points cluster closely).
MARKER = {"jev": "o", "llm:openrouter/openai/gpt-5.6-sol": "D", "llm:openrouter/openai/gpt-oss-20b": "s",
          "llm:local/qwen3-8b": "v", "kev-4b": "^", "cascade": "P", "floor": "X", "vcache": "*", "threshold": "h"}
CURVE = {"threshold": ("Similarity threshold", "#8a8984", "-"), "cross-encoder": ("Cross-encoder", "#8a8984", "--")}


def _style(ax, xlabel=None, ylabel=None):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_2, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_2, fontsize=10)


def dataset_points(name: str) -> dict:
    """Per decider: (wrong-reuse rate, reuse rate, accuracy CI, $/decision) on the test split."""
    run = ROOT / f"results/replay/cacheguard-{name}"
    meta = json.loads((run / "meta.json").read_text())
    stream = [json.loads(line) for p in meta["states"] for line in open(ROOT / p) if line.strip()]
    by_id = {ac.state_id(r): r for r in stream}
    test = [r for r in stream if r["split"] == "test"]
    dev = [r for r in stream if r["split"] == "dev"]
    correct = np.array([r["reuse_correct"] for r in test])
    clusters = np.array([r["query_class"] for r in test])
    out = {"curves": {}, "points": {}}

    def point(reuse, right, clus, usd):
        s = ac.summarize(np.asarray(reuse), np.asarray(right), np.asarray(clus))
        return dict(wrong=s["wrong_reuse"][0], reuse=s["reuse_rate"], acc=s["accuracy"], usd=usd)

    by_decider = defaultdict(list)
    for o in load_outcomes(run):
        if o["state_id"] in by_id and o["error"] is None:
            by_decider[o["decider"]].append(o)
    for d, calls in by_decider.items():
        calls = [o for o in calls if by_id[o["state_id"]]["split"] == "test"]
        if d in POINT and calls:
            costs = [o["cost_usd"] for o in calls if o.get("cost_usd") is not None]
            out["points"][d] = point([o["choice"] == "reuse" for o in calls],
                                     [by_id[o["state_id"]]["reuse_correct"] for o in calls],
                                     [by_id[o["state_id"]]["query_class"] for o in calls],
                                     float(np.mean(costs)) if costs else 0.0)
    casc = ac.cascade_rows(by_decider.get("jev", []), by_id, dev)
    if casc:
        c = casc[0]
        out["points"]["cascade"] = dict(wrong=c["wrong_reuse"][0], reuse=c["reuse_rate"], acc=c["accuracy"], usd=c["usd"] or 0.0)

    scores = {"threshold": {ac.state_id(r): r["similarity"] for r in stream}}
    for key, fname in (("cross-encoder", "scores-crossencoder.jsonl"), ("floor", "scores-floor.jsonl")):
        p = run / fname
        if p.exists():
            scores[key] = {json.loads(line)["state_id"]: json.loads(line)["score"] for line in open(p)}
    for key in ("threshold", "cross-encoder"):
        if key in scores:
            sc = np.array([scores[key][ac.state_id(r)] for r in test])
            taus = np.unique(np.quantile(sc, np.linspace(0, 1, 201)))
            out["curves"][key] = [(float(np.mean((sc >= t) & ~correct)), float(np.mean(sc >= t))) for t in taus] + [(0.0, 0.0)]
    # The threshold's own operating point for the accuracy chart: max dev accuracy (the curve shows the rest).
    tau = ac.pick_tau(np.array([r["similarity"] for r in dev]), np.array([r["reuse_correct"] for r in dev]))["max accuracy"]
    out["points"]["threshold"] = point(np.array([r["similarity"] for r in test]) >= tau, correct, clusters, 0.0)
    if "floor" in scores:
        sc = np.array([scores["floor"][ac.state_id(r)] for r in test])
        out["points"]["floor"] = point(sc >= 0.5, correct, clusters, 0.0)
    vp = run / "scores-vcache.jsonl"
    if vp.exists():
        vc = {json.loads(line)["state_id"]: json.loads(line) for line in open(vp)}
        rows = [r for r in test if ac.state_id(r) in vc]
        reuse = [vc[ac.state_id(r)]["reuse"] for r in rows]
        right = [vc[ac.state_id(r)]["served_correct"] if vc[ac.state_id(r)]["reuse"] else r["reuse_correct"] for r in rows]
        out["points"]["vcache"] = point(reuse, right, [r["query_class"] for r in rows], 0.0)
    out["base_rate"] = float(correct.mean())
    return out


def fig_curves(data, out_dir, plt):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (key, title) in zip(axes, DATASETS):
        d = data[key]
        for name, pts in d["curves"].items():
            label, color, ls = CURVE[name]
            xs, ys = zip(*sorted(pts))
            ax.plot(xs, ys, color=color, linestyle=ls, linewidth=1.6, label=label, zorder=2)
        ax.axhline(d["base_rate"], color=GRID, linewidth=1.2, linestyle=":", zorder=1)
        ax.annotate(f"reusable: {d['base_rate']:.0%}", (0.98, d["base_rate"]), xycoords=("axes fraction", "data"),
                    ha="right", va="bottom", fontsize=8, color=INK_2)
        for name, p in d["points"].items():
            if name == "threshold":
                continue  # drawn as the curve
            label, color = POINT[name]
            ax.scatter([p["wrong"]], [p["reuse"]], s=150 if MARKER[name] == "*" else 85, marker=MARKER[name],
                       color=color, edgecolor=BG, linewidth=1.2, zorder=4, label=label)
        ax.set_xlim(left=-0.005)
        ax.set_ylim(-0.02, 1.02)
        _style(ax, xlabel="Wrong-reuse rate (wrong cached answer served)", ylabel="Reuse rate" if key == "gsmplus" else None)
        ax.set_title(title, loc="left", fontsize=11, color=INK)
    # One shared legend below the panels (labels next to clustered points collide).
    handles, labels = {}, {}
    for ax in axes:
        for h, l in zip(*ax.get_legend_handles_labels()):
            handles.setdefault(l, h)
    fig.legend(list(handles.values()), list(handles), loc="lower center", ncol=5, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("Figure 15. Cache guard: reuse vs. wrong reuse (up and to the left is better)", x=0.01, ha="left",
                 fontsize=12, color=INK)
    fig.tight_layout(rect=[0, 0.1, 1, 0.95])
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"fig15_cacheguard_reuse_vs_error.{ext}", dpi=200, facecolor=BG,
                    metadata={"Software": None} if ext == "png" else {"CreationDate": None, "Producer": None})
    plt.close(fig)


def fig_accuracy(data, out_dir, plt):
    order = ["jev", "cascade", "llm:openrouter/openai/gpt-5.6-sol", "llm:openrouter/openai/gpt-oss-20b",
             "llm:local/qwen3-8b", "kev-4b", "floor", "vcache", "threshold"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
    for ax, (key, title) in zip(axes, DATASETS):
        pts = data[key]["points"]
        names = [n for n in order if n in pts]
        ys = np.arange(len(names))
        for y, n in zip(ys, names):
            m, lo, hi = pts[n]["acc"]
            ax.barh(y, m, color=POINT[n][1], height=0.6, zorder=2)
            ax.errorbar(m, y, xerr=[[m - lo], [hi - m]], fmt="none", ecolor=INK, capsize=3, zorder=3)
            ax.annotate(f"{m:.1%}", (hi, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=INK)
        ax.set_yticks(ys, [POINT[n][0] for n in names])
        ax.invert_yaxis()
        ax.set_xlim(0, 1.12)
        _style(ax, xlabel="Accuracy (reuse when right, regenerate when not)")
        ax.set_title(title, loc="left", fontsize=11, color=INK)
    fig.suptitle("Figure 16. Cache-guard accuracy with 95% CI (clustered by class)", x=0.01, ha="left", fontsize=12, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"fig16_cacheguard_accuracy.{ext}", dpi=200, facecolor=BG,
                    metadata={"Software": None} if ext == "png" else {"CreationDate": None, "Producer": None})
    plt.close(fig)


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = {key: dataset_points(key) for key, _ in DATASETS}
    out_dir = ROOT / "results/replay/cacheguard-paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_curves(data, out_dir, plt)
    fig_accuracy(data, out_dir, plt)
    (out_dir / "points.json").write_text(json.dumps(
        {k: {n: {kk: vv for kk, vv in p.items()} for n, p in v["points"].items()} for k, v in data.items()},
        indent=2, default=float))
    print(f"==> wrote fig15, fig16 (PNG+PDF) and points.json to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
