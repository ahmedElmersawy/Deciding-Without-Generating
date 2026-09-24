#!/usr/bin/env python3
"""Publication-quality cascade figure: accuracy, latency and cost vs. confidence threshold.

Reads the cascade simulation already computed by post_experiment_analysis.py (Phase D) —
no new data, just a dedicated figure for it. Also identifies the Pareto-optimal threshold(s)
(minimize latency & cost, maximize accuracy) and picks a single recommended operating point
via a normalized-distance-to-utopia heuristic among the frontier.

Usage:
    python3 scripts/make_cascade_figure.py results/replay/mock-pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

INK, INK_2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
KEV_COLOR, GPT_COLOR, CASCADE_COLOR = "#1baf7a", "#eb6834", "#7d5fd6"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    analysis = json.loads((args.run / "post_experiment_analysis.json").read_text())
    points = analysis["phase_d_calibration"]["cascade_kev4b_to_gptoss"]
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
    panels = [
        (axes[0], accs, "Blended accuracy (%)", None),
        (axes[1], lats, "Blended latency (ms)", "log"),
        (axes[2], costs, "Blended $/decision", "log"),
    ]
    for ax, ys, ylabel, scale in panels:
        ax.plot(thresholds, ys, color=INK_2, linewidth=1.2, linestyle="--", zorder=1)
        for t, y, on in zip(thresholds, ys, on_frontier):
            ax.scatter([t], [y], s=150 if on else 80, color=CASCADE_COLOR,
                       edgecolor=INK if on else "none", linewidth=1.4, zorder=3)
        if scale:
            ax.set_yscale(scale)
        _style(ax, ylabel=ylabel)
    # Mark the recommended operating point on all three panels.
    for ax in axes:
        ax.axvline(best["threshold"], color=INK, linewidth=1, linestyle=":", zorder=2)
    axes[0].annotate(f"recommended: t={best['threshold']:g}", (best["threshold"], best["blended_accuracy"] * 100),
                      xytext=(8, -14), textcoords="offset points", fontsize=9, color=INK)
    axes[0].annotate(f"Kev-4B alone (t=0)  ★ Pareto-optimal", (0.02, 0.90), xycoords="axes fraction",
                      fontsize=8, color=INK_2, style="italic")
    axes[-1].set_xlabel("Kev-4B confidence threshold (escalate to GPT-OSS-20B below this)", color=INK_2, fontsize=10)
    axes[0].set_title(
        "Cascade accuracy / latency / cost vs. confidence threshold\n"
        "(outlined markers = Pareto-optimal; simulated from replayed calls)",
        loc="left", fontsize=11.5, color=INK,
    )
    fig.tight_layout(rect=[0, 0, 0.98, 1])
    fig.savefig(out / "fig10_cascade_threshold_sweep.png", dpi=200, facecolor=BG, metadata={"Software": None})
    fig.savefig(out / "fig10_cascade_threshold_sweep.pdf", facecolor=BG, metadata={"CreationDate": None, "Producer": None})
    plt.close(fig)

    result = dict(
        pareto_optimal_thresholds=[p["threshold"] for p in frontier],
        dominated_thresholds=[t for t in thresholds if t not in frontier_t],
        recommended_threshold=best["threshold"],
        recommended_point=best,
    )
    (out / "cascade_recommendation.json").write_text(json.dumps(result, indent=2))
    print(f"==> wrote fig10_cascade_threshold_sweep.{{png,pdf}} and cascade_recommendation.json to {out}")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
