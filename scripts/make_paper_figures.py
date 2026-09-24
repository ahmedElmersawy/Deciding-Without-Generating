#!/usr/bin/env python3
"""Publication-quality figures for the mock-pilot agent-control decision benchmark.

Reads the SAME source of truth as scripts/analyze_decisions.py (results/replay/<run>/
calls-*.jsonl + meta-*.json, plus the states file(s) named in meta.json) and reuses
dwg.stats for every statistic (bootstrap CIs, ECE, Brier, reliability bins) so numbers
here never diverge from the run's own report/summary.md.

Deciders included: jev, kev-0.8b, kev-4b, kev-9b, llm:openrouter/openai/gpt-oss-20b —
the five with real replay data in this run. Qwen3 is NOT included anywhere: no Qwen3
decider has been run yet (PLAN.md G3 is still open), so no value is invented for it;
every figure that would show it instead prints where its bar/point would go with an
explicit "not yet benchmarked" label.

Usage:
    python3 scripts/make_paper_figures.py results/replay/mock-pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.runfiles import load_calls, load_decider_metas  # noqa: E402
from dwg.stats import bootstrap_ci, brier_score, describe, expected_calibration_error, reliability_bins  # noqa: E402

RESPOND = "respond_to_user"

# Fixed order and display names, used identically across every figure and the table.
ORDER = ["jev", "llm:openrouter/openai/gpt-oss-20b", "kev-0.8b", "kev-4b", "kev-9b", "cascade-kev-4b-t0.9"]
DISPLAY = {
    "jev": "Jev",
    "llm:openrouter/openai/gpt-oss-20b": "GPT-OSS-20B",
    "kev-0.8b": "Kev-0.8B",
    "kev-4b": "Kev-4B",
    "kev-9b": "Kev-9B",
    "cascade-kev-4b-t0.9": "Cascade (t=0.9)",
}
# Family color rule carried over from analyze_decisions.py (hue = family, never position):
# blue = Jev, orange = hosted LLM, green shades = local Kev sizes (light->dark = small->large),
# purple = the hybrid cascade (its own family: neither pure-local nor pure-hosted).
COLOR = {
    "jev": "#2a78d6",
    "llm:openrouter/openai/gpt-oss-20b": "#eb6834",
    "kev-0.8b": "#8fd9c4",
    "kev-4b": "#1baf7a",
    "kev-9b": "#0b7d54",
    "cascade-kev-4b-t0.9": "#7d5fd6",
}
QWEN3_NOTE = "Qwen3: not yet benchmarked (PLAN.md G3 not started — no local Qwen3 decider run exists)"

INK, INK_2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load_states(run: Path) -> dict[str, dict]:
    meta = json.loads((run / "meta.json").read_text())
    states = {}
    for p in meta["states"]:
        with open(p) as fh:
            for line in fh:
                if line.strip():
                    s = json.loads(line)
                    states[s["state_id"]] = s
    return states


def already_called_tools(state: dict) -> set[str]:
    """Tool names that already appear as executed calls earlier in this state's history."""
    names = set()
    for m in state["history"]:
        for call in m.get("tool_calls") or []:
            names.add(call["name"])
    return names


