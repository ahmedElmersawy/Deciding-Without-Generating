"""Summarize an in-loop run (PLAN.md U4): per arm, pass^k, mean reward with a 95% CI clustered
by task, $ per successful task, the decision share of agent cost and latency, and how often
the decider failed and G decided instead.

pass^k is tau-bench's reliability metric: for a task with n trials and c successes,
C(c, k) / C(n, k) is the chance that k trials drawn from the n all succeed; averaged over tasks.
Success = reward 1. Each (arm, task, trial) counts once, as its first attempt that was not an
infra error (dwg.errors), like the arm-0 analysis.

Usage: python3 scripts/analyze_inloop.py results/inloop/<domain>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.errors import is_infra_error  # noqa: E402
from dwg.stats import bootstrap_ci  # noqa: E402

ARM_LABEL = {
    "A": "A: Jev decides + G",
    "B": "B: G decides (constrained) + G",
    "C": "C: G alone (single call)",
    "D": "D: small LLM decides + G",
    "E": "E: Kev decides + G",
}


def resolve(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["arm"], r["task_id"], r["trial"])].append(r)
    out, missing = [], defaultdict(int)
    for (arm, _, _), rs in groups.items():
        real = [r for r in rs if r.get("error") is None or not is_infra_error(r["error"])]
        if real:
            out.append(real[0])
        else:
            missing[arm] += 1
    return out, missing


def pass_hat_k(successes_by_task: dict[str, list[bool]], k: int) -> float:
    vals = [comb(sum(s), k) / comb(len(s), k) for s in successes_by_task.values() if len(s) >= k]
    return float(np.mean(vals)) if vals else float("nan")


def summarize_arm(rows: list[dict]) -> dict:
    ok = [r for r in rows if r.get("error") is None and r.get("reward") is not None]
    failed = [r for r in rows if r not in ok]
    by_task = defaultdict(list)
    for r in ok:
        by_task[r["task_id"]].append(r["reward"] >= 1 - 1e-6)
    n_trials = min((len(v) for v in by_task.values()), default=0)
    succ = sum(s for v in by_task.values() for s in v)

    def s(key):
        return float(np.nansum([r.get(key) or 0.0 for r in ok]))

    dec_cost, exe_cost, usr_cost = s("decision_cost_usd"), s("exec_cost_usd"), s("user_cost_usd")
    dec_lat, exe_lat = s("decision_latency_s"), s("exec_latency_s")
    turns = s("n_turns")
    return {
        "episodes": len(ok),
        "episode_errors": len(failed),
        "tasks": len(by_task),
        "reward": bootstrap_ci([r["reward"] for r in ok], [r["task_id"] for r in ok]) if ok else (float("nan"),) * 3,
        "pass_k": {k: pass_hat_k(by_task, k) for k in range(1, n_trials + 1)},
        "successes": succ,
        "agent_cost_usd": dec_cost + exe_cost,
        "user_cost_usd": usr_cost,
        "usd_per_success": (dec_cost + exe_cost) / succ if succ else float("nan"),
        "decision_share_cost": dec_cost / (dec_cost + exe_cost) if dec_cost + exe_cost else float("nan"),
        "decision_share_latency": dec_lat / (dec_lat + exe_lat) if dec_lat + exe_lat else float("nan"),
        "agent_latency_per_turn_s": (dec_lat + exe_lat) / turns if turns else float("nan"),
        "turns_per_episode": turns / len(ok) if ok else float("nan"),
        "decider_fallback_rate": s("n_decider_failed") / turns if turns else float("nan"),
    }


# Paired arm comparisons. Every arm runs the same (task, trial) with the same user-simulator seed,
# so differences are taken per task (mean over its trials), then bootstrapped over tasks.
# A-B isolates who decides (Jev vs. G, same executor); A-C is Jev+G vs. the production single
# call; D-A and E-A put the other deciders against Jev.
PAIRS = [("A", "B"), ("A", "C"), ("B", "C"), ("D", "A"), ("E", "A")]


def paired_task_diff(rows_a: list[dict], rows_b: list[dict], value, n_boot: int = 10000, seed: int = 0) -> dict:
    """Mean over tasks of (mean value in arm a) - (mean value in arm b), with a 95% bootstrap
    CI over tasks, on (task, trial) pairs both arms finished."""
    a = {(r["task_id"], r["trial"]): value(r) for r in rows_a}
    b = {(r["task_id"], r["trial"]): value(r) for r in rows_b}
    by_task = defaultdict(list)
    for key in a.keys() & b.keys():
        if a[key] is not None and b[key] is not None:
            by_task[key[0]].append(a[key] - b[key])
    diffs = np.array([np.mean(v) for v in by_task.values()])
    if diffs.size == 0:
        return {"tasks": 0, "pairs": 0, "diff": float("nan"), "ci": (float("nan"), float("nan")), "significant": False}
    rng = np.random.default_rng(seed)
    boot = diffs[rng.integers(0, diffs.size, size=(n_boot, diffs.size))].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return {"tasks": int(diffs.size), "pairs": int(sum(len(v) for v in by_task.values())),
            "diff": float(diffs.mean()), "ci": (float(lo), float(hi)), "significant": not (lo <= 0 <= hi)}


def agent_cost(r: dict):
    parts = [r.get("decision_cost_usd"), r.get("exec_cost_usd")]
    return None if all(p is None for p in parts) else float(sum(p or 0.0 for p in parts))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    rows = []
    for path in sorted(args.run.glob("episodes-*.jsonl")):
        with path.open() as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    if not rows:
        raise SystemExit(f"no episodes in {args.run}")
    rows, missing = resolve(rows)
    metas = {p.stem.removeprefix("meta-"): json.loads(p.read_text()) for p in args.run.glob("meta-*.json")}
    summary = {arm: summarize_arm([r for r in rows if r["arm"] == arm]) for arm in sorted({r["arm"] for r in rows})}
    for arm in summary:
        summary[arm]["still_missing_infra"] = missing.get(arm, 0)

    ks = sorted({k for s in summary.values() for k in s["pass_k"]})

    def f(x, fmt="{:.3f}"):
        return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else fmt.format(x)

    lines = [
        f"# In-loop run — {args.run.name}",
        "",
        "- reward = tau2's episode reward, mean with a 95% bootstrap CI clustered by task; pass^k = chance that "
        "k trials of the same task all succeed (tau-bench).",
        "- $ = agent side (decision + execution); the user simulator's $ is listed apart. G and the user are "
        "priced by litellm's price map, deciders by OpenRouter's reported cost.",
        "- decision share = decider's part of the agent's $ / latency (0 for arm C by construction). "
        "Fallback = turns where the decider failed and G decided instead.",
        "",
        "| arm | G | decider | episodes | errors | reward [95% CI] | " + " | ".join(f"pass^{k}" for k in ks)
        + " | $/success | decision share $ | decision share latency | s/turn | turns/ep | fallback |",
        "|---|---|---|---|---|---|" + "---|" * len(ks) + "---|---|---|---|---|---|",
    ]
    for arm, s in summary.items():
        m = metas.get(arm, {})
        r = s["reward"]
        lines.append(
            f"| {ARM_LABEL.get(arm, arm)} | {m.get('g_model', '?')} | {m.get('decider') or '—'} | {s['episodes']} | "
            f"{s['episode_errors']} (+{s['still_missing_infra']} infra) | {f(r[0])} [{f(r[1])}, {f(r[2])}] | "
            + " | ".join(f(s["pass_k"].get(k)) for k in ks)
            + f" | {f(s['usd_per_success'], '{:.4f}')} | {f(s['decision_share_cost'], '{:.1%}')} | "
            f"{f(s['decision_share_latency'], '{:.1%}')} | {f(s['agent_latency_per_turn_s'], '{:.2f}')} | "
            f"{f(s['turns_per_episode'], '{:.1f}')} | {f(s['decider_fallback_rate'], '{:.1%}')} |"
        )
    ok = {arm: [r for r in rows if r["arm"] == arm and r.get("error") is None and r.get("reward") is not None]
          for arm in summary}
    paired = {}
    for a, b in PAIRS:
        if a in ok and b in ok:
            paired[f"{a}-{b}"] = {
                "reward": paired_task_diff(ok[a], ok[b], lambda r: r["reward"]),
                "agent_usd_per_episode": paired_task_diff(ok[a], ok[b], agent_cost),
                "wall_s_per_episode": paired_task_diff(ok[a], ok[b], lambda r: r.get("wall_s")),
            }
    if paired:
        lines += [
            "",
            "## Paired arm differences (first arm minus second)",
            "",
            "Same (task, trial) and user seed in both arms; per-task mean difference, 95% bootstrap CI over tasks. "
            "Starred = CI excludes 0.",
            "",
            "| comparison | tasks (pairs) | reward diff [95% CI] | agent $/episode diff [95% CI] | wall s/episode diff [95% CI] |",
            "|---|---|---|---|---|",
        ]
        for name, c in paired.items():
            def cell(x, fmt):
                star = "*" if x["significant"] else ""
                return f"{fmt.format(x['diff'])}{star} [{fmt.format(x['ci'][0])}, {fmt.format(x['ci'][1])}]"
            lines.append(f"| {name} | {c['reward']['tasks']} ({c['reward']['pairs']}) | {cell(c['reward'], '{:+.3f}')} | "
                         f"{cell(c['agent_usd_per_episode'], '{:+.4f}')} | {cell(c['wall_s_per_episode'], '{:+.1f}')} |")
    report = args.run / "report"
    report.mkdir(exist_ok=True)
    (report / "summary.md").write_text("\n".join(lines) + "\n")
    (report / "summary.json").write_text(json.dumps({"arms": summary, "paired": paired}, indent=2, default=float))
    print("\n".join(lines))
    print(f"==> report in {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
