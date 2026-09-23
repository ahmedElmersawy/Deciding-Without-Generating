"""Analyze a decision-replay run (arm 0, step 3): tables + figures from <run>/calls.jsonl.

Writes into <run>/report/:
  summary.md             per-decider table: accuracy [95% CI], latency distribution, cost,
                         calibration (ECE/Brier), consistency across repeats, errors
  per_state.csv          one row per (decider, state): accuracy, modal choice, consistency
  fig_*.png / fig_*.pdf  accuracy, latency (with outliers), cost, consistency, reliability,
                         per-task accuracy

CIs are 95% cluster-bootstrap over STATES (repeats on one state are correlated).

Usage:
    python3 scripts/analyze_decisions.py results/replay/<run>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.stats import (  # noqa: E402
    bootstrap_ci,
    brier_score,
    describe,
    expected_calibration_error,
    reliability_bins,
)

# Reference categorical palette (dataviz skill, light mode), slots in fixed order. The first
# three validate for every chart form; deciders past three fold or facet.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def decider_color(decider: str) -> str:
    """Color follows the decider family, never its position, so adding a decider never
    repaints the others: jev = slot 1, LLMs = slot 2, local System One models (Kev) = slot 3."""
    if decider.startswith("llm:"):
        return SERIES[1]
    if decider.startswith("kev"):
        return SERIES[2]
    return SERIES[0]


def display_name(decider: str) -> str:
    """Figure label: `llm:openrouter/openai/gpt-oss-20b` -> `gpt-oss-20b (LLM)`."""
    if decider.startswith("llm:"):
        return f"{decider.rsplit('/', 1)[-1]} (LLM)"
    return decider


def load_rows(run: Path) -> list[dict]:
    with (run / "calls.jsonl").open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def per_state(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        if r["error"] is None:
            groups[(r["decider"], r["state_id"])].append(r)
    out = []
    for (decider, state_id), rs in sorted(groups.items()):
        counts = Counter(r["choice"] for r in rs)
        modal, modal_n = counts.most_common(1)[0]
        out.append(
            {
                "decider": decider,
                "state_id": state_id,
                "task_id": rs[0]["task_id"],
                "reference": rs[0]["reference"],
                "n": len(rs),
                "accuracy": float(np.mean([r["correct"] for r in rs])),
                "modal_choice": modal,
                "consistency": modal_n / len(rs),
                "n_distinct_choices": len(counts),
            }
        )
    return out


def summarize(rows: list[dict], states: list[dict], idle_watts=None) -> dict[str, dict]:
    summary = {}
    for decider in sorted({r["decider"] for r in rows}):
        all_rows = [r for r in rows if r["decider"] == decider]
        ok = [r for r in all_rows if r["error"] is None]
        clusters = [r["state_id"] for r in ok]
        acc = bootstrap_ci([r["correct"] for r in ok], clusters)
        costs = [r["cost_usd"] for r in ok if r["cost_usd"] is not None]
        cost_clusters = [r["state_id"] for r in ok if r["cost_usd"] is not None]
        with_conf = [r for r in ok if r["confidence"] is not None]
        conf = [r["confidence"] for r in with_conf]
        corr = [r["correct"] for r in with_conf]
        summary[decider] = {
            "model": ok[0]["model"] if ok else None,
            "calls": len(all_rows),
            "errors": len(all_rows) - len(ok),
            "accuracy": acc,
            "latency": describe([r["latency_s"] for r in ok]),
            "cost": bootstrap_ci(costs, cost_clusters) if costs else (float("nan"),) * 3,
            "cost_total": float(np.sum(costs)) if costs else float("nan"),
            "input_tokens": describe([r["input_tokens"] for r in ok if r["input_tokens"] is not None]),
            "ece": expected_calibration_error(conf, corr) if conf else float("nan"),
            "brier": brier_score(conf, corr) if conf else float("nan"),
            "consistency": bootstrap_ci([s["consistency"] for s in states if s["decider"] == decider]),
            "all_repeats_agree": float(np.mean([s["n_distinct_choices"] == 1 for s in states if s["decider"] == decider])),
            "server_latency": describe([r["server_latency_s"] for r in ok if r.get("server_latency_s") is not None]),
            "energy": _energy(ok, idle_watts),
        }
    return summary


def _energy(ok: list[dict], idle_watts) -> dict:
    """Gross J/decision and, given the idle baseline, net = gross - idle_W * call latency."""
    metered = [r for r in ok if r.get("energy_j") is not None]
    if not metered:
        return {}
    clusters = [r["state_id"] for r in metered]
    out = {"gross": bootstrap_ci([r["energy_j"] for r in metered], clusters)}
    if idle_watts is not None:
        net = [r["energy_j"] - idle_watts * r["latency_s"] for r in metered]
        out["net"] = bootstrap_ci(net, clusters)
    return out


def write_summary_md(run: Path, meta: dict, summary: dict, report: Path) -> None:
    def ci(t, fmt="{:.3f}"):
        return f"{fmt.format(t[0])} [{fmt.format(t[1])}, {fmt.format(t[2])}]"

    lines = [
        f"# Decision replay — {run.name}",
        "",
        f"- states: {meta['n_states']} ({'all episodes' if meta['include_failed'] else 'reward=1 episodes only'}), "
        f"repeats per state: {meta['repeats']}, concurrency: {meta['workers']}",
        f"- LLM decider model: `{meta['llm_model']}`",
        "- accuracy = agreement with the reference action from a successful trajectory (a lower bound: "
        "other actions may also be acceptable)",
        "- 95% CIs: cluster bootstrap over states. Latency = client wall clock per call, network included.",
        "",
        "## Decision quality",
        "",
        "| decider | calls | errors | accuracy [95% CI] | consistency [95% CI] | all repeats agree | ECE | Brier |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for d, s in summary.items():
        lines.append(
            f"| {d} | {s['calls']} | {s['errors']} | {ci(s['accuracy'])} | {ci(s['consistency'])} | "
            f"{s['all_repeats_agree']:.2f} | {s['ece']:.3f} | {s['brier']:.3f} |"
        )
    lines += [
        "",
        "## Decision cost",
        "",
        "| decider | latency mean | p50 | p95 | min | max | outliers (IQR) | $ / decision [95% CI] | $ total | input tokens p50 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for d, s in summary.items():
        lat = s["latency"]
        lines.append(
            f"| {d} | {lat.get('mean', float('nan')):.3f}s | {lat.get('p50', float('nan')):.3f}s | "
            f"{lat.get('p95', float('nan')):.3f}s | {lat.get('min', float('nan')):.3f}s | "
            f"{lat.get('max', float('nan')):.3f}s | {lat.get('n_outliers', 0)} | "
            f"{ci(s['cost'], '{:.2e}') if not np.isnan(s['cost'][0]) else 'n/a (local)'} | "
            f"{s['cost_total']:.4f} | {s['input_tokens'].get('p50', float('nan')):.0f} |".replace("| nan |", "| n/a |")
        )
    local = {d: s for d, s in summary.items() if s["server_latency"].get("n") or s["energy"]}
    if local:
        gpu = meta.get("gpu") or f"energy not measured ({meta.get('energy_unavailable') or 'no GPU meter'})"
        idle = meta.get("gpu_idle_watts")
        lines += [
            "",
            "## Local deciders: model time vs. overhead, and energy",
            "",
            f"GPU: {gpu}" + (f", idle baseline {idle:.1f} W" if idle is not None else "")
            + ". Energy is whole-GPU over each (serialized) call; net subtracts the idle baseline.",
            "",
            "| decider | server (model) latency p50 | client latency p50 | HTTP/client overhead p50 | "
            "J / decision gross [95% CI] | J / decision net [95% CI] |",
            "|---|---|---|---|---|---|",
        ]
        for d, s in local.items():
            srv, cli = s["server_latency"], s["latency"]
            overhead = cli["p50"] - srv["p50"] if srv.get("n") else float("nan")
            e = dict(s["energy"])
            block = (meta.get("energy_blocks") or {}).get(d)
            if block and block["calls"]:
                gross = block["joules"] / block["calls"]
                e["gross"] = (gross, gross, gross)  # block measure: exact, no per-call CI
                if idle is not None:
                    net = (block["joules"] - idle * block["seconds"]) / block["calls"]
                    e["net"] = (net, net, net)
            lines.append(
                f"| {d} | {srv.get('p50', float('nan')):.3f}s | {cli['p50']:.3f}s | {overhead:.3f}s | "
                f"{ci(e['gross'], '{:.2f}') if 'gross' in e else 'n/a'} | {ci(e['net'], '{:.2f}') if 'net' in e else 'n/a'} |"
            )
    names = list(summary)
    if "jev" in summary and len(names) > 1:
        lines += ["", "## Jev relative to each other decider", ""]
        j = summary["jev"]
        for d in names:
            if d == "jev":
                continue
            o = summary[d]
            cost = (f"mean $/decision {o['cost'][0] / j['cost'][0]:.2f}x" if not np.isnan(o["cost"][0])
                    else "no $ cost (local)")
            lines.append(
                f"- vs `{d}`: median latency {o['latency']['p50'] / j['latency']['p50']:.2f}x, {cost} "
                f"(>1 means Jev is faster/cheaper); accuracy difference {j['accuracy'][0] - o['accuracy'][0]:+.3f}"
            )
    (report / "summary.md").write_text("\n".join(lines) + "\n")


def _style(ax, xlabel=None, ylabel=None):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_2, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_2, fontsize=9)


def _save(fig, report: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(report / f"{name}.png", dpi=200, facecolor="#fcfcfb")
    fig.savefig(report / f"{name}.pdf", facecolor="#fcfcfb")


def _plain_log_ticks(ax):
    """Log axis with readable decimal ticks instead of overlapping 3x10^-1 style labels."""
    from matplotlib.ticker import FixedLocator, NullFormatter, NullLocator

    lo, hi = ax.get_xlim()
    candidates = [0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 3, 5, 10, 20, 30, 60]
    ax.xaxis.set_major_locator(FixedLocator([t for t in candidates if lo <= t <= hi]))
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:g}")
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_minor_formatter(NullFormatter())


def _dot_ci(ax, labels, triples, colors, fmt):
    """Horizontal dot + 95% CI per decider, value labeled directly (one series per row)."""
    for i, (t, c) in enumerate(zip(triples, colors)):
        ax.plot([t[1], t[2]], [i, i], color=c, linewidth=2, solid_capstyle="round", zorder=3)
        ax.plot(t[0], i, "o", color=c, markersize=8, markeredgecolor="#fcfcfb", markeredgewidth=2, zorder=4)
        ax.annotate(fmt(t), (t[0], i), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(-0.6, len(labels) - 0.4)


def plot_all(summary: dict, rows: list[dict], states: list[dict], report: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(summary)
    labels = [display_name(d) for d in names]
    colors = {d: decider_color(d) for d in names}
    ok = [r for r in rows if r["error"] is None]
    height = 0.7 * len(names) + 1.2

    # 1. accuracy
    fig, ax = plt.subplots(figsize=(6.5, height))
    _dot_ci(ax, labels, [summary[d]["accuracy"] for d in names], [colors[d] for d in names],
            lambda t: f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]")
    ax.set_xlim(0, 1.02)
    _style(ax, xlabel="Agreement with reference action (95% CI)")
    ax.set_title("Decision accuracy", loc="left", fontsize=11, color=INK)
    _save(fig, report, "fig_accuracy")
    plt.close(fig)

    # 2. latency distribution, outliers visible
    fig, ax = plt.subplots(figsize=(6.5, height))
    data = [[r["latency_s"] for r in ok if r["decider"] == d] for d in names]
    bp = ax.boxplot(data, orientation="horizontal", widths=0.5, patch_artist=True, whis=1.5,
                    flierprops={"marker": "o", "markersize": 4, "alpha": 0.6, "markeredgewidth": 0})
    for i, d in enumerate(names):
        bp["boxes"][i].set(facecolor=colors[d] + "33", edgecolor=colors[d], linewidth=1.5)
        bp["medians"][i].set(color=colors[d], linewidth=2)
        for key in ("whiskers", "caps"):
            for line in bp[key][2 * i: 2 * i + 2]:
                line.set(color=colors[d], linewidth=1.2)
        bp["fliers"][i].set(markerfacecolor=colors[d])
        p50 = summary[d]["latency"]["p50"]
        ax.annotate(f"p50 {p50:.2f}s", (p50, i + 1.33), ha="center", fontsize=8, color=INK_2)
    ax.set_yticks(range(1, len(names) + 1), labels)
    ax.set_xscale("log")
    _plain_log_ticks(ax)
    _style(ax, xlabel="Latency per decision, seconds (log scale; dots = IQR outliers)")
    ax.set_title("Decision latency", loc="left", fontsize=11, color=INK)
    _save(fig, report, "fig_latency")
    plt.close(fig)

    # 3. cost per decision
    fig, ax = plt.subplots(figsize=(6.5, height))
    priced = [d for d in names if not np.isnan(summary[d]["cost"][0])]
    _dot_ci(ax, [display_name(d) for d in priced], [summary[d]["cost"] for d in priced], [colors[d] for d in priced],
            lambda t: f"${t[0]:.2e}")
    ax.set_xscale("log")
    ax.margins(x=0.3)
    ax.xaxis.set_major_formatter(lambda x, _: f"${x:.0e}".replace("e-0", "e-"))
    ax.xaxis.set_minor_formatter(lambda x, _: "")
    _style(ax, xlabel=r"\$ per decision (95% CI, log scale; local deciders have no \$ cost)")
    ax.set_title("Decision cost", loc="left", fontsize=11, color=INK)
    _save(fig, report, "fig_cost")
    plt.close(fig)

    # 4. consistency across repeats: small multiples, one panel per decider
    fig, axes = plt.subplots(1, len(names), figsize=(3.2 * len(names), 2.8), sharey=True, squeeze=False)
    for ax, d in zip(axes[0], names):
        vals = [s["consistency"] for s in states if s["decider"] == d]
        ax.hist(vals, bins=np.linspace(0, 1, 11), color=colors[d], edgecolor="#fcfcfb", linewidth=2, zorder=3)
        _style(ax, xlabel="Share of repeats matching the modal choice")
        ax.set_title(display_name(d), loc="left", fontsize=10, color=INK)
    axes[0][0].set_ylabel("States", color=INK_2, fontsize=9)
    fig.suptitle("Consistency across repeated calls on the same state", x=0.01, ha="left", fontsize=11, color=INK)
    _save(fig, report, "fig_consistency")
    plt.close(fig)

    # 5. reliability diagrams: small multiples
    fig, axes = plt.subplots(1, len(names), figsize=(3.2 * len(names), 3.2), sharey=True, squeeze=False)
    for ax, d in zip(axes[0], names):
        rs = [r for r in ok if r["decider"] == d and r["confidence"] is not None]
        ax.plot([0, 1], [0, 1], color=GRID, linewidth=1.5, zorder=2)
        if rs:
            bins = reliability_bins([r["confidence"] for r in rs], [r["correct"] for r in rs])
            xs, ys, ns = zip(*bins)
            ax.plot(xs, ys, color=colors[d], linewidth=2, zorder=3)
            ax.scatter(xs, ys, s=[18 + 60 * n / max(ns) for n in ns], color=colors[d],
                       edgecolor="#fcfcfb", linewidth=1.5, zorder=4)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        _style(ax, xlabel="Stated confidence")
        ax.set_title(f"{display_name(d)}  ECE {summary[d]['ece']:.3f}", loc="left", fontsize=10, color=INK)
    axes[0][0].set_ylabel("Observed accuracy", color=INK_2, fontsize=9)
    fig.suptitle("Calibration (dot size = calls in bin; diagonal = perfect)", x=0.01, ha="left", fontsize=11, color=INK)
    _save(fig, report, "fig_reliability")
    plt.close(fig)

    # 6. per-task accuracy, deciders side by side
    tasks = sorted({s["task_id"] for s in states})
    fig, ax = plt.subplots(figsize=(7, 0.45 * len(tasks) + 1.5))
    offsets = np.linspace(-0.18, 0.18, len(names)) if len(names) > 1 else [0.0]
    for off, d in zip(offsets, names):
        for i, t in enumerate(tasks):
            vals = [s["accuracy"] for s in states if s["decider"] == d and s["task_id"] == t]
            if vals:
                ax.plot(np.mean(vals), i + off, "o", color=colors[d], markersize=7,
                        markeredgecolor="#fcfcfb", markeredgewidth=1.5, zorder=3, label=display_name(d) if i == 0 else None)
    ax.set_yticks(range(len(tasks)), tasks, fontsize=8)
    ax.set_xlim(-0.03, 1.03)
    _style(ax, xlabel="Mean agreement with reference action")
    ax.legend(frameon=False, fontsize=9, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(names))
    ax.set_title("Accuracy by task", loc="left", fontsize=11, color=INK, pad=24)
    _save(fig, report, "fig_per_task")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    rows = load_rows(args.run)
    meta = json.loads((args.run / "meta.json").read_text())
    report = args.run / "report"
    report.mkdir(exist_ok=True)

    states = per_state(rows)
    summary = summarize(rows, states, meta.get("gpu_idle_watts"))
    write_summary_md(args.run, meta, summary, report)
    with (report / "per_state.csv").open("w") as fh:
        cols = list(states[0])
        fh.write(",".join(cols) + "\n")
        for s in states:
            fh.write(",".join(str(s[c]) for c in cols) + "\n")
    plot_all(summary, rows, states, report)
    print((report / "summary.md").read_text())
    print(f"==> report in {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