def compute_metrics(run: Path) -> dict[str, dict]:
    rows = load_calls(run)
    dmetas = load_decider_metas(run)
    states = load_states(run)
    already = {sid: already_called_tools(s) for sid, s in states.items()}

    metrics = {}
    for d in ORDER:
        drows = [r for r in rows if r["decider"] == d]
        if not drows:
            continue
        ok = [r for r in drows if r["error"] is None]
        clusters = [r["state_id"] for r in ok]
        acc = bootstrap_ci([r["correct"] for r in ok], clusters)
        lat_ms = [r["latency_s"] * 1000 for r in ok]
        lat_desc = describe(lat_ms)
        with_conf = [r for r in ok if r["confidence"] is not None]
        conf = [r["confidence"] for r in with_conf]
        corr = [r["correct"] for r in with_conf]
        ece = expected_calibration_error(conf, corr) if conf else float("nan")
        brier = brier_score(conf, corr) if conf else float("nan")
        rel = reliability_bins(conf, corr) if conf else []

        by_state = defaultdict(list)
        for r in ok:
            by_state[r["state_id"]].append(r["choice"])
        cons_vals, cons_clusters = [], []
        for sid, choices in by_state.items():
            modal_n = Counter(choices).most_common(1)[0][1]
            cons_vals.append(modal_n / len(choices))
            cons_clusters.append(sid)
        consistency = bootstrap_ci(cons_vals, cons_clusters)

        dm = dmetas.get(d, {})
        energy_gross = energy_net = None
        block = dm.get("energy_block")
        if block and block.get("calls"):
            energy_gross = block["joules"] / block["calls"]
            idle_w = dm.get("gpu_idle_watts")
            if idle_w is not None:
                energy_net = (block["joules"] - idle_w * block["seconds"]) / block["calls"]

        err_counts = Counter()
        for r in ok:
            if r["correct"]:
                continue
            ref, choice, sid = r["reference"], r["choice"], r["state_id"]
            if ref == RESPOND and choice != RESPOND:
                err_counts["Called tool instead of replying"] += 1
            elif choice == RESPOND and ref != RESPOND:
                err_counts["Reply instead of tool call"] += 1
            elif choice != ref and choice in already.get(sid, set()):
                err_counts["Repeated tool call"] += 1
            elif choice != ref:
                err_counts["Wrong tool selected"] += 1
            else:
                err_counts["Other decision errors"] += 1  # should not trigger; kept for safety

        metrics[d] = dict(
            n=len(ok),
            errors=len(drows) - len(ok),
            accuracy=acc,
            latency_ms=lat_desc,
            raw_latency_ms=lat_ms,
            ece=ece,
            brier=brier,
            reliability=rel,
            consistency=consistency,
            energy_gross=energy_gross,
            energy_net=energy_net,
            error_counts=err_counts,
            n_incorrect=sum(err_counts.values()),
        )
    return metrics


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


def fig1_pareto(metrics, out, plt) -> dict:
    pts = {d: (metrics[d]["latency_ms"]["p50"], metrics[d]["accuracy"][0] * 100) for d in metrics}
    items = sorted(pts.items(), key=lambda kv: kv[1][0])
    frontier, best_y = [], -1.0
    for d, (_, y) in items:
        if y > best_y:
            frontier.append(d)
            best_y = y
    frontier_set = set(frontier)

    fig, ax = plt.subplots(figsize=(7.5, 5.8))
    fx = [pts[d][0] for d in frontier]
    fy = [pts[d][1] for d in frontier]
    ax.plot(fx, fy, color=INK_2, linewidth=1.2, linestyle="--", zorder=1, label="Pareto frontier")
    # Kev-4B and Kev-9B sit close together in both axes: alternate label offsets so the two
    # text boxes don't collide (a fixed (9, 7) offset for both overlapped in the first draft).
    label_offset = {"kev-4b": (9, -14), "kev-9b": (9, 9)}
    for d, (x, y) in pts.items():
        on = d in frontier_set
        ax.scatter([x], [y], s=170 if on else 100, color=COLOR[d],
                   edgecolor=INK if on else "none", linewidth=1.6, zorder=3)
        tag = DISPLAY[d] + (" ★" if on else "")
        ax.annotate(tag, (x, y), xytext=label_offset.get(d, (9, 7)), textcoords="offset points",
                    fontsize=9.5, color=INK)
    ax.annotate(QWEN3_NOTE, (0.02, 0.03), xycoords="axes fraction", fontsize=7.5, color=INK_2, style="italic")
    ax.set_xscale("log")
    _style(ax, xlabel="Median latency (ms, log scale)", ylabel="Accuracy (%)")
    ax.set_title("Figure 1. Accuracy vs. latency: the decision-cost Pareto frontier", loc="left", fontsize=12, color=INK)
    ax.set_ylim(0, 100)
    _save(fig, out, "fig1_pareto_accuracy_latency")
    plt.close(fig)
    return {"frontier": frontier, "dominated": [d for d in pts if d not in frontier_set], "points": pts}


