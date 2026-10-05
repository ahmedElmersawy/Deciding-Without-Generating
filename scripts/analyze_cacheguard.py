"""Summarize a cache-guard run (PLAN.md CG8): per decider, how often it serves a wrong cached
answer and how often it regenerates needlessly, on the test queries it answered.

Deciders: every LLM / Jev / Kev decider in <run>/calls-*.jsonl (one outcome per call, resolved
like arm 0: dwg.runfiles), plus two non-LLM baselines computed here from the stream:
  - threshold: reuse iff the GTE similarity >= tau;
  - cross-encoder: reuse iff P(duplicate) >= tau (scripts/cacheguard_crossencoder.py scores).
Each baseline's tau is picked on the DEV split only, two ways fixed in advance:
  - "@95% precision": the most reuse with >= 95% of reuses correct (a 5% error budget, the level
    the semantic-caching literature reports);
  - "max accuracy": the fewest total mistakes.
Baselines are scored on exactly the test queries the LLM deciders saw (so a pilot subset is
compared like for like), and also on the full test split. Also, when their inputs exist:
  - floor: the classifier fine-tuned on dev (scripts/cacheguard_floor.py), reuse iff P >= 0.5;
  - threshold -> Jev cascade: reuse above a similarity `hi`, regenerate below `lo`, ask Jev in
    between. (lo, hi) maximize dev accuracy using Jev's dev calls (ties: the narrower band, i.e.
    fewer Jev calls); test uses Jev's own test calls, so its $ is Jev's times the band share.

Rates are over all queries (wrong reuse + needless regeneration + correct = 1), with 95%
bootstrap CIs clustered by the query's class. "reuse precision" = share of reuses that were right.

Usage: python3 scripts/analyze_cacheguard.py results/replay/cacheguard-gsmplus
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

PRECISION_TARGET = 0.95


def state_id(r: dict) -> str:
    return f"{r['dataset']}:{r['split']}:{r['query_id']}"


def pick_tau(scores: np.ndarray, correct: np.ndarray) -> dict[str, float]:
    """Dev-split thresholds: most reuse at >= PRECISION_TARGET reuse precision, and max accuracy."""
    cands = np.unique(scores)
    best_prec, best_acc = (np.inf, -1.0), (np.inf, -1.0)
    for t in cands:
        reuse = scores >= t
        acc = float(np.mean(reuse == correct))
        if acc > best_acc[1]:
            best_acc = (t, acc)
        if reuse.any() and correct[reuse].mean() >= PRECISION_TARGET and reuse.mean() > best_prec[1]:
            best_prec = (t, float(reuse.mean()))
    return {"@95% precision": float(best_prec[0]), "max accuracy": float(best_acc[0])}


def summarize(choices_reuse: np.ndarray, correct: np.ndarray, clusters: np.ndarray) -> dict:
    wrong_reuse = (choices_reuse & ~correct).astype(float)
    needless = (~choices_reuse & correct).astype(float)
    ok = (choices_reuse == correct).astype(float)
    n_reuse = int(choices_reuse.sum())
    return {
        "n": int(len(correct)),
        "wrong_reuse": bootstrap_ci(wrong_reuse, clusters),
        "needless_regen": bootstrap_ci(needless, clusters),
        "accuracy": bootstrap_ci(ok, clusters),
        "reuse_rate": float(choices_reuse.mean()),
        "reuse_precision": float(correct[choices_reuse].mean()) if n_reuse else float("nan"),
    }


def cascade_decide(calls, by_id, lo, hi):
    """Reuse above `hi`, regenerate below `lo`, Jev's own call in between; also which calls hit the band."""
    sim = np.array([by_id[o["state_id"]]["similarity"] for o in calls])
    jev_reuse = np.array([o["choice"] == "reuse" for o in calls])
    in_band = (sim >= lo) & (sim < hi)
    return np.where(sim >= hi, True, np.where(sim < lo, False, jev_reuse)), in_band


