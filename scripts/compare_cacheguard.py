"""Paired significance for the cache-guard claims (DECISIONS.md 2026-10-05): every method scored on
the same test queries, per-query correctness (LLM deciders: mean over their repeats), differences
bootstrapped over classes (the query's id_set / GSM-Plus seed), 10,000 resamples. Also the
wrong-reuse rate for the SearchQueries safety claim.

Methods as in analyze_cacheguard.py: threshold and cross-encoder at their dev-tuned max-accuracy tau,
floor at 0.5, vCache as a system, threshold -> Jev cascade at its dev-tuned band.

Usage: python3 scripts/compare_cacheguard.py   ->  results/replay/cacheguard-paired.md
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

GPT56, OSS = "llm:openrouter/openai/gpt-5.6-sol", "llm:openrouter/openai/gpt-oss-20b"
CLAIMS = {  # (a, b): "a minus b"
    "gsmplus": [("jev", "threshold"), ("jev", "vcache"), ("jev", "floor"), ("jev", "kev-4b"), (GPT56, "jev"), (OSS, "jev"),
                ("cascade", "jev")],
    "lmarena": [("threshold", "jev"), ("cascade", "threshold"), ("floor", "threshold"), ("kev-4b", "jev")],
    "searchqueries": [("jev", "threshold"), (GPT56, "jev"), ("jev", "floor")],
}
NAME = {"jev": "Jev", "threshold": "Threshold", "vcache": "vCache", "floor": "Floor", "cascade": "Threshold→Jev",
        "kev-4b": "Kev-4B", GPT56: "GPT-5.6", OSS: "GPT-OSS-20B"}


def per_query(name: str):
    """{state_id: (correct in [0,1], wrong_reuse in [0,1])} on the test split, per method."""
    run = ROOT / f"results/replay/cacheguard-{name}"
    meta = json.loads((run / "meta.json").read_text())
    stream = [json.loads(line) for p in meta["states"] for line in open(ROOT / p) if line.strip()]
    by_id = {ac.state_id(r): r for r in stream}
    test = [r for r in stream if r["split"] == "test"]
    dev = [r for r in stream if r["split"] == "dev"]
    methods = {}
    calls = defaultdict(list)
    for o in load_outcomes(run):
        if o["state_id"] in by_id and o["error"] is None:
            calls[o["decider"]].append(o)
    for d, cs in calls.items():
        acc = defaultdict(list)
        for o in cs:
            if by_id[o["state_id"]]["split"] == "test":
                r = by_id[o["state_id"]]
                reuse = o["choice"] == "reuse"
                acc[o["state_id"]].append((float(reuse == r["reuse_correct"]), float(reuse and not r["reuse_correct"])))
        methods[d] = {k: tuple(np.mean(v, axis=0)) for k, v in acc.items()}
    jev = calls.get("jev", [])
    jev_dev = [o for o in jev if by_id[o["state_id"]]["split"] == "dev"]
    jev_test = [o for o in jev if by_id[o["state_id"]]["split"] == "test"]
    if jev_dev and jev_test:
        lo, hi = ac.cascade_band(jev_dev, by_id)
        reuse, _ = ac.cascade_decide(jev_test, by_id, lo, hi)
        acc = defaultdict(list)
        for o, ru in zip(jev_test, reuse):
            r = by_id[o["state_id"]]
            acc[o["state_id"]].append((float(ru == r["reuse_correct"]), float(ru and not r["reuse_correct"])))
        methods["cascade"] = {k: tuple(np.mean(v, axis=0)) for k, v in acc.items()}
    tau = ac.pick_tau(np.array([r["similarity"] for r in dev]), np.array([r["reuse_correct"] for r in dev]))["max accuracy"]
    methods["threshold"] = {ac.state_id(r): (float((r["similarity"] >= tau) == r["reuse_correct"]),
                                             float(r["similarity"] >= tau and not r["reuse_correct"])) for r in test}
    fp = run / "scores-floor.jsonl"
    if fp.exists():
        fl = {json.loads(line)["state_id"]: json.loads(line)["score"] for line in open(fp)}
        methods["floor"] = {ac.state_id(r): (float((fl[ac.state_id(r)] >= 0.5) == r["reuse_correct"]),
                                             float(fl[ac.state_id(r)] >= 0.5 and not r["reuse_correct"]))
                            for r in test if ac.state_id(r) in fl}
    vp = run / "scores-vcache.jsonl"
    if vp.exists():
        vc = {json.loads(line)["state_id"]: json.loads(line) for line in open(vp)}
        m = {}
        for r in test:
            v = vc.get(ac.state_id(r))
            if v is None:
                continue
            right = v["served_correct"] if v["reuse"] else r["reuse_correct"]
            m[ac.state_id(r)] = (float(v["reuse"] == right) if v["reuse"] else float(not r["reuse_correct"]),
                                 float(v["reuse"] and not v["served_correct"]))
        methods["vcache"] = m
    return methods, {ac.state_id(r): r["query_class"] for r in test}


def paired(a: dict, b: dict, cls: dict, k: int, n_boot=10_000, seed=0):
    ids = sorted(set(a) & set(b))
    diff = np.array([a[i][k] - b[i][k] for i in ids])
    keys, inv = np.unique([cls[i] for i in ids], return_inverse=True)
    sums, counts = np.bincount(inv, weights=diff, minlength=len(keys)), np.bincount(inv, minlength=len(keys))
    picks = np.random.default_rng(seed).integers(0, len(keys), size=(n_boot, len(keys)))
    boots = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return float(diff.mean()), float(lo), float(hi), len(ids)


def main() -> int:
    lines = ["# Cache guard: paired differences (same test queries, bootstrap over classes)", "",
             "Accuracy difference in points (a − b); * = 95% CI excludes 0.", ""]
    for name, claims in CLAIMS.items():
        methods, cls = per_query(name)
        lines += [f"## {name}", "", "| a − b | queries | accuracy diff [95% CI] | wrong-reuse diff [95% CI] |", "|---|---|---|---|"]
        for a, b in claims:
            if a not in methods or b not in methods:
                continue
            acc, wr = paired(methods[a], methods[b], cls, 0), paired(methods[a], methods[b], cls, 1)
            star = lambda x: "*" if not (x[1] <= 0 <= x[2]) else ""
            lines.append(f"| {NAME[a]} − {NAME[b]} | {acc[3]} | {acc[0]*100:+.1f}{star(acc)} [{acc[1]*100:+.1f}, {acc[2]*100:+.1f}] | "
                         f"{wr[0]*100:+.1f}{star(wr)} [{wr[1]*100:+.1f}, {wr[2]*100:+.1f}] |")
        lines.append("")
    out = ROOT / "results/replay/cacheguard-paired.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