def fig2_accuracy_ci(metrics, out, plt) -> None:
    order = sorted(metrics, key=lambda d: metrics[d]["accuracy"][0])
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    xs = np.arange(len(order))
    means = [metrics[d]["accuracy"][0] * 100 for d in order]
    lo = [metrics[d]["accuracy"][0] * 100 - metrics[d]["accuracy"][1] * 100 for d in order]
    hi = [metrics[d]["accuracy"][2] * 100 - metrics[d]["accuracy"][0] * 100 for d in order]
    colors = [COLOR[d] for d in order]
    ax.bar(xs, means, color=colors, width=0.6, zorder=2)
    ax.errorbar(xs, means, yerr=[lo, hi], fmt="none", ecolor=INK, elinewidth=1.4, capsize=4, zorder=3)
    for x, d in zip(xs, order):
        a = metrics[d]["accuracy"]
        ax.annotate(f"{a[0]*100:.1f}%\n[{a[1]*100:.1f}, {a[2]*100:.1f}]", (x, means[xs.tolist().index(x)] + hi[list(xs).index(x)] + 2),
                    ha="center", fontsize=8, color=INK)
    ax.set_xticks(xs, [DISPLAY[d] for d in order])
    ax.set_ylim(0, 105)
    _style(ax, ylabel="Accuracy (%)")
    ax.set_title("Figure 2. Decision accuracy with 95% CI (lowest → highest)", loc="left", fontsize=12, color=INK)
    _save(fig, out, "fig2_accuracy_ci")
    plt.close(fig)


def fig3_energy(metrics, out, plt) -> None:
    labels = ["Kev-0.8B", "Kev-4B", "Kev-9B", "Qwen3"]
    keys = ["kev-0.8b", "kev-4b", "kev-9b", None]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    xs = np.arange(len(labels))
    width = 0.35
    for i, (lab, k) in enumerate(zip(labels, keys)):
        if k is None or metrics.get(k, {}).get("energy_gross") is None:
            reason = "not available" if k is None else "not measured (invalid GPU energy counter)"
            ax.annotate(reason, (xs[i], 1.5), ha="center", fontsize=8, color=INK_2, rotation=90, va="bottom")
            continue
        m = metrics[k]
        ax.bar(xs[i] - width / 2, m["energy_gross"], width, color=COLOR[k], zorder=2, label="gross" if i == 1 else None)
        ax.annotate(f"{m['energy_gross']:.2f} J", (xs[i] - width / 2, m["energy_gross"]), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=8, color=INK)
        if m["energy_net"] is not None:
            ax.bar(xs[i] + width / 2, m["energy_net"], width, color=COLOR[k], alpha=0.55, zorder=2,
                   label="net (idle-subtracted)" if i == 1 else None)
            ax.annotate(f"{m['energy_net']:.2f} J", (xs[i] + width / 2, m["energy_net"]), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=8, color=INK)
    ax.set_xticks(xs, labels)
    _style(ax, ylabel="Joules per decision")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("Figure 3. Energy per decision (local deciders only)", loc="left", fontsize=12, color=INK)
    _save(fig, out, "fig3_energy_per_decision")
    plt.close(fig)


