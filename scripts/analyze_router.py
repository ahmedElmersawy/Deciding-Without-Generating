"""Summarize the router run (PLAN.md R6): quality vs cost for every decider, against the always-small,
always-large and random-mix baselines, plus the cost-quality figure (fig 17).

Quality of a routing = mean recorded score of the model each prompt is sent to (RouterBench's own
grading; GSM8K scores in quarters); $ per query = the decider's mean $ per decision + the routed
model's recorded $. Each decider is scored two ways:
  - its own choice (the option it picked; every repeat counted), with a 95% bootstrap CI over prompts;
  - as a curve: P(large) per prompt (mean over repeats; Jev / Kev report option probabilities, LLMs
    a verbalized confidence in their choice) swept as a threshold. PGR(rate) = share of the
    large - small quality gap recovered when that share of prompts goes large; APGR = mean PGR over
    rates 0..1 (RouteLLM's metric). A random mix has PGR(rate) = rate, so APGR 0.5 = no routing signal.
The floor's P(large) comes from scripts/router_floor.py.

Usage: python3 scripts/analyze_router.py results/replay/router-routerbench
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.runfiles import load_outcomes  # noqa: E402
from dwg.stats import bootstrap_ci  # noqa: E402

LABEL = {"jev": "Jev", "llm:openrouter/openai/gpt-5.6-sol": "GPT-5.6", "llm:openrouter/openai/gpt-oss-20b": "GPT-OSS-20B",
         "llm:local/qwen3-8b": "Qwen3-8B", "kev-4b": "Kev-4B", "floor": "Floor (trained on RouterBench)"}
COLOR = {"jev": "#2a78d6", "llm:openrouter/openai/gpt-5.6-sol": "#c9a000", "llm:openrouter/openai/gpt-oss-20b": "#eb6834",
         "llm:local/qwen3-8b": "#a8431c", "kev-4b": "#1baf7a", "floor": "#7d5fd6"}
MARKER = {"jev": "o", "llm:openrouter/openai/gpt-5.6-sol": "D", "llm:openrouter/openai/gpt-oss-20b": "s",
          "llm:local/qwen3-8b": "v", "kev-4b": "^", "floor": "X"}


def p_large(call: dict) -> float:
    probs = call.get("probabilities") or {}
    if "large" in probs:
        return float(probs["large"])
    conf = call.get("confidence")
    conf = 0.5 if conf is None else float(conf)
    return conf if call["choice"] == "large" else 1.0 - conf


def pgr_curve(score: np.ndarray, small: np.ndarray, large: np.ndarray):
    """(large-call rate, quality) as the threshold on P(large) sweeps; ties broken by prompt order."""
    order = np.argsort(-score, kind="stable")
    gain = (large - small)[order]
    rates = np.arange(len(score) + 1) / len(score)
    quality = small.mean() + np.concatenate([[0.0], np.cumsum(gain)]) / len(score)
    return rates, quality


def apgr(rates, quality, q_small, q_large, grid=np.linspace(0, 1, 101)):
    pgr = (np.interp(grid, rates, quality) - q_small) / (q_large - q_small)
    return float(pgr.mean())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    meta = json.loads((args.run / "meta.json").read_text())
    stream = [json.loads(line) for p in meta["states"] for line in open(p) if line.strip()]
    sid = lambda r: f"{r['dataset']}:{r['split']}:{r['query_id']}"
    test = [r for r in stream if r["split"] == "test"]
    by_id = {sid(r): r for r in test}
    small = np.array([r["small_score"] for r in test])
    large = np.array([r["large_score"] for r in test])
    c_small = np.array([r["small_cost"] for r in test])
    c_large = np.array([r["large_cost"] for r in test])
    q_small, q_large = small.mean(), large.mean()

    calls = defaultdict(list)
    for o in load_outcomes(args.run):
        if o["state_id"] in by_id:
            calls[o["decider"]].append(o)

    rows, curves = [], {}
    rows.append(dict(name="Always small (Mixtral)", n=len(test), q=(q_small, q_small, q_small), large=0.0,
                     usd=float(c_small.mean()), apgr=None, vs_random=0.0, fail=0))
    rows.append(dict(name="Always large (GPT-4)", n=len(test), q=(q_large, q_large, q_large), large=1.0,
                     usd=float(c_large.mean()), apgr=None, vs_random=0.0, fail=0))
    idx = {s: i for i, s in enumerate(by_id)}
    for d, cs in sorted(calls.items()):
        ok = [c for c in cs if c["error"] is None]
        if not ok:
            continue
        i = np.array([idx[c["state_id"]] for c in ok])
        go_large = np.array([c["choice"] == "large" for c in ok])
        q = np.where(go_large, large[i], small[i])
        dec_usd = np.mean([c["cost_usd"] for c in ok if c.get("cost_usd") is not None] or [0.0])
        usd = dec_usd + np.where(go_large, c_large[i], c_small[i]).mean()
        rate = go_large.mean()
        # Against a random mix on the same prompts this decider answered (a pilot covers a subset).
        vs_random = q.mean() - (small[i].mean() + rate * (large[i].mean() - small[i].mean()))
        per_prompt = defaultdict(list)
        for c in ok:
            per_prompt[c["state_id"]].append(p_large(c))
        covered = [s for s in by_id if s in per_prompt]
        score = np.array([np.mean(per_prompt[s]) for s in covered])
        ci = [idx[s] for s in covered]
        r_, qq = pgr_curve(score, small[ci], large[ci])
        curves[d] = (r_, (qq - small[ci].mean()) / (large[ci].mean() - small[ci].mean()))
        rows.append(dict(name=LABEL.get(d, d), key=d, n=len(ok), q=bootstrap_ci(q, i), large=float(rate), usd=float(usd),
                         apgr=apgr(r_, qq, small[ci].mean(), large[ci].mean()), vs_random=float(vs_random),
                         fail=len(cs) - len(ok), covered=len(covered)))
    floor_path = args.run / "scores-floor.jsonl"
    if floor_path.exists():
        fl = {json.loads(line)["state_id"]: json.loads(line)["score"] for line in open(floor_path)}
        score = np.array([fl[s] for s in by_id])
        go_large = score >= 0.5
        q = np.where(go_large, large, small)
        r_, qq = pgr_curve(score, small, large)
        curves["floor"] = (r_, (qq - q_small) / (q_large - q_small))
        rows.append(dict(name=LABEL["floor"], key="floor", n=len(test), q=bootstrap_ci(q, np.arange(len(q))),
                         large=float(go_large.mean()), usd=float(np.where(go_large, c_large, c_small).mean()),
                         apgr=apgr(r_, qq, q_small, q_large), vs_random=float(q.mean() - (q_small + go_large.mean() * (q_large - q_small))),
                         fail=0))

    lines = [
        f"# Router: {args.run.name} (small = Mixtral-8x7B, large = GPT-4; {len(test)} test prompts)",
        "",
        f"- quality = mean recorded score of the routed model (small alone {q_small:.3f}, large alone {q_large:.3f}); "
        f"$ = decider $ + routed model's recorded $ per query; 'vs random' = quality minus a random mix sending the same "
        f"share to the large model; APGR = mean share of the quality gap recovered over all large-call rates "
        f"(random mix = 0.5).",
        "",
        "| router | n | quality [95% CI] | sent to large | $ / query | vs random mix | APGR | failures |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        q = r["q"]
        ap = "—" if r["apgr"] is None else f"{r['apgr']:.3f}"
        lines.append(f"| {r['name']} | {r['n']} | {q[0]:.3f} [{q[1]:.3f}, {q[2]:.3f}] | {r['large']:.1%} | "
                     f"{r['usd']:.2e} | {r['vs_random']:+.3f} | {ap} | {r['fail']} |")
    report = args.run / "report"
    report.mkdir(exist_ok=True)
    (report / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    INK, INK_2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    fig, ax = plt.subplots(figsize=(7.5, 5.6))
    ax.plot([0, 1], [0, 1], color="#8a8984", linestyle="--", linewidth=1.4, label="Random mix (APGR 0.5)", zorder=1)
    for d, (r_, pgr) in curves.items():
        ax.plot(r_, pgr, color=COLOR.get(d, INK_2), linewidth=1.8, zorder=2,
                label=f"{LABEL.get(d, d)} (APGR {next(x['apgr'] for x in rows if x.get('key') == d):.2f})")
        own = next(x for x in rows if x.get("key") == d)
        ax.scatter([own["large"]], [(own["q"][0] - q_small) / (q_large - q_small)], marker=MARKER.get(d, "o"), s=80,
                   color=COLOR.get(d, INK_2), edgecolor=BG, linewidth=1.2, zorder=3)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_xlabel("Share of prompts sent to the large model (cost)", color=INK_2)
    ax.set_ylabel("Share of the small-to-large quality gap recovered", color=INK_2)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("Figure 17. Router: quality recovered vs. large-model share (markers = own choice)", loc="left",
                 fontsize=11, color=INK)
    fig.tight_layout()
    out = Path("results/replay/router-paper_figures")
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "fig17_router_pgr.png", dpi=200, facecolor=BG, metadata={"Software": None})
    fig.savefig(out / "fig17_router_pgr.pdf", facecolor=BG, metadata={"CreationDate": None, "Producer": None})
    print(f"==> report in {report}, figure in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
