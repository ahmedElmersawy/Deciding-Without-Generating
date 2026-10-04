#!/usr/bin/env python3
"""Paper figures for an in-loop run (PLAN.md U4/U5): reward per arm, cost vs. reward, pass^k,
and where each arm's dollars go. Reads the episodes and the report that
scripts/analyze_inloop.py writes (run it first), so every number matches report/summary.md.

Arm colors follow the decider's color in make_paper_figures.py (A Jev blue, B GPT-5.6 gold,
D GPT-OSS orange, E Kev-4B green); C has no separate decider, so it is the neutral baseline.

Usage:
    python3 scripts/analyze_inloop.py results/inloop/airline-frontier-gpt-5.6-sol
    python3 scripts/make_inloop_figures.py results/inloop/airline-frontier-gpt-5.6-sol
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

INK, INK_2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
ARM_NAME = {
    "A": "A: Jev → G",
    "B": "B: G decides → G",
    "C": "C: G alone",
    "D": "D: GPT-OSS → G",
    "E": "E: Kev-4B → G",
}
ARM_COLOR = {"A": "#2a78d6", "B": "#c9a000", "C": "#4a4946", "D": "#eb6834", "E": "#1baf7a"}
# Stacked cost parts: one sequential hue (part of one whole), dark -> light.
PART_COLOR = {"decision": "#104281", "execution": "#5598e7", "user simulator": "#c5dbf6"}


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


def _save(fig, out: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(out / f"{name}.png", dpi=200, facecolor=BG, metadata={"Software": None})
    fig.savefig(out / f"{name}.pdf", facecolor=BG, metadata={"CreationDate": None, "Producer": None})


def per_episode_costs(run: Path, arms: list[str]) -> dict[str, dict[str, float]]:
    """Mean $ per finished episode, split into decision / execution / user simulator."""
    sys.path.insert(0, str(Path(__file__).parent))
    from analyze_inloop import resolve

    rows = []
    for path in sorted(run.glob("episodes-*.jsonl")):
        with path.open() as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    rows, _ = resolve(rows)
    out = {}
    for arm in arms:
        ok = [r for r in rows if r["arm"] == arm and r.get("error") is None and r.get("reward") is not None]
        mean = lambda k: float(np.mean([r.get(k) or 0.0 for r in ok])) if ok else float("nan")
        out[arm] = {"decision": mean("decision_cost_usd"), "execution": mean("exec_cost_usd"),
                    "user simulator": mean("user_cost_usd")}
    return out


def fig_reward(summary, out, plt) -> None:
    arms = list(summary)
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for i, arm in enumerate(arms):
        m, lo, hi = summary[arm]["reward"]
        ax.bar(i, m, color=ARM_COLOR[arm], width=0.6, zorder=2)
        ax.errorbar(i, m, yerr=[[m - lo], [hi - m]], fmt="none", ecolor=INK, elinewidth=1.4, capsize=4, zorder=3)
        ax.annotate(f"{m:.2f}\n[{lo:.2f}, {hi:.2f}]", (i, hi + 0.03), ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(arms)), [ARM_NAME[a] for a in arms], rotation=15, ha="right")
    ax.set_ylim(0, 1.15)
    _style(ax, ylabel="Mean task reward")
    n = min(s["episodes"] for s in summary.values())
    ax.set_title(f"Figure 11. Task reward per arm, 95% CI clustered by task (≥{n} episodes per arm)",
                 loc="left", fontsize=11, color=INK)
    _save(fig, out, "fig11_inloop_reward")
    plt.close(fig)


def fig_cost_vs_reward(summary, costs, out, plt) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5.4))
    for arm, s in summary.items():
        x = costs[arm]["decision"] + costs[arm]["execution"]
        m, lo, hi = s["reward"]
        ax.errorbar([x], [m], yerr=[[m - lo], [hi - m]], fmt="none", ecolor=ARM_COLOR[arm], elinewidth=1.4,
                    capsize=3, zorder=2)
        ax.scatter([x], [m], s=150, color=ARM_COLOR[arm], edgecolor=BG, linewidth=2, zorder=3)
        # D sits just left of A and below it: label D on its left so it clears A's error bar.
        off, ha = ((-10, -14), "right") if arm == "D" else ((10, 6), "left")
        ax.annotate(ARM_NAME[arm], (x, m), xytext=off, textcoords="offset points", ha=ha, fontsize=9, color=INK)
    ax.set_xscale("log")
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:.3f}".rstrip("0")))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(-0.05, 1.1)
    _style(ax, xlabel="Agent $ per episode (decision + execution, log scale)", ylabel="Mean task reward")
    ax.set_title("Figure 12. Reward vs. agent cost per episode (up-left is better)", loc="left", fontsize=11,
                 color=INK)
    _save(fig, out, "fig12_inloop_cost_vs_reward")
    plt.close(fig)


def fig_pass_k(summary, out, plt) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ends = []
    for arm, s in summary.items():
        ks = sorted(int(k) for k in s["pass_k"])
        if not ks:
            continue
        ys = [s["pass_k"][str(k)] if str(k) in s["pass_k"] else s["pass_k"][k] for k in ks]
        ax.plot(ks, ys, color=ARM_COLOR[arm], linewidth=2, marker="o", markersize=7, zorder=3)
        ends.append([ys[-1], ks[-1], arm])
    # End labels: lines that finish close together (B and C) get their labels pushed apart to a
    # minimum vertical gap, keeping each label's x at its own line end.
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.045)
    for y_label, k_end, arm in ends:
        y_line = summary[arm]["pass_k"][str(k_end)] if str(k_end) in summary[arm]["pass_k"] else summary[arm]["pass_k"][k_end]
        ax.annotate(ARM_NAME[arm], (k_end, y_line), xytext=(k_end + 0.12, y_label), textcoords="data",
                    va="center", fontsize=9, color=INK)
    ax.set_ylim(0, 1.02)
    ax.set_xticks(range(1, max(len(s["pass_k"]) for s in summary.values()) + 1))
    _style(ax, xlabel="k (trials of the same task that must all succeed)", ylabel="pass^k")
    ax.set_title("Figure 13. Reliability: pass^k per arm", loc="left", fontsize=11, color=INK)
    ax.margins(x=0.25)
    _save(fig, out, "fig13_inloop_pass_k")
    plt.close(fig)


def fig_cost_breakdown(costs, out, plt) -> None:
    arms = list(costs)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    bottoms = np.zeros(len(arms))
    for part, color in PART_COLOR.items():
        vals = np.array([costs[a][part] for a in arms])
        ax.bar(range(len(arms)), vals, bottom=bottoms, color=color, width=0.6, edgecolor=BG, linewidth=2,
               zorder=2, label=part)
        bottoms += vals
    for i, total in enumerate(bottoms):
        ax.annotate(f"${total:.3f}", (i, total), xytext=(0, 3), textcoords="offset points", ha="center",
                    fontsize=8.5, color=INK)
    ax.set_xticks(range(len(arms)), [ARM_NAME[a] for a in arms], rotation=15, ha="right")
    ax.set_ylim(0, max(bottoms) * 1.12)
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    _style(ax, ylabel="$ per episode")
    ax.set_title("Figure 14. Where each arm's money goes, per episode", loc="left", fontsize=11, color=INK)
    _save(fig, out, "fig14_inloop_cost_breakdown")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    summary_path = args.run / "report" / "summary.json"
    if not summary_path.exists():
        raise SystemExit(f"no {summary_path}; run scripts/analyze_inloop.py {args.run} first")
    summary = json.loads(summary_path.read_text())["arms"]
    summary = {a: summary[a] for a in sorted(summary) if a in ARM_NAME}
    costs = per_episode_costs(args.run, list(summary))

    out = args.run / "paper_figures"
    out.mkdir(parents=True, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_reward(summary, out, plt)
    fig_cost_vs_reward(summary, costs, out, plt)
    fig_pass_k(summary, out, plt)
    fig_cost_breakdown(costs, out, plt)
    print(f"==> wrote fig11-fig14 (PNG+PDF) to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