def fig4_accuracy_vs_energy(metrics, out, plt) -> dict:
    have = {d: metrics[d] for d in metrics if metrics[d]["energy_gross"] is not None}
    fig, ax = plt.subplots(figsize=(7.5, 6))
    eff = {}
    accs = [m["accuracy"][0] * 100 for m in have.values()]
    energies = [m["energy_gross"] for m in have.values()]
    # Only 2-3 points typically, all close together: fixed generous padding so labels never
    # collide with each other or with the axis frame (autoscale alone was too tight here).
    y_pad = max(3.0, (max(accs) - min(accs)) * 0.6) if len(accs) > 1 else 5.0
    x_pad = max(2.0, (max(energies) - min(energies)) * 0.6) if len(energies) > 1 else 2.0
    ax.set_ylim(min(accs) - y_pad, max(accs) + y_pad * 1.8)
    ax.set_xlim(max(0, min(energies) - x_pad), max(energies) + x_pad)
    for d, m in have.items():
        acc = m["accuracy"][0] * 100
        e = m["energy_gross"]
        eff[d] = acc / e
        ax.scatter([e], [acc], s=170, color=COLOR[d], zorder=3)
        ax.annotate(f"{DISPLAY[d]}: {acc/e:.3f} %/J", (e, acc), xytext=(0, 14), textcoords="offset points",
                    ha="center", fontsize=9.5, color=INK)
    if eff:
        best = max(eff, key=eff.get)
        bx, by = have[best]["energy_gross"], have[best]["accuracy"][0] * 100
        ax.scatter([bx], [by], s=380, facecolors="none", edgecolors=INK, linewidth=1.6, zorder=4)
        ax.annotate("best accuracy/J", (bx, by), xytext=(0, -22), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK_2, style="italic")
    excluded = [DISPLAY.get(d, d) for d in metrics if d not in have] + ["Qwen3 (not available)"]
    ax.annotate("no valid energy measurement: " + ", ".join(excluded), (0.5, -0.16), xycoords="axes fraction",
                ha="center", fontsize=8, color=INK_2, style="italic")
    _style(ax, xlabel="Energy per decision (J, gross)", ylabel="Accuracy (%)")
    ax.set_title("Figure 4. Accuracy vs. energy: the efficiency frontier", loc="left", fontsize=12, color=INK)
    _save(fig, out, "fig4_accuracy_vs_energy")
    plt.close(fig)
    return eff


def fig5_consistency(metrics, out, plt) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    xs = np.arange(len(ORDER))
    order = [d for d in ORDER if d in metrics]
    vals = [metrics[d]["consistency"][0] * 100 for d in order]
    lo = [metrics[d]["consistency"][0] * 100 - metrics[d]["consistency"][1] * 100 for d in order]
    hi = [metrics[d]["consistency"][2] * 100 - metrics[d]["consistency"][0] * 100 for d in order]
    ax.bar(range(len(order)), vals, color=[COLOR[d] for d in order], width=0.6, zorder=2)
    ax.errorbar(range(len(order)), vals, yerr=[lo, hi], fmt="none", ecolor=INK, elinewidth=1.4, capsize=4, zorder=3)
    for i, d in enumerate(order):
        ax.annotate(f"{vals[i]:.1f}%", (i, vals[i] + hi[i] + 1.5), ha="center", fontsize=9, color=INK)
    ax.set_xticks(range(len(order)), [DISPLAY[d] for d in order])
    ax.set_ylim(0, 108)
    _style(ax, ylabel="Repeats matching the modal choice (%)")
    ax.set_title("Figure 5. Decision consistency across 5 repeats per state", loc="left", fontsize=12, color=INK)
    _save(fig, out, "fig5_consistency")
    plt.close(fig)


def fig6_calibration(metrics, out, plt) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    ax.plot([0, 1], [0, 1], color=GRID, linewidth=1.2, linestyle="--", zorder=1, label="perfect calibration")
    for d in ORDER:
        if d not in metrics or not metrics[d]["reliability"]:
            continue
        rel = metrics[d]["reliability"]
        xs = [r[0] for r in rel]
        ys = [r[1] for r in rel]
        ns = [r[2] for r in rel]
        ax.plot(xs, ys, color=COLOR[d], linewidth=1.6, zorder=2)
        ax.scatter(xs, ys, s=[max(20, n * 3) for n in ns], color=COLOR[d], zorder=3,
                   label=f"{DISPLAY[d]} (ECE {metrics[d]['ece']:.3f})")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _style(ax, xlabel="Stated confidence", ylabel="Observed accuracy")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("Figure 6. Calibration (dot size = calls in bin)", loc="left", fontsize=12, color=INK)
    _save(fig, out, "fig6_calibration")
    plt.close(fig)


