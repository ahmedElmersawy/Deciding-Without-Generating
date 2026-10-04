#!/usr/bin/env python3
"""Publication-quality cascade figure: accuracy, latency and cost vs. confidence threshold.

Reads the cascade simulation already computed by post_experiment_analysis.py (Phase D) —
no new data, just a dedicated figure for it. Also identifies the Pareto-optimal threshold(s)
(minimize latency & cost, maximize accuracy) and picks a single recommended operating point
via a normalized-distance-to-utopia heuristic among the frontier.

The headline cascade is Jev -> GPT-5.6 (`--cascade jev`, default, fig10); `--cascade kev` draws
the Kev-4B -> GPT-OSS-20B comparison sweep (fig10b). When the run also holds a LIVE cascade
replay at one threshold (calls-cascade-<fast>-t<t>.jsonl), its measured accuracy / mean latency /
$ are overlaid as an open marker, so the simulation can be checked against reality.

Usage:
    python3 scripts/make_cascade_figure.py results/replay/airline
    python3 scripts/make_cascade_figure.py results/replay/airline --cascade kev
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

INK, INK_2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
# Same colors as make_paper_figures.py: magenta = the Jev-led cascade, purple = the Kev-led one.
CASCADES = {
    "jev": dict(key="cascade_jev_to_gpt56", fast="Jev", target="GPT-5.6", color="#cf3f8a",
                live_prefix="cascade-jev-t", fig="fig10_cascade_threshold_sweep"),
    "kev": dict(key="cascade_kev4b_to_gptoss", fast="Kev-4B", target="GPT-OSS-20B", color="#7d5fd6",
                live_prefix="cascade-kev-4b-t", fig="fig10b_cascade_kev_threshold_sweep"),
}


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


def pareto_frontier(points: list[dict]) -> list[dict]:
    """Minimize latency, maximize accuracy (cost tracks latency monotonically here, so a
    2D accuracy/latency Pareto set also determines which thresholds are cost-dominated)."""
    by_lat = sorted(points, key=lambda p: p["blended_latency_ms"])
    frontier, best_acc = [], -1.0
    for p in by_lat:
        if p["blended_accuracy"] > best_acc:
            frontier.append(p)
            best_acc = p["blended_accuracy"]
    return frontier


def recommend(frontier: list[dict]) -> dict:
    """Normalized distance-to-utopia (min latency, min cost, max accuracy) among the
    frontier only — the single best-balanced operating point, not the whole frontier."""
    lat = np.array([p["blended_latency_ms"] for p in frontier])
    cost = np.array([p["blended_cost_usd_per_decision"] for p in frontier])
    acc = np.array([p["blended_accuracy"] for p in frontier])
    norm = lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else np.zeros_like(x)
    lat_n, cost_n, acc_n = norm(lat), norm(cost), norm(acc)
    dist = np.sqrt(lat_n**2 + cost_n**2 + (1 - acc_n) ** 2)
    return frontier[int(np.argmin(dist))]


def live_points(run: Path, prefix: str) -> list[dict]:
    """Measured accuracy / mean latency / mean $ of each live cascade replay in the run, one per
    threshold, counted like the rest of the analysis (dwg.runfiles.load_outcomes)."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from dwg.runfiles import load_outcomes

    by_decider = {}
    for r in load_outcomes(run):
        if r["decider"].startswith(prefix) and r["error"] is None:
            by_decider.setdefault(r["decider"], []).append(r)
    out = []
    for d, rows in sorted(by_decider.items()):
        costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
        out.append(dict(
            decider=d, threshold=float(d.removeprefix(prefix)), n=len(rows),
            accuracy=float(np.mean([r["correct"] for r in rows])),
            latency_ms=float(np.mean([r["latency_s"] for r in rows])) * 1000,
            cost=float(np.mean(costs)) if costs else 0.0,
        ))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--cascade", choices=sorted(CASCADES), default="jev")
    args = parser.parse_args()
    spec = CASCADES[args.cascade]
    CASCADE_COLOR = spec["color"]

    analysis = json.loads((args.run / "post_experiment_analysis.json").read_text())
    points = analysis["phase_d_calibration"].get(spec["key"])
    if not points:
        raise SystemExit(f"no {spec['key']} sweep in {args.run}/post_experiment_analysis.json; "
                         "run scripts/post_experiment_analysis.py first")
    live = live_points(args.run, spec["live_prefix"])
    frontier = pareto_frontier(points)
    frontier_t = {p["threshold"] for p in frontier}
    best = recommend(frontier)

    out = args.run / "paper_figures"
    out.mkdir(parents=True, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    thresholds = [p["threshold"] for p in points]
    accs = [p["blended_accuracy"] * 100 for p in points]
    lats = [p["blended_latency_ms"] for p in points]
    costs = [p["blended_cost_usd_per_decision"] for p in points]
    on_frontier = [t in frontier_t for t in thresholds]

    fig, axes = plt.subplots(3, 1, figsize=(7.5, 9), sharex=True)
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    panels = [
        (axes[0], accs, "Accuracy (%)", None, None),
        (axes[1], lats, "Mean latency per decision (ms)", "log", lambda v, _: f"{v:,.0f}"),
        (axes[2], costs, "$ per decision", "log", lambda v, _: f"${v:.4f}".rstrip("0")),
    ]
    for ax, ys, ylabel, scale, fmt in panels:
        ax.plot(thresholds, ys, color=INK_2, linewidth=1.2, linestyle="--", zorder=1)
        for t, y, on in zip(thresholds, ys, on_frontier):
            ax.scatter([t], [y], s=150 if on else 80, color=CASCADE_COLOR,
                       edgecolor=INK if on else "none", linewidth=1.4, zorder=3)
        if scale:
            ax.set_yscale(scale)
            ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
            ax.yaxis.set_minor_formatter(NullFormatter())
            ax.yaxis.set_major_formatter(FuncFormatter(fmt))
        _style(ax, ylabel=ylabel)
    # Live replays at a fixed threshold: measured, not simulated (open markers).
    for lp in live:
        for ax, y in zip(axes, (lp["accuracy"] * 100, lp["latency_ms"], lp["cost"])):
            ax.scatter([lp["threshold"]], [y], s=190, facecolors="none", edgecolors=INK, linewidth=1.6, zorder=4)
        axes[0].annotate(f"live run, t={lp['threshold']:g}: {lp['accuracy']*100:.1f}%",
                         (lp["threshold"], lp["accuracy"] * 100), xytext=(-12, 10), textcoords="offset points",
                         ha="right", fontsize=8.5, color=INK)
        axes[1].annotate(f"live: {lp['latency_ms']:.0f} ms", (lp["threshold"], lp["latency_ms"]),
                         xytext=(14, -4), textcoords="offset points", ha="left", fontsize=8.5, color=INK)
    # The dotted line marks the operating point actually used: the live run's threshold, which was
    # chosen on held-out tasks (DECISIONS.md 2026-10-02). The full-data distance-to-utopia pick
    # depends on the threshold grid (it normalizes over the frontier), so it is only reported in
    # the JSON, never drawn as "the" recommendation next to a live run.
    marked = live[0]["threshold"] if live else best["threshold"]
    for ax in axes:
        ax.axvline(marked, color=INK, linewidth=1, linestyle=":", zorder=2)
    if not live:
        axes[0].annotate(f"recommended: t={marked:g}", (marked, best["blended_accuracy"] * 100),
                         xytext=(8, -14), textcoords="offset points", fontsize=9, color=INK)
    axes[-1].set_xlabel(f"{spec['fast']} confidence threshold (escalate to {spec['target']} below this)",
                        color=INK_2, fontsize=10)
    axes[0].set_title(
        f"{spec['fast']} → {spec['target']} cascade: accuracy / latency / cost vs. threshold\n"
        "filled = simulated from standalone replays (outlined = Pareto-optimal);\n"
        "open ring = live run; dotted line = threshold in use",
        loc="left", fontsize=10.5, color=INK,
    )
    fig.tight_layout(rect=[0, 0, 0.98, 1])
    fig.savefig(out / f"{spec['fig']}.png", dpi=200, facecolor=BG, metadata={"Software": None})
    fig.savefig(out / f"{spec['fig']}.pdf", facecolor=BG, metadata={"CreationDate": None, "Producer": None})
    plt.close(fig)

    result = dict(
        pareto_optimal_thresholds=[p["threshold"] for p in frontier],
        dominated_thresholds=[t for t in thresholds if t not in frontier_t],
        recommended_threshold=best["threshold"],
        recommended_point=best,
        live_runs=live,
    )
    rec_name = "cascade_recommendation.json" if args.cascade == "jev" else f"cascade_recommendation_{args.cascade}.json"
    (out / rec_name).write_text(json.dumps(result, indent=2))
    print(f"==> wrote {spec['fig']}.{{png,pdf}} and {rec_name} to {out}")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
