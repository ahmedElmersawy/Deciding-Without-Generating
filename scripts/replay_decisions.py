"""Decision-only replay (arm 0, step 2): ask every decider the same decision, R times per state.

Loads states from scripts/collect_decision_states.py, keeps those from reward=1 episodes by
default (so the reference action is a known-good one), and asks each decider "respond or
which tool?" on the identical rendered state. Nothing is executed — this measures the cost,
latency, accuracy, consistency, and calibration of DECIDING only.

Every call is one row in <out>/calls-<decider>.jsonl (errors included, so error rate is
reportable); each decider also gets <out>/meta-<decider>.json. Per-decider files mean the laptop
and Gilbreth can add different deciders to the same run without git conflicts (PLAN.md U0).
Re-running with the same --out resumes: (decider, state, repeat) rows already present are
skipped.

Usage:
    python3 scripts/replay_decisions.py --states results/states/mock-*.jsonl --repeats 5
    python3 scripts/analyze_decisions.py results/replay/<run>
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.decisions import (  # noqa: E402
    CascadeDecider,
    JevChoiceDecider,
    LLMChoiceDecider,
    decision_options,
    make_kev_decider,
    render_transcript,
)
from dwg.energy import try_energy_meter  # noqa: E402
from dwg.runfiles import calls_path, decider_meta_path, load_calls  # noqa: E402

DEFAULT_LLM = "openrouter/openai/gpt-oss-20b"


def load_states(paths: list[Path], include_failed: bool) -> list[dict]:
    states = []
    for path in paths:
        with path.open() as fh:
            states.extend(json.loads(line) for line in fh if line.strip())
    if not include_failed:
        states = [s for s in states if s["episode_reward"] == 1.0]
    return states


def rebuild_messages(state: dict):
    from tau2.data_model.message import AssistantMessage, SystemMessage, ToolMessage, UserMessage

    by_role = {"assistant": AssistantMessage, "user": UserMessage, "tool": ToolMessage}
    messages = [SystemMessage(role="system", content=state["system_prompt"])]
    messages += [by_role[m["role"]].model_validate(m) for m in state["history"]]
    return messages


def build_deciders(names: list[str], args, energy_meter) -> list:
    deciders = []
    for name in names:
        if name == "jev":
            deciders.append(JevChoiceDecider())
        elif name == "llm":
            deciders.append(LLMChoiceDecider(model=args.llm_model))
        elif name == "kev":
            deciders.append(make_kev_decider(base_url=args.kev_url, name=args.kev_name, energy_meter=energy_meter))
        elif name == "cascade":
            # No energy meter on the fast stage here: see CascadeDecider's docstring for why
            # a live NVML window around a call that may block on a network escalation would
            # misattribute GPU idle power as decision energy. Kev's own energy figure from a
            # standalone replay is reused post-hoc instead.
            fast = make_kev_decider(base_url=args.kev_url, name=args.kev_name, energy_meter=None)
            escalate = LLMChoiceDecider(model=args.llm_model)
            deciders.append(CascadeDecider(fast=fast, escalate=escalate, threshold=args.cascade_threshold,
                                            name=f"cascade-{args.kev_name}-t{args.cascade_threshold:g}"))
        else:
            raise SystemExit(f"unknown decider {name!r} (known: jev, llm, kev, cascade)")
    return deciders


def local_model_info(base_url: str) -> dict:
    """What the local System One server says it has loaded (GET /v1/models), for the run record."""
    import requests

    try:
        return requests.get(f"{base_url.rstrip('/')}/v1/models", timeout=10).json()
    except Exception as exc:
        raise SystemExit(f"local decider server at {base_url} is not reachable: {exc!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--states", type=Path, nargs="+", required=True)
    parser.add_argument("--deciders", nargs="+", default=["jev", "llm"])
    parser.add_argument("--llm-model", default=DEFAULT_LLM)
    parser.add_argument("--kev-url", default="http://127.0.0.1:8009", help="local Kev server (scripts/serve_kev.sh)")
    parser.add_argument("--kev-name", default="kev", help="label for this Kev run, e.g. kev-4b")
    parser.add_argument("--cascade-threshold", type=float, default=0.9,
                         help="cascade decider: escalate to --llm-model when Kev's confidence is below this")
    parser.add_argument("--no-energy", action="store_true", help="skip GPU energy for local deciders")
    parser.add_argument("--warmup", type=int, default=5, help="discarded warmup calls per local decider")
    parser.add_argument("--repeats", type=int, default=5, help="calls per (decider, state)")
    parser.add_argument("--workers", type=int, default=4, help="concurrent calls (same for every decider)")
    parser.add_argument("--include-failed", action="store_true", help="also replay states from reward<1 episodes")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    load_dotenv()
    from tau2.runner import build_environment

    states = load_states(args.states, args.include_failed)
    if not states:
        raise SystemExit("no states to replay (all episodes failed? try --include-failed)")
    domains = {s["domain"] for s in states}
    options_by_domain = {d: decision_options(build_environment(d).get_tools()) for d in domains}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or Path("results/replay") / f"{'-'.join(sorted(domains))}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    done = {
        (row["decider"], row["state_id"], row["repeat"]) for row in load_calls(out) if row.get("error") is None
    }

    energy_meter, idle_w, kev_info, energy_unavailable = None, None, None, None
    if "kev" in args.deciders:
        kev_info = local_model_info(args.kev_url)
        if args.no_energy:
            energy_unavailable = "disabled with --no-energy"
        else:
            energy_meter, energy_unavailable = try_energy_meter()
            if energy_meter:
                idle_w = energy_meter.idle_watts()
                print(f"==> GPU {energy_meter.device_name}: idle {idle_w:.1f} W")
    elif "cascade" in args.deciders:
        # Provenance only: record which Kev checkpoint backs the fast stage. No energy meter
        # is created here on purpose (CascadeDecider's docstring explains why).
        kev_info = local_model_info(args.kev_url)
        energy_unavailable = ("not measured live for the cascade run: the fast stage's GPU energy is "
                               "reused post-hoc from that decider's own standalone replay, not re-metered here")
    deciders = build_deciders(args.deciders, args, energy_meter)

    # Run-level record: written once by whoever creates the run, never rewritten.
    run_meta_path = out / "meta.json"
    if not run_meta_path.exists():
        run_meta_path.write_text(json.dumps(
            {
                "states": [str(p) for p in args.states],
                "n_states": len(states),
                "include_failed": args.include_failed,
                "created": stamp,
            },
            indent=2,
        ))

    def write_decider_meta(decider, energy_block=None) -> None:
        is_cascade = hasattr(decider, "fast")
        local = getattr(decider, "energy_meter", None) is not None or decider.name == args.kev_name
        provenance = local or is_cascade  # cascade: record which Kev checkpoint, even with no energy meter
        meta = {
            "decider": decider.name,
            "model": args.llm_model if isinstance(decider, (LLMChoiceDecider, CascadeDecider)) else None,
            "cascade_threshold": args.cascade_threshold if is_cascade else None,
            "repeats": args.repeats,
            "workers": args.workers,
            "started": stamp,
            "host": platform.node(),
            "kev_url": args.kev_url if provenance else None,
            "kev_models": kev_info if provenance else None,
            "gpu": energy_meter.device_name if (local and energy_meter) else None,
            "gpu_idle_watts": idle_w if local else None,
            "energy_unavailable": energy_unavailable if provenance else None,
            "energy_block": energy_block,
        }
        # Resuming or extending a decider keeps its earlier records instead of overwriting them.
        path = decider_meta_path(out, decider.name)
        if path.exists():
            previous = json.loads(path.read_text())
            history = previous.pop("previous_runs", [])
            if previous.get("started") != stamp:  # not just this run updating its own energy block
                history.append(previous)
            if history:
                meta["previous_runs"] = history
        path.write_text(json.dumps(meta, indent=2))

    jobs = [
        (decider, state, rep)
        for state in states
        for decider in deciders
        for rep in range(args.repeats)
        if (decider.name, state["state_id"], rep) not in done
    ]
    # Interleave deciders/states so transient network or rate-limit conditions hit every
    # decider equally instead of landing on whichever ran during a bad minute.
    random.Random(0).shuffle(jobs)
    # Only deciders with work to do get a new run record; a no-op resume leaves files untouched.
    for decider in deciders:
        if any(job[0] is decider for job in jobs):
            write_decider_meta(decider)
    print(f"==> {len(states)} states x {len(deciders)} deciders x {args.repeats} repeats; {len(jobs)} calls to make")

    rendered = {s["state_id"]: render_transcript(rebuild_messages(s)) for s in states}
    lock = threading.Lock()
    # Energy is whole-GPU: calls to a metered decider must not overlap each other. Hosted
    # deciders still run concurrently alongside, since they don't touch the local GPU.
    gpu_lock = threading.Lock()

    def one_call(decider, state, rep) -> dict:
        row = {
            "decider": decider.name,
            "state_id": state["state_id"],
            "task_id": state["task_id"],
            "domain": state["domain"],
            "repeat": rep,
            "reference": state["label"],
            "timestamp": time.time(),
            "error": None,
        }
        try:
            if getattr(decider, "energy_meter", None) is not None:
                with gpu_lock:
                    decision = decider.decide(rendered[state["state_id"]], options_by_domain[state["domain"]])
            else:
                decision = decider.decide(rendered[state["state_id"]], options_by_domain[state["domain"]])
            row.update(decision.to_dict())
            row["correct"] = decision.choice == state["label"]
        except Exception as exc:
            row["error"] = repr(exc)[:500]
        return row

    # Local deciders: discard warmup calls (the first CUDA call pays one-off kernel/allocator
    # setup — 0.65 s vs 0.11 s steady-state for Kev-0.8B on the pilot laptop).
    for decider in deciders:
        warm_target = decider.fast if hasattr(decider, "fast") else decider  # cascade: warm only Kev, no $ cost
        if (decider.name == args.kev_name or hasattr(decider, "fast")) and args.warmup:
            s0 = states[0]
            for _ in range(args.warmup):
                warm_target.decide(rendered[s0["state_id"]], options_by_domain[s0["domain"]])
            print(f"==> {decider.name}: {args.warmup} warmup calls discarded")

    # Block energy: counter delta over the whole run / metered calls. Only meaningful when the
    # metered decider runs alone and back to back (no gaps while hosted calls are in flight).
    metered_only = energy_meter is not None and all(getattr(d, "energy_meter", None) for d in deciders)
    block_e0, block_t0 = (energy_meter.read_mj(), time.perf_counter()) if metered_only else (None, None)

    n_err = 0
    handles = {d.name: calls_path(out, d.name).open("a") for d in deciders}
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(one_call, *job) for job in jobs]
            for i, future in enumerate(as_completed(futures), 1):
                row = future.result()
                n_err += row["error"] is not None
                with lock:
                    handles[row["decider"]].write(json.dumps(row) + "\n")
                    handles[row["decider"]].flush()
                if i % 25 == 0 or i == len(futures):
                    print(f"   {i}/{len(futures)} calls ({n_err} errors)")
    finally:
        for fh in handles.values():
            fh.close()

    if metered_only:
        n_metered = len(futures) - n_err
        block = {
            "decider": args.kev_name,
            "joules": (energy_meter.read_mj() - block_e0) / 1000.0,
            "seconds": time.perf_counter() - block_t0,
            "calls": n_metered,
        }
        for decider in deciders:
            write_decider_meta(decider, energy_block=block)
        print(f"==> block energy {block['joules']:.1f} J over {block['calls']} calls in {block['seconds']:.1f}s")

    print(f"==> wrote {', '.join(calls_path(out, d.name).name for d in deciders)} in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