def fig7_latency(metrics, out, plt) -> None:
    order = [d for d in ORDER if d in metrics]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    data = [metrics[d]["raw_latency_ms"] for d in order]
    bp = ax.boxplot(data, vert=False, positions=range(len(order)), widths=0.55, showfliers=True,
                     patch_artist=True, medianprops=dict(color=INK, linewidth=1.8),
                     flierprops=dict(marker="o", markersize=3.5, markerfacecolor=INK_2, markeredgecolor="none", alpha=0.6))
    for i, (d, box) in enumerate(zip(order, bp["boxes"])):
        box.set_facecolor(COLOR[d])
        box.set_alpha(0.5)
        box.set_edgecolor(COLOR[d])
        p95 = metrics[d]["latency_ms"]["p95"]
        ax.plot([p95], [i], marker="|", color=INK, markersize=16, markeredgewidth=2, zorder=4)
        ax.annotate(f"p95 {p95:.0f}ms", (p95, i), xytext=(6, 8), textcoords="offset points", fontsize=7.5, color=INK_2)
    ax.set_yticks(range(len(order)), [DISPLAY[d] for d in order])
    ax.set_xscale("log")
    _style(ax, xlabel="Latency per decision (ms, log scale)")
    ax.set_title("Figure 7. Latency distribution: median, IQR, p95, outliers", loc="left", fontsize=12, color=INK)
    _save(fig, out, "fig7_latency_distribution")
    plt.close(fig)


ERROR_CATS = ["Called tool instead of replying", "Reply instead of tool call", "Repeated tool call",
              "Wrong tool selected", "Other decision errors"]
ERROR_COLORS = ["#c0392b", "#e67e22", "#8e44ad", "#7f8c8d", "#bdc3c7"]


def fig8_error_breakdown(metrics, out, plt) -> dict:
    order = [d for d in ORDER if d in metrics]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    bottoms = np.zeros(len(order))
    totals = {d: sum(metrics[d]["error_counts"].values()) for d in order}
    for cat, col in zip(ERROR_CATS, ERROR_COLORS):
        vals = np.array([metrics[d]["error_counts"].get(cat, 0) for d in order], dtype=float)
        ax.bar(range(len(order)), vals, bottom=bottoms, color=col, width=0.6, zorder=2, label=cat)
        bottoms += vals
    for i, d in enumerate(order):
        if totals[d]:
            ax.annotate(f"n={totals[d]}", (i, bottoms[i] + 1), ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(order)), [DISPLAY[d] for d in order])
    _style(ax, ylabel="Incorrect calls (count)")
    ax.legend(frameon=False, fontsize=8, loc="upper right", bbox_to_anchor=(1.0, 1.15), ncol=1)
    ax.set_title("Figure 8. Error-type breakdown", loc="left", fontsize=12, color=INK)
    _save(fig, out, "fig8_error_breakdown")
    plt.close(fig)
    return {d: dict(metrics[d]["error_counts"]) for d in order}


