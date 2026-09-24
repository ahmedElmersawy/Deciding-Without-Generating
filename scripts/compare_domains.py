#!/usr/bin/env python3
"""Side-by-side comparison of two decision-replay runs (e.g. mock-pilot vs airline).

Reuses the same metric computation as make_paper_figures.py / post_experiment_analysis.py
(dwg.stats, the run's own calls-*.jsonl + meta-*.json) so numbers never diverge from those
reports. For every decider present in BOTH runs: accuracy, latency, ECE, consistency side by
side, plus the delta, plus a paired-style significance flag (bootstrap CI on the difference,
resampled independently per domain since they're different state universes — NOT a paired
cluster bootstrap, which only applies when both sides share the same states).

Usage:
    python3 scripts/compare_domains.py results/replay/mock-pilot results/replay/airline \
        --labels Mock Airline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.runfiles import load_calls, load_decider_metas  # noqa: E402
from dwg.stats import bootstrap_ci, brier_score, describe, expected_calibration_error  # noqa: E402

DISPLAY = {
    "jev": "Jev",
    "llm:openrouter/openai/gpt-oss-20b": "GPT-OSS-20B",
    "kev-0.8b": "Kev-0.8B",
    "kev-4b": "Kev-4B",
    "kev-9b": "Kev-9B",
    "cascade-kev-4b-t0.9": "Cascade (t=0.9)",
}
INK, INK_2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
COLOR = {
    "jev": "#2a78d6", "llm:openrouter/openai/gpt-oss-20b": "#eb6834",
    "kev-0.8b": "#8fd9c4", "kev-4b": "#1baf7a", "kev-9b": "#0b7d54",
    "cascade-kev-4b-t0.9": "#7d5fd6",
}


def decider_metrics(run: Path) -> dict[str, dict]:
    rows = load_calls(run)
    dmetas = load_decider_metas(run)
    out = {}
    for d in sorted({r["decider"] for r in rows}):
        drows = [r for r in rows if r["decider"] == d]
        ok = [r for r in drows if r["error"] is None]
        if not ok:
            continue
        clusters = [r["state_id"] for r in ok]
        acc = bootstrap_ci([r["correct"] for r in ok], clusters)
        lat = describe([r["latency_s"] * 1000 for r in ok])
        with_conf = [r for r in ok if r["confidence"] is not None]
        conf = [r["confidence"] for r in with_conf]
        corr = [r["correct"] for r in with_conf]
        ece = expected_calibration_error(conf, corr) if conf else float("nan")
        brier = brier_score(conf, corr) if conf else float("nan")
        from collections import Counter, defaultdict
        by_state = defaultdict(list)
        for r in ok:
            by_state[r["state_id"]].append(r["choice"])
        cons_vals = [Counter(c).most_common(1)[0][1] / len(c) for c in by_state.values()]
        consistency = bootstrap_ci(cons_vals, list(by_state))
        dm = dmetas.get(d, {})
        block = dm.get("energy_block")
        energy = (block["joules"] / block["calls"]) if block and block.get("calls") else None
        out[d] = dict(n=len(ok), n_states=len(by_state), accuracy=acc, latency_ms=lat, ece=ece,
                      brier=brier, consistency=consistency, energy_j=energy)
    return out


def unpaired_diff_ci(run_a: Path, run_b: Path, decider: str, n_boot=10000, seed=0):
    """Independent-sample bootstrap on the accuracy difference: valid across two DIFFERENT
    state universes (mock vs airline), unlike the paired cluster bootstrap used within one
    run's own states (post_experiment_analysis.py's Phase A)."""
    def per_state_acc(run):
        rows = [r for r in load_calls(run) if r["decider"] == decider and r["error"] is None]
        from collections import defaultdict
        by_state = defaultdict(list)
        for r in rows:
            by_state[r["state_id"]].append(r["correct"])
        return np.array([np.mean(v) for v in by_state.values()])

    a, b = per_state_acc(run_a), per_state_acc(run_b)
    if len(a) == 0 or len(b) == 0:
        return None
    rng = np.random.default_rng(seed)
    boot_a = a[rng.integers(0, len(a), size=(n_boot, len(a)))].mean(axis=1)
    boot_b = b[rng.integers(0, len(b), size=(n_boot, len(b)))].mean(axis=1)
    diff = boot_a - boot_b
    lo, hi = np.quantile(diff, [0.025, 0.975])
    return dict(mean_diff=float(a.mean() - b.mean()), ci_lo=float(lo), ci_hi=float(hi),
                n_a=len(a), n_b=len(b), significant=not (lo <= 0 <= hi))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_a", type=Path)
    parser.add_argument("run_b", type=Path)
    parser.add_argument("--labels", nargs=2, default=None, metavar=("LABEL_A", "LABEL_B"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    label_a, label_b = args.labels or (args.run_a.name, args.run_b.name)
    out = args.out or Path("results/replay") / f"compare-{args.run_a.name}-vs-{args.run_b.name}"
    out.mkdir(parents=True, exist_ok=True)

    metrics_a = decider_metrics(args.run_a)
    metrics_b = decider_metrics(args.run_b)
    common = sorted(set(metrics_a) & set(metrics_b))
    if not common:
        raise SystemExit(f"no deciders in common between {args.run_a} and {args.run_b}")

    lines = [f"# {label_a} vs {label_b} — decider comparison", "",
             f"- {label_a}: {args.run_a}", f"- {label_b}: {args.run_b}",
             "- Significance: independent-sample bootstrap on accuracy (NOT paired — different state universes)",
             "",
             f"| Decider | {label_a} acc | {label_b} acc | Diff | 95% CI | Sig? | "
             f"{label_a} p50 lat (ms) | {label_b} p50 lat (ms) | {label_a} ECE | {label_b} ECE |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    sig_results = {}
    for d in common:
        a, b = metrics_a[d], metrics_b[d]
        sig = unpaired_diff_ci(args.run_a, args.run_b, d)
        sig_results[d] = sig
        diff_pct = (a["accuracy"][0] - b["accuracy"][0]) * 100
        ci_str = f"[{sig['ci_lo']*100:+.1f}, {sig['ci_hi']*100:+.1f}]" if sig else "n/a"
        sig_str = ("YES" if sig["significant"] else "no") if sig else "n/a"
        lines.append(
            f"| {DISPLAY.get(d, d)} | {a['accuracy'][0]*100:.1f}% | {b['accuracy'][0]*100:.1f}% | "
            f"{diff_pct:+.1f}pts | {ci_str} | {sig_str} | "
            f"{a['latency_ms']['p50']:.1f} | {b['latency_ms']['p50']:.1f} | "
            f"{a['ece']:.3f} | {b['ece']:.3f} |"
        )
    (out / "comparison.md").write_text("\n".join(lines) + "\n")
    (out / "comparison.json").write_text(json.dumps(
        dict(labels=[label_a, label_b], metrics_a=metrics_a, metrics_b=metrics_b, significance=sig_results),
        indent=2, default=str))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    xs = np.arange(len(common))
    width = 0.35
    for i, (run_metrics, label, offset) in enumerate([(metrics_a, label_a, -width/2), (metrics_b, label_b, width/2)]):
        vals = [run_metrics[d]["accuracy"][0] * 100 for d in common]
        err_lo = [run_metrics[d]["accuracy"][0] * 100 - run_metrics[d]["accuracy"][1] * 100 for d in common]
        err_hi = [run_metrics[d]["accuracy"][2] * 100 - run_metrics[d]["accuracy"][0] * 100 for d in common]
        colors = [COLOR.get(d, "#888") for d in common]
        alpha = 1.0 if i == 0 else 0.55
        ax.bar(xs + offset, vals, width, color=colors, alpha=alpha, zorder=2,
               label=label, edgecolor=INK if i == 1 else "none", linewidth=1)
        ax.errorbar(xs + offset, vals, yerr=[err_lo, err_hi], fmt="none", ecolor=INK, elinewidth=1, capsize=3, zorder=3)
    ax.set_xticks(xs, [DISPLAY.get(d, d) for d in common], rotation=15, ha="right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(True, axis="y", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylabel("Accuracy (%)", color=INK_2)
    ax.set_title(f"Figure 11. {label_a} vs {label_b}: accuracy by decider", loc="left", fontsize=12, color=INK)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig11_domain_comparison.png", dpi=200, facecolor=BG)
    fig.savefig(out / "fig11_domain_comparison.pdf", facecolor=BG)
    plt.close(fig)

    print(f"==> wrote comparison.md, comparison.json, fig11_domain_comparison.{{png,pdf}} to {out}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
