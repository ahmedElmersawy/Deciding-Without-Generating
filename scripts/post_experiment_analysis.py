#!/usr/bin/env python3
"""Post-experiment rigor pass on a decision-replay run (Phases A-E of the 2026-09-23 review).

Every number here is computed from the same source data as analyze_decisions.py /
make_paper_figures.py (calls-*.jsonl, meta-*.json, the states file) — nothing is eyeballed
off the summary report. Phases:

  A. Paired-cluster-bootstrap significance test for Kev-4B vs Kev-9B (and other pairs),
     plus a states-needed estimate to narrow the CI further.
  B. Data-integrity checks: row counts vs expected, warmup leakage, cache-hit leakage,
     missing states, resumed-retry accounting.
  C. Per-state cross-tabulation: which deciders get which states right/wrong, and where.
  D. Post-hoc temperature scaling (2-fold, state-level split, so it's not evaluated on its
     own fitting data) + a confidence-gated Kev-4B -> GPT-OSS-20B cascade simulation.
  E. Accuracy/ms, accuracy/J, and a normalized composite efficiency table.

Usage:
    python3 scripts/post_experiment_analysis.py results/replay/mock-pilot
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
from dwg.stats import bootstrap_ci, expected_calibration_error  # noqa: E402

DISPLAY = {
    "jev": "Jev",
    "llm:openrouter/openai/gpt-oss-20b": "GPT-OSS-20B",
    "kev-0.8b": "Kev-0.8B",
    "kev-4b": "Kev-4B",
    "kev-9b": "Kev-9B",
    "cascade-kev-4b-t0.9": "Cascade (Kev-4B→GPT-OSS, t=0.9)",
}
# Kev-4B's own already-validated gross J/decision from its standalone replay in this same
# run (results/replay/mock-pilot/meta-kev-4b.json: energy_block.joules / .calls). The cascade
# always calls Kev-4B first, so it always pays this; see CascadeDecider's docstring for why
# the cascade run itself doesn't re-meter energy live.
CASCADE_REUSED_ENERGY_J = 18.333289230769232


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


# ---------------------------------------------------------------- Phase A ---

def paired_diff_ci(rows_a, rows_b, n_boot=10000, seed=0):
    a_by_state, b_by_state = defaultdict(list), defaultdict(list)
    for r in rows_a:
        a_by_state[r["state_id"]].append(r["correct"])
    for r in rows_b:
        b_by_state[r["state_id"]].append(r["correct"])
    common = sorted(set(a_by_state) & set(b_by_state))
    a_acc = np.array([np.mean(a_by_state[s]) for s in common])
    b_acc = np.array([np.mean(b_by_state[s]) for s in common])
    diff = a_acc - b_acc
    rng = np.random.default_rng(seed)
    n = len(common)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot = diff[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return dict(mean_diff=float(diff.mean()), ci_lo=float(lo), ci_hi=float(hi),
                n_states=n, std_diff=float(diff.std(ddof=1)), significant=not (lo <= 0 <= hi))


def states_needed(std_diff: float, n_current: int, target_half_widths=(0.05, 0.03)) -> dict:
    out = {}
    for hw in target_half_widths:
        n_needed = (1.96 * std_diff / hw) ** 2
        out[hw] = dict(n_states=int(np.ceil(n_needed)), multiple_of_current=round(n_needed / n_current, 1))
    return out


def phase_a(rows_by_decider) -> dict:
    pairs = [
        ("kev-4b", "kev-9b"), ("jev", "kev-9b"), ("jev", "llm:openrouter/openai/gpt-oss-20b"),
        ("cascade-kev-4b-t0.9", "kev-4b"), ("cascade-kev-4b-t0.9", "kev-9b"),
        ("cascade-kev-4b-t0.9", "jev"), ("cascade-kev-4b-t0.9", "llm:openrouter/openai/gpt-oss-20b"),
    ]
    out = {}
    for a, b in pairs:
        if a not in rows_by_decider or b not in rows_by_decider:
            continue
        key = f"{DISPLAY[a]} vs {DISPLAY[b]}"
        res = paired_diff_ci([r for r in rows_by_decider[a] if r["error"] is None],
                              [r for r in rows_by_decider[b] if r["error"] is None])
        res["needed"] = states_needed(res["std_diff"], res["n_states"])
        out[key] = res
    return out


# ---------------------------------------------------------------- Phase B ---

def phase_b(run: Path, rows_by_decider: dict, dmetas: dict, states: dict) -> dict:
    out = {}
    run_meta = json.loads((run / "meta.json").read_text())
    # This run only replays reward==1 episodes by default (include_failed=False in meta.json):
    # the "expected" universe is that filtered subset, not every state in the source file.
    if run_meta.get("include_failed"):
        all_state_ids = set(states)
    else:
        all_state_ids = {sid for sid, s in states.items() if s["episode_reward"] == 1.0}
    for d, rows in rows_by_decider.items():
        ok = [r for r in rows if r["error"] is None]
        errs = [r for r in rows if r["error"] is not None]
        by_state = Counter(r["state_id"] for r in ok)
        seen_states = set(by_state)
        counts_per_state = Counter(by_state.values())  # e.g. {5: 65} is the healthy case
        rec = dict(
            total_rows=len(rows),
            ok_rows=len(ok),
            error_rows=len(errs),
            distinct_states_seen=len(seen_states),
            expected_states=len(all_state_ids),
            missing_states=sorted(all_state_ids - seen_states),
            extra_states=sorted(seen_states - all_state_ids),
            calls_per_state_histogram=dict(counts_per_state),
            any_state_over_5_calls="warmup or duplicate leakage suspected" if any(
                v > 5 for v in by_state.values()) else "clean (no state exceeds 5 logged calls)",
        )
        dm = dmetas.get(d, {})
        if dm.get("kev_models"):
            models = dm["kev_models"].get("models", [])
            pc = models[0].get("prefix_cache") if models else None
            rec["prefix_cache"] = pc
            rec["cache_clean"] = (pc is not None and pc.get("hits", 0) == 0)
        out[d] = rec
    return out


# ---------------------------------------------------------------- Phase C ---

def modal(rows) -> tuple[str, bool]:
    choices = [r["choice"] for r in rows]
    c = Counter(choices).most_common(1)[0][0]
    ref = rows[0]["reference"]
    return c, c == ref


def phase_c(rows_by_decider: dict, states: dict) -> dict:
    wanted = ["jev", "llm:openrouter/openai/gpt-oss-20b", "kev-4b", "kev-9b"]
    per_state_modal = {}  # decider -> state_id -> (choice, correct)
    for d in wanted:
        if d not in rows_by_decider:
            continue
        by_state = defaultdict(list)
        for r in rows_by_decider[d]:
            if r["error"] is None:
                by_state[r["state_id"]].append(r)
        per_state_modal[d] = {sid: modal(rs) for sid, rs in by_state.items()}
    # Only deciders actually present in this run: a run with just kev-4b/kev-9b (e.g. airline
    # while jev/gpt-oss-20b are blocked on funding) must not crash on the ones missing.
    core = [d for d in wanted if d in per_state_modal]

    common_states = set.intersection(*(set(v) for v in per_state_modal.values())) if per_state_modal else set()

    def fail_count(sid):
        return sum(1 for d in core if not per_state_modal[d][sid][1])

    hardest = sorted(common_states, key=fail_count, reverse=True)
    hardest_rows = []
    for sid in hardest[:12]:
        row = {"state_id": sid, "task_id": states[sid]["task_id"], "reference": states[sid]["label"],
               "n_failing": fail_count(sid)}
        for d in core:
            row[DISPLAY[d]] = per_state_modal[d][sid][0]
        hardest_rows.append(row)

    def where(cond) -> list[dict]:
        out = []
        for sid in common_states:
            if cond(sid):
                out.append({"state_id": sid, "task_id": states[sid]["task_id"], "reference": states[sid]["label"],
                            **{DISPLAY[d]: per_state_modal[d][sid][0] for d in core}})
        return out

    def ok(d, sid):
        return per_state_modal[d][sid][1]

    def task_pattern(rows):
        return dict(Counter(r["task_id"] for r in rows).most_common())

    def summarize(rows):
        return dict(count=len(rows), by_task=task_pattern(rows), examples=rows[:6])

    NA = dict(count=None, by_task={}, examples=[], note="not available: required decider(s) missing from this run")

    have = set(core)
    kev4_wins = summarize(where(lambda sid: ok("kev-4b", sid) and not ok("kev-9b", sid))) \
        if {"kev-4b", "kev-9b"} <= have else NA
    kev9_wins = summarize(where(lambda sid: ok("kev-9b", sid) and not ok("kev-4b", sid))) \
        if {"kev-4b", "kev-9b"} <= have else NA
    jev_only = summarize(where(lambda sid: ok("jev", sid) and not ok("kev-4b", sid) and not ok("kev-9b", sid))) \
        if {"jev", "kev-4b", "kev-9b"} <= have else NA
    gptoss_only = summarize(where(
        lambda sid: ok("llm:openrouter/openai/gpt-oss-20b", sid) and not ok("jev", sid)
        and not ok("kev-4b", sid) and not ok("kev-9b", sid)
    )) if {"jev", "llm:openrouter/openai/gpt-oss-20b", "kev-4b", "kev-9b"} <= have else NA

    return dict(
        deciders_present=[DISPLAY[d] for d in core],
        n_common_states=len(common_states),
        hardest_states=hardest_rows,
        kev4_wins_kev9_loses=kev4_wins,
        kev9_wins_kev4_loses=kev9_wins,
        jev_beats_both_kev=jev_only,
        gptoss_beats_everyone=gptoss_only,
    )


# ---------------------------------------------------------------- Phase D ---

def logit(p, eps=1e-6):
    p = np.clip(np.asarray(p, dtype=float), eps, 1 - eps)
    return np.log(p / (1 - p))


def sigmoid(x):
    return 1 / (1 + np.exp(-np.asarray(x, dtype=float)))


def fit_temperature(conf, correct, T_grid):
    best_T, best_ece = 1.0, expected_calibration_error(conf, correct)
    for T in T_grid:
        scaled = sigmoid(logit(conf) / T)
        e = expected_calibration_error(scaled, correct)
        if e < best_ece:
            best_ece, best_T = e, T
    return best_T, best_ece


def two_fold_temperature(rows_with_conf, seed=0):
    states = sorted({r["state_id"] for r in rows_with_conf})
    rng = np.random.default_rng(seed)
    order = states.copy()
    rng.shuffle(order)
    half = len(order) // 2
    folds = [set(order[:half]), set(order[half:])]
    T_grid = np.concatenate([np.linspace(0.2, 1, 17), np.linspace(1.1, 6, 50)])
    fold_results = []
    for i in range(2):
        train_s, test_s = folds[i], folds[1 - i]
        train = [r for r in rows_with_conf if r["state_id"] in train_s]
        test = [r for r in rows_with_conf if r["state_id"] in test_s]
        T, _ = fit_temperature([r["confidence"] for r in train], [r["correct"] for r in train], T_grid)
        test_conf = [r["confidence"] for r in test]
        test_correct = [r["correct"] for r in test]
        ece_before = expected_calibration_error(test_conf, test_correct)
        scaled = sigmoid(logit(test_conf) / T).tolist()
        ece_after = expected_calibration_error(scaled, test_correct)
        fold_results.append(dict(T=float(T), ece_before=ece_before, ece_after=ece_after, n_test=len(test)))
    return fold_results


def cascade_sim(kev_rows, gpt_rows, thresholds):
    gpt_by_state = defaultdict(list)
    for r in gpt_rows:
        if r["error"] is None:
            gpt_by_state[r["state_id"]].append(r)
    kev_ok = [r for r in kev_rows if r["error"] is None and r["confidence"] is not None]
    n = len(kev_ok)
    avg_kev_latency_s = float(np.mean([r["latency_s"] for r in kev_ok]))
    out = []
    for t in thresholds:
        accepted = [r for r in kev_ok if r["confidence"] >= t]
        escalated = [r for r in kev_ok if r["confidence"] < t]
        correct_accept = sum(r["correct"] for r in accepted)
        correct_escalate, extra_lat_sum, cost_sum, matched = 0.0, 0.0, 0.0, 0
        for r in escalated:
            g = gpt_by_state.get(r["state_id"])
            if not g:
                continue
            matched += 1
            correct_escalate += float(np.mean([x["correct"] for x in g]))
            extra_lat_sum += float(np.mean([x["latency_s"] for x in g]))
            costs = [x["cost_usd"] for x in g if x["cost_usd"] is not None]
            cost_sum += float(np.mean(costs)) if costs else 0.0
        blended_accuracy = (correct_accept + correct_escalate) / n if n else float("nan")
        esc_rate = len(escalated) / n if n else float("nan")
        avg_extra_lat = (extra_lat_sum / matched) if matched else 0.0
        avg_cost = (cost_sum / matched * esc_rate) if matched else 0.0
        out.append(dict(
            threshold=t, accept_rate=len(accepted) / n if n else float("nan"), escalate_rate=esc_rate,
            unmatched_escalations=len(escalated) - matched,
            blended_accuracy=blended_accuracy,
            blended_latency_ms=(avg_kev_latency_s + esc_rate * avg_extra_lat) * 1000,
            blended_cost_usd_per_decision=avg_cost,
        ))
    return out


def phase_d(rows_by_decider: dict) -> dict:
    out = {}
    for d in ["jev", "llm:openrouter/openai/gpt-oss-20b", "kev-4b", "kev-9b", "kev-0.8b"]:
        if d not in rows_by_decider:
            continue
        rows = [r for r in rows_by_decider[d] if r["error"] is None and r["confidence"] is not None]
        if len(rows) < 20:
            continue
        folds = two_fold_temperature(rows)
        out[DISPLAY[d]] = dict(
            folds=folds,
            mean_ece_before=float(np.mean([f["ece_before"] for f in folds])),
            mean_ece_after=float(np.mean([f["ece_after"] for f in folds])),
        )
    cascade = None
    if "kev-4b" in rows_by_decider and "llm:openrouter/openai/gpt-oss-20b" in rows_by_decider:
        thresholds = [0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.01]
        cascade = cascade_sim(rows_by_decider["kev-4b"], rows_by_decider["llm:openrouter/openai/gpt-oss-20b"], thresholds)
    return dict(temperature_scaling=out, cascade_kev4b_to_gptoss=cascade)


# ---------------------------------------------------------------- Phase E ---

def phase_e(rows_by_decider: dict, dmetas: dict) -> dict:
    out = {}
    for d, rows in rows_by_decider.items():
        ok = [r for r in rows if r["error"] is None]
        acc = float(np.mean([r["correct"] for r in ok])) * 100
        lat_ms = float(np.median([r["latency_s"] for r in ok])) * 1000
        dm = dmetas.get(d, {})
        block = dm.get("energy_block")
        energy = (block["joules"] / block["calls"]) if block and block.get("calls") else None
        note = None
        if d.startswith("cascade") and energy is None:
            energy = CASCADE_REUSED_ENERGY_J
            note = "energy reused from Kev-4B's own standalone run (fast stage always runs); not re-metered live"
        cost_usd = [r["cost_usd"] for r in ok if r["cost_usd"] is not None]
        out[DISPLAY[d]] = dict(
            accuracy_pct=acc,
            median_latency_ms=lat_ms,
            accuracy_per_ms=acc / lat_ms,
            energy_j=energy,
            accuracy_per_joule=(acc / energy) if energy else None,
            mean_cost_usd=(float(np.mean(cost_usd)) if cost_usd else None),
            note=note,
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()

    rows_all = load_calls(args.run)
    dmetas = load_decider_metas(args.run)
    states = load_states(args.run)
    rows_by_decider = defaultdict(list)
    for r in rows_all:
        rows_by_decider[r["decider"]].append(r)

    report = dict(
        phase_a_significance=phase_a(rows_by_decider),
        phase_b_validation=phase_b(args.run, rows_by_decider, dmetas, states),
        phase_c_error_analysis=phase_c(rows_by_decider, states),
        phase_d_calibration=phase_d(rows_by_decider),
        phase_e_efficiency=phase_e(rows_by_decider, dmetas),
    )

    out_path = args.run / "post_experiment_analysis.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"==> wrote {out_path}")
    print(json.dumps(report, indent=2, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