def fig9_radar(metrics, eff, out, plt) -> None:
    axes_labels = ["Accuracy", "Speed\n(1/latency)", "Energy\nefficiency", "Calibration\n(1−ECE)", "Consistency"]
    order = [d for d in ORDER if d in metrics]
    n = len(axes_labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    def minmax(vals: dict[str, float]) -> dict[str, float]:
        xs = [v for v in vals.values() if v is not None and not np.isnan(v)]
        if len(xs) < 2 or max(xs) == min(xs):
            return {k: (1.0 if v is not None else np.nan) for k, v in vals.items()}
        lo, hi = min(xs), max(xs)
        return {k: (np.nan if v is None else (v - lo) / (hi - lo)) for k, v in vals.items()}

    acc_raw = {d: metrics[d]["accuracy"][0] for d in order}
    speed_raw = {d: -metrics[d]["latency_ms"]["p50"] for d in order}  # negate: lower latency -> higher score
    energy_raw = {d: (eff.get(d) if d in eff else None) for d in order}
    calib_raw = {d: (1 - metrics[d]["ece"] if not np.isnan(metrics[d]["ece"]) else None) for d in order}
    cons_raw = {d: metrics[d]["consistency"][0] for d in order}

    scores = {
        "Accuracy": minmax(acc_raw),
        "Speed\n(1/latency)": minmax(speed_raw),
        "Energy\nefficiency": minmax(energy_raw),
        "Calibration\n(1−ECE)": minmax(calib_raw),
        "Consistency": minmax(cons_raw),
    }

    fig = plt.figure(figsize=(8, 7.5))
    ax = fig.add_axes([0.08, 0.06, 0.62, 0.8], polar=True)
    ax.set_facecolor(BG)
    for d in order:
        vals = [scores[lab][d] for lab in axes_labels]
        vals += vals[:1]
        ax.plot(angles, vals, color=COLOR[d], linewidth=2, label=DISPLAY[d], zorder=3)
        ax.fill(angles, vals, color=COLOR[d], alpha=0.08, zorder=2)
    ax.set_xticks(angles[:-1], axes_labels, fontsize=9, color=INK)
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.grid(True, color=GRID, linewidth=0.7)
    # Legend and title placed OUTSIDE the polar axes (fig-level, not ax-level): the earlier
    # bbox_to_anchor on the axes itself collided with the wrapped title text at this figure size.
    fig.legend(loc="center left", bbox_to_anchor=(0.72, 0.75), frameon=False, fontsize=9.5)
    fig.text(
        0.06, 0.94,
        "Figure 9. Normalized summary\n(per-axis min-max across shown deciders; gap in a line = metric not measured)",
        fontsize=11, color=INK, ha="left", va="top",
    )
    # Manually-placed axes (fig.add_axes, not subplots/gridspec): skip _save's tight_layout,
    # which is only meant for gridspec-managed figures and would warn/fight this layout.
    fig.savefig(out / "fig9_radar_summary.png", dpi=200, facecolor=BG, metadata={"Software": None})
    fig.savefig(out / "fig9_radar_summary.pdf", facecolor=BG, metadata={"CreationDate": None, "Producer": None})
    plt.close(fig)


def write_table(metrics, out: Path, run_name: str) -> str:
    order = [d for d in ORDER if d in metrics]
    lines = [
        f"# Benchmark table ({run_name})",
        "",
        "| Decider | Accuracy | 95% CI | Median latency (ms) | p95 latency (ms) | ECE |",
        "|---|---|---|---|---|---|",
    ]
    for d in order:
        m = metrics[d]
        a = m["accuracy"]
        lines.append(
            f"| {DISPLAY[d]} | {a[0]*100:.1f}% | [{a[1]*100:.1f}%, {a[2]*100:.1f}%] | "
            f"{m['latency_ms']['p50']:.1f} | {m['latency_ms']['p95']:.1f} | {m['ece']:.3f} |"
        )
    lines.append("")
    lines.append(QWEN3_NOTE + ".")
    text = "\n".join(lines) + "\n"
    (out / "table.md").write_text(text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    out = args.run / "paper_figures"
    out.mkdir(parents=True, exist_ok=True)

    metrics = compute_metrics(args.run)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pareto = fig1_pareto(metrics, out, plt)
    fig2_accuracy_ci(metrics, out, plt)
    fig3_energy(metrics, out, plt)
    eff = fig4_accuracy_vs_energy(metrics, out, plt)
    fig5_consistency(metrics, out, plt)
    fig6_calibration(metrics, out, plt)
    fig7_latency(metrics, out, plt)
    errors = fig8_error_breakdown(metrics, out, plt)
    fig9_radar(metrics, eff, out, plt)
    table = write_table(metrics, out, args.run.name)

    interp = {
        "fig1": (
            f"Pareto-optimal: {', '.join(DISPLAY[d] for d in pareto['frontier'])}. "
            f"Dominated (another decider is both faster and more accurate): "
            f"{', '.join(DISPLAY[d] for d in pareto['dominated']) or 'none'}. "
            f"{QWEN3_NOTE}."
        ),
        "fig4": (
            "Accuracy-per-joule: " + ", ".join(f"{DISPLAY[d]} {v:.3f} %/J" for d, v in eff.items())
            + ". Only Kev-4B and Kev-9B have a valid energy measurement in this run "
              "(Kev-0.8B's laptop GPU counter failed validation; Jev/GPT-OSS-20B are hosted, no local GPU)."
        ),
        "fig8": {
            DISPLAY[d]: {"total_incorrect": sum(c.values()), "dominant": (max(c, key=c.get) if c else "n/a"), "counts": dict(c)}
            for d, c in errors.items()
        },
    }
    (out / "interpretations.json").write_text(json.dumps(interp, indent=2))

    print(f"==> wrote 9 figures (PNG+PDF), table.md, interpretations.json to {out}")
    print()
    print(table)
    print("Figure 1:", interp["fig1"])
    print("Figure 4:", interp["fig4"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
