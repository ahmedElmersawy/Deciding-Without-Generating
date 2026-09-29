"""Layout of a replay run directory, shared by replay and analysis (PLAN.md U0).

    <run>/meta.json               run-level, written once: which states, how filtered
    <run>/calls-<decider>.jsonl   one row per call, for ONE decider
    <run>/meta-<decider>.json     that decider's run record: model, repeats, GPU, energy block

Each decider owns its own files, so machines adding different deciders to the same run (the
laptop adding API deciders, Gilbreth adding Kev) never edit the same file and never conflict
in git.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from dwg.errors import is_infra_error


def decider_slug(decider: str) -> str:
    """`llm:openrouter/openai/gpt-oss-20b` -> `llm_openrouter_openai_gpt-oss-20b`."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", decider)


def calls_path(run: Path, decider: str) -> Path:
    return run / f"calls-{decider_slug(decider)}.jsonl"


def decider_meta_path(run: Path, decider: str) -> Path:
    return run / f"meta-{decider_slug(decider)}.json"


def load_calls(run: Path) -> list[dict]:
    rows = []
    for path in sorted(run.glob("calls-*.jsonl")):
        with path.open() as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    for r in rows:
        # A cascade call that didn't escalate ran only its local fast stage: it cost $0, not
        # "unknown". Rows written before CascadeDecider recorded that have cost None, which
        # dropped them from $/decision means and overstated the cascade's cost ~2.5x (mock).
        if r.get("escalated") is False and r.get("cost_usd") is None and r.get("error") is None \
                and str(r.get("decider", "")).startswith("cascade"):
            r["cost_usd"] = 0.0
    return rows


def load_decider_metas(run: Path) -> dict[str, dict]:
    """decider name -> its meta record."""
    metas = {}
    for path in sorted(run.glob("meta-*.json")):
        meta = json.loads(path.read_text())
        metas[meta["decider"]] = meta
    return metas


def pooled_energy(dmeta: dict) -> dict | None:
    """Whole-GPU block energy for one decider, pooled over every run that metered it.

    A resumed decider has one `energy_block` per run (the current one plus `previous_runs`),
    each covering only the calls that run made. Reading just the latest block reports the
    J/decision of whatever subset the last resume covered, so all blocks are summed; net
    energy subtracts each run's own idle baseline. Returns None if no run has a block.
    """
    runs = [dmeta] + list(dmeta.get("previous_runs", []))
    blocks = [(r["energy_block"], r.get("gpu_idle_watts")) for r in runs
              if r.get("energy_block") and r["energy_block"].get("calls")]
    if not blocks:
        return None
    calls = sum(b["calls"] for b, _ in blocks)
    joules = sum(b["joules"] for b, _ in blocks)
    net = None
    if all(w is not None for _, w in blocks):
        net = sum(b["joules"] - w * b["seconds"] for b, w in blocks) / calls
    return {"gross_j": joules / calls, "net_j": net, "calls": calls, "runs": len(blocks)}


def resolve_attempts(rows: list[dict]) -> tuple[list[dict], dict[str, Counter]]:
    """One outcome per (decider, state, repeat).

    A resumed run appends new attempts after infra-failed ones, so the raw file can hold several
    rows for one (decider, state, repeat). The outcome is the first attempt that was not an infra
    error (a success or a decider failure: decider failures are final, see dwg.errors), else the
    last attempt. Older files also hold retries of decider failures, made before replay stopped
    retrying them; taking the first real attempt ignores those re-rolls. Also counts, per
    decider, raw attempts and infra errors vs. decider failures.
    """
    groups = defaultdict(list)
    for r in rows:
        groups[(r["decider"], r["state_id"], str(r["repeat"]))].append(r)
    resolved, stats = [], defaultdict(Counter)
    for (decider, _, _), rs in groups.items():
        stats[decider]["attempts"] += len(rs)
        stats[decider]["infra_errors"] += sum(1 for r in rs if r["error"] and is_infra_error(r["error"]))
        # Calls files are append-only, so file order is attempt order.
        real = [r for r in rs if r["error"] is None or not is_infra_error(r["error"])]
        outcome = real[0] if real else rs[-1]
        if outcome["error"] is not None:
            stats[decider]["unresolved_infra" if is_infra_error(outcome["error"]) else "decider_failures"] += 1
        resolved.append(outcome)
    return resolved, stats


def load_outcomes(run: Path) -> list[dict]:
    """One row per (decider, state, repeat): what every analysis should count (see resolve_attempts)."""
    return resolve_attempts(load_calls(run))[0]