def cascade_band(dev_calls: list[dict], by_id: dict) -> tuple[float, float]:
    """(lo, hi) maximizing dev accuracy over a 41-quantile similarity grid; ties: the narrower band."""
    dev_correct = np.array([by_id[o["state_id"]]["reuse_correct"] for o in dev_calls])
    grid = np.unique(np.quantile([by_id[o["state_id"]]["similarity"] for o in dev_calls], np.linspace(0, 1, 41)))
    grid = np.concatenate([[-np.inf], grid, [np.inf]])
    best = None
    for i, lo in enumerate(grid):
        for hi in grid[i:]:
            reuse, band = cascade_decide(dev_calls, by_id, lo, hi)
            key = (float(np.mean(reuse == dev_correct)), -float(band.mean()))
            if best is None or key > best[0]:
                best = (key, lo, hi)
    return float(best[1]), float(best[2])


def cascade_rows(jev_calls: list[dict], by_id: dict, dev: list[dict]) -> list[dict]:
    """Threshold -> Jev cascade, band tuned on Jev's dev calls, scored on Jev's test calls."""
    ok = [o for o in jev_calls if o["error"] is None]
    dev_calls = [o for o in ok if by_id[o["state_id"]]["split"] == "dev"]
    test_calls = [o for o in ok if by_id[o["state_id"]]["split"] == "test"]
    if not dev_calls or not test_calls:
        return []

    lo, hi = cascade_band(dev_calls, by_id)
    reuse, band = cascade_decide(test_calls, by_id, lo, hi)
    s = summarize(reuse, np.array([by_id[o["state_id"]]["reuse_correct"] for o in test_calls]),
                  np.array([by_id[o["state_id"]]["query_class"] for o in test_calls]))
    costs = [o["cost_usd"] for o in test_calls if o.get("cost_usd") is not None]
    s.update(decider=f"threshold -> Jev cascade (band [{lo:.3f}, {hi:.3f}); Jev asked {band.mean():.0%})",
             failures=len([o for o in jev_calls if o["error"] is not None and by_id[o["state_id"]]["split"] == "test"]),
             usd=float(np.mean(costs)) * float(band.mean()) if costs else None, p50_s=None)
    return [s]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    meta = json.loads((args.run / "meta.json").read_text())
    stream = [json.loads(line) for p in meta["states"] for line in open(p) if line.strip()]
    by_id = {state_id(r): r for r in stream}
    dev = [r for r in stream if r["split"] == "dev"]
    test = [r for r in stream if r["split"] == "test"]

    outcomes = [o for o in load_outcomes(args.run) if o["state_id"] in by_id]
    by_decider = defaultdict(list)
    for o in outcomes:
        by_decider[o["decider"]].append(o)
    # The test queries the deciders answered (dev calls exist only to tune the cascade band).
    seen = sorted({o["state_id"] for o in outcomes if by_id[o["state_id"]]["split"] == "test"})
    seen_rows = [by_id[s] for s in seen] if seen else test

    xenc_path = args.run / "scores-crossencoder.jsonl"
    xenc = {json.loads(line)["state_id"]: json.loads(line)["score"] for line in open(xenc_path)} if xenc_path.exists() else {}

    table = []
    test_ids = {state_id(r) for r in test}
    for d, rows in sorted(by_decider.items()):
        rows = [o for o in rows if o["state_id"] in test_ids]  # dev calls only tune the cascade
        if not rows:
            continue
        ok = [o for o in rows if o["error"] is None]
        reuse = np.array([o["choice"] == "reuse" for o in ok])
        correct = np.array([by_id[o["state_id"]]["reuse_correct"] for o in ok])
        clusters = np.array([by_id[o["state_id"]]["query_class"] for o in ok])
        s = summarize(reuse, correct, clusters)
        costs = [o["cost_usd"] for o in ok if o.get("cost_usd") is not None]
        lat = [o["latency_s"] for o in ok]
        s.update(decider=d, failures=len(rows) - len(ok), usd=float(np.mean(costs)) if costs else None,
                 p50_s=float(np.median(lat)) if lat else None)
        table.append(s)

    baselines = {"threshold": {r_id: by_id[r_id]["similarity"] for r_id in by_id}}
    if xenc:
        baselines["cross-encoder"] = xenc
    for name, score in baselines.items():
        dev_s = np.array([score[state_id(r)] for r in dev])
        taus = pick_tau(dev_s, np.array([r["reuse_correct"] for r in dev]))
        for rule, tau in taus.items():
            for label, rows in (("", seen_rows), (" (full test)", test if seen and len(seen) < len(test) else [])):
                if not rows:
                    continue
                sc = np.array([score[state_id(r)] for r in rows])
                s = summarize(sc >= tau, np.array([r["reuse_correct"] for r in rows]),
                              np.array([r["query_class"] for r in rows]))
                s.update(decider=f"{name} {rule}{label} (tau {tau:.3f})", failures=0, usd=0.0, p50_s=None)
                table.append(s)

    floor_path = args.run / "scores-floor.jsonl"
    if floor_path.exists():
        floor = {json.loads(line)["state_id"]: json.loads(line)["score"] for line in open(floor_path)}
        for label, rows in (("", seen_rows), (" (full test)", test if seen and len(seen) < len(test) else [])):
            rows = [r for r in rows if state_id(r) in floor]
            if rows:
                s = summarize(np.array([floor[state_id(r)] >= 0.5 for r in rows]),
                              np.array([r["reuse_correct"] for r in rows]), np.array([r["query_class"] for r in rows]))
                s.update(decider=f"floor (trained on dev){label}", failures=0, usd=0.0, p50_s=None)
                table.append(s)

    vcache_path = args.run / "scores-vcache.jsonl"
    if vcache_path.exists():
        # vCache only stores prompts it missed, so it is scored as a system: a hit is right iff the
        # answer it served was right; a miss is needless iff a correct earlier answer existed.
        vc = {json.loads(line)["state_id"]: json.loads(line) for line in open(vcache_path)}
        for label, rows in (("", seen_rows), (" (full test)", test if seen and len(seen) < len(test) else [])):
            rows = [r for r in rows if state_id(r) in vc]
            if rows:
                reuse = np.array([vc[state_id(r)]["reuse"] for r in rows])
                right = np.array([vc[state_id(r)]["served_correct"] if vc[state_id(r)]["reuse"] else r["reuse_correct"]
                                  for r in rows])
                s = summarize(reuse, right, np.array([r["query_class"] for r in rows]))
                delta = next(iter(vc.values()))["delta"]
                s.update(decider=f"vCache (delta {delta}){label}", failures=0, usd=0.0, p50_s=None)
                table.append(s)

    table.extend(cascade_rows(by_decider.get("jev", []), by_id, dev))

    def ci(x):
        return f"{x[0]:.3f} [{x[1]:.3f}, {x[2]:.3f}]"

    base_rate = np.mean([r["reuse_correct"] for r in seen_rows])
    lines = [
        f"# Cache guard: {args.run.name}",
        "",
        f"- test queries answered by the deciders: {len(seen_rows)} (reuse would be correct for {base_rate:.1%}); "
        f"dev queries for tuning: {len(dev)}.",
        "- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; "
        "both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.",
        "",
        "| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in table:
        usd = "—" if s["usd"] is None else ("local/free" if s["usd"] == 0 else f"{s['usd']:.2e}")
        lat = "—" if s["p50_s"] is None else f"{s['p50_s']:.2f}s"
        lines.append(f"| {s['decider']} | {s['n']} | {ci(s['wrong_reuse'])} | {ci(s['needless_regen'])} | "
                     f"{ci(s['accuracy'])} | {s['reuse_rate']:.3f} | {s['reuse_precision']:.3f} | {s['failures']} | {usd} | {lat} |")
    report = args.run / "report"
    report.mkdir(exist_ok=True)
    (report / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
