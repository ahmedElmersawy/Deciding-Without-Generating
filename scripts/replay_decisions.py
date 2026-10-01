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

Spending guard (added 2026-09-25, after a run was launched without checking the balance and
ran the account dry mid-run): before any paid call, the $ cost of the run is estimated from
earlier successful calls of the same decider in --out (or --est-cost-per-call) and compared
with --max-usd and with the live OpenRouter balance; the run refuses to start if it doesn't
fit. While running, it stops submitting paid calls once --max-usd is spent, or on the first
402 (out of credits), instead of writing thousands of billing-error rows.

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
from typing import Optional

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
from dwg.billing import check_budget  # noqa: E402
from dwg.errors import is_infra_error, is_out_of_credits  # noqa: E402
from dwg.runfiles import calls_path, decider_meta_path, load_calls  # noqa: E402

DEFAULT_LLM = "openrouter/openai/gpt-oss-20b"
def is_paid(decider) -> bool:
    if hasattr(decider, "fast"):  # cascade: paid whenever either stage is
        return is_paid(decider.fast) or is_paid(decider.escalate)
    if isinstance(decider, LLMChoiceDecider):
        return decider.hosted
    return decider.name == "jev"


def cost_per_call(rows: list[dict], decider_name: str) -> Optional[float]:
    costs = [r["cost_usd"] for r in rows
             if r["decider"] == decider_name and r.get("error") is None and r.get("cost_usd") is not None]
    return sum(costs) / len(costs) if len(costs) >= 20 else None


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


def llm_decider(args, energy_meter) -> LLMChoiceDecider:
    completion_args = {}
    if args.llm_api_base:  # local OpenAI-compatible server (vLLM), e.g. Qwen3-8B on the A100
        completion_args["api_base"] = args.llm_api_base
        completion_args["api_key"] = "local"
    return LLMChoiceDecider(model=args.llm_model, name=args.llm_name, provider_sort=args.provider_sort,
                            extra_body=json.loads(args.llm_extra_body) if args.llm_extra_body else None,
                            energy_meter=energy_meter if args.llm_api_base else None,
                            **completion_args)


def build_deciders(names: list[str], args, energy_meter) -> list:
    deciders = []
    for name in names:
        if name == "jev":
            deciders.append(JevChoiceDecider())
        elif name == "llm":
            deciders.append(llm_decider(args, energy_meter))
        elif name == "kev":
            deciders.append(make_kev_decider(base_url=args.kev_url, name=args.kev_name, energy_meter=energy_meter))
        elif name == "cascade":
            # Jev is the project's fast stage; Kev is only a comparison next to it. No energy
            # meter on a Kev fast stage here: see CascadeDecider's docstring for why a live NVML
            # window around a call that may block on a network escalation would misattribute GPU
            # idle power as decision energy. Kev's own energy figure from a standalone replay is
            # reused post-hoc instead.
            if args.cascade_fast == "jev":
                fast, fast_name = JevChoiceDecider(), "jev"
            else:
                fast = make_kev_decider(base_url=args.kev_url, name=args.kev_name, energy_meter=None)
                fast_name = args.kev_name
            escalate = llm_decider(args, None)
            deciders.append(CascadeDecider(fast=fast, escalate=escalate, threshold=args.cascade_threshold,
                                            name=f"cascade-{fast_name}-t{args.cascade_threshold:g}"))
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
    parser.add_argument("--llm-name", default=None, help="label for the LLM decider (default llm:<model>)")
    parser.add_argument("--llm-api-base", default=None,
                        help="local OpenAI-compatible server for the LLM decider, e.g. http://127.0.0.1:8000/v1 "
                             "(vLLM); makes it a local decider with GPU energy, like Kev")
    parser.add_argument("--llm-extra-body", default=None,
                        help='JSON merged into the LLM request body, e.g. \'{"chat_template_kwargs": {"enable_thinking": false}}\'')
    parser.add_argument("--provider-sort", default=None, choices=["price", "throughput", "latency"],
                        help="OpenRouter upstream routing for hosted LLMs (default: OpenRouter's own). Keep it the "
                             "same for every run you compare: it changes latency as well as price")
    parser.add_argument("--max-usd", type=float, default=None,
                        help="refuse to start if the estimated $ exceeds this; stop paid calls once it is spent")
    parser.add_argument("--est-cost-per-call", type=float, default=None,
                        help="$ per call for a paid decider with no earlier calls in --out to estimate from")
    parser.add_argument("--dry-run", action="store_true", help="print the call count and $ estimate, then exit")
    parser.add_argument("--kev-url", default="http://127.0.0.1:8009", help="local Kev server (scripts/serve_kev.sh)")
    parser.add_argument("--kev-name", default="kev", help="label for this Kev run, e.g. kev-4b")
    parser.add_argument("--cascade-fast", default="jev", choices=["jev", "kev"],
                        help="cascade decider's fast stage (kev = the --kev-url server, for comparison only)")
    parser.add_argument("--cascade-threshold", type=float, default=0.9,
                         help="cascade decider: escalate to --llm-model when the fast stage's confidence is "
                              "below this. Pick it from an offline sweep over standalone runs, not a fixed value")
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
    # Done = any attempt that wasn't an infra error. Decider failures are final, not retried
    # (dwg.errors): re-running them would re-roll a stochastic decider's failures into successes.
    done = {
        (row["decider"], row["state_id"], row["repeat"]) for row in load_calls(out)
        if row.get("error") is None or not is_infra_error(row["error"])
    }

    energy_meter, idle_w, kev_info, llm_info, energy_unavailable = None, None, None, None, None
    local_llm = "llm" in args.deciders and args.llm_api_base
    if local_llm:
        llm_info = local_model_info(args.llm_api_base.rstrip("/").removesuffix("/v1"))
    if "kev" in args.deciders or local_llm:
        if "kev" in args.deciders:
            kev_info = local_model_info(args.kev_url)
        if args.no_energy:
            energy_unavailable = "disabled with --no-energy"
        else:
            energy_meter, energy_unavailable = try_energy_meter()
            if energy_meter:
                idle_w = energy_meter.idle_watts()
                print(f"==> GPU {energy_meter.device_name}: idle {idle_w:.1f} W")
    elif "cascade" in args.deciders and args.cascade_fast == "kev":
        # Provenance only: record which Kev checkpoint backs the fast stage. No energy meter
        # is created here on purpose (CascadeDecider's docstring explains why).
        kev_info = local_model_info(args.kev_url)
        energy_unavailable = ("not measured live for the cascade run: the fast stage's GPU energy is "
                               "reused post-hoc from that decider's own standalone replay, not re-metered here")
    elif "cascade" in args.deciders:
        energy_unavailable = "hosted: both cascade stages are API calls"
    deciders = build_deciders(args.deciders, args, energy_meter)

    # Run-level record: written once by whoever creates the run; only n_states is refreshed.
    run_meta_path = out / "meta.json"
    if run_meta_path.exists():
        # The one field that can go stale: states files grow when episodes are added later
        # (airline went 689 -> 1,076 states). Keep the old count in a history list. Only ever
        # grow it: a pilot on a few states (--states <subset>) is not the run shrinking.
        run_meta = json.loads(run_meta_path.read_text())
        if len(states) > (run_meta.get("n_states") or 0):
            run_meta.setdefault("n_states_history", []).append({"n_states": run_meta.get("n_states"), "until": stamp})
            run_meta["n_states"] = len(states)
            run_meta_path.write_text(json.dumps(run_meta, indent=2))
    else:
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
        local = (getattr(decider, "energy_meter", None) is not None or decider.name == args.kev_name
                 or (isinstance(decider, LLMChoiceDecider) and not decider.hosted))
        provenance = local or is_cascade  # cascade: record which Kev checkpoint, even with no energy meter
        # Server provenance: a Kev checkpoint for Kev and the cascade's fast stage; the vLLM
        # server's model list for a local LLM decider (never the other one's).
        uses_kev = decider.name == args.kev_name or (is_cascade and args.cascade_fast == "kev")
        meta = {
            "decider": decider.name,
            "model": args.llm_model if isinstance(decider, (LLMChoiceDecider, CascadeDecider)) else None,
            "cascade_fast": args.cascade_fast if is_cascade else None,
            "cascade_threshold": args.cascade_threshold if is_cascade else None,
            "provider_sort": args.provider_sort if is_paid(decider) else None,
            "llm_api_base": args.llm_api_base if isinstance(decider, LLMChoiceDecider) else None,
            "llm_extra_body": args.llm_extra_body if isinstance(decider, (LLMChoiceDecider, CascadeDecider)) else None,
            "repeats": args.repeats,
            "workers": args.workers,
            "started": stamp,
            "host": platform.node(),
            "kev_url": args.kev_url if (provenance and uses_kev) else None,
            "kev_models": kev_info if (provenance and uses_kev) else None,
            "llm_models": llm_info if (isinstance(decider, LLMChoiceDecider) and not decider.hosted) else None,
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
    # Spending guard: estimate $ from this decider's own earlier calls, check it against
    # --max-usd and the live balance BEFORE any paid call is made.
    earlier = load_calls(out)
    estimate = {}
    for decider in deciders:
        n = sum(1 for job in jobs if job[0] is decider)
        if not n or not is_paid(decider):
            continue
        per_call = cost_per_call(earlier, decider.name) or args.est_cost_per_call
        if per_call is None:
            raise SystemExit(f"!! no cost history for {decider.name} in {out} to estimate $ from; "
                             f"pass --est-cost-per-call (e.g. from a small pilot)")
        estimate[decider.name] = (n, per_call, n * per_call)
    est_total = sum(e[2] for e in estimate.values())
    for name, (n, per_call, total) in estimate.items():
        print(f"==> $ estimate {name}: {n} calls x ${per_call:.2e} = ${total:.2f}")
    if estimate:
        print(f"==> $ estimate total: ${est_total:.2f}")
        check_budget(est_total, args.max_usd)
    if args.dry_run:
        return 0

    print(f"==> {len(states)} states x {len(deciders)} deciders x {args.repeats} repeats; {len(jobs)} calls to make")

    rendered = {s["state_id"]: render_transcript(rebuild_messages(s)) for s in states}
    lock = threading.Lock()
    # Energy is whole-GPU: calls to a metered decider must not overlap each other. Hosted
    # deciders still run concurrently alongside, since they don't touch the local GPU.
    gpu_lock = threading.Lock()
    stop_paid = threading.Event()  # set on the first 402 or once --max-usd is spent

    def one_call(decider, state, rep) -> Optional[dict]:
        if stop_paid.is_set() and is_paid(decider):
            return None  # not attempted: left for a resumed run
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
            if is_out_of_credits(row["error"]):
                stop_paid.set()
        return row

    # Local deciders: discard warmup calls (the first CUDA call pays one-off kernel/allocator
    # setup — 0.65 s vs 0.11 s steady-state for Kev-0.8B on the pilot laptop).
    for decider in deciders:
        warm_target = decider.fast if hasattr(decider, "fast") else decider  # cascade: warm only Kev, no $ cost
        is_local = decider.name == args.kev_name or (isinstance(decider, LLMChoiceDecider) and not decider.hosted)
        if (is_local or hasattr(decider, "fast")) and args.warmup:
            s0 = states[0]
            for _ in range(args.warmup):
                warm_target.decide(rendered[s0["state_id"]], options_by_domain[s0["domain"]])
            print(f"==> {decider.name}: {args.warmup} warmup calls discarded")

    # Only deciders with work to do get a new run record; a no-op resume leaves files untouched.
    # Written after warmup, so a server that rejects every request leaves no stray record.
    for decider in deciders:
        if any(job[0] is decider for job in jobs):
            write_decider_meta(decider)

    # Block energy: counter delta over the whole run / metered calls. Only meaningful when the
    # metered decider runs alone and back to back (no gaps while hosted calls are in flight).
    # With two metered deciders in one run, a single whole-GPU delta can't be split between them,
    # so block energy needs exactly one (per-call energy is still recorded either way).
    metered_only = (energy_meter is not None and len(deciders) == 1
                    and getattr(deciders[0], "energy_meter", None) is not None)
    block_e0, block_t0 = (energy_meter.read_mj(), time.perf_counter()) if metered_only else (None, None)

    n_err, n_skipped, spent = 0, 0, 0.0
    handles = {d.name: calls_path(out, d.name).open("a") for d in deciders}
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(one_call, *job) for job in jobs]
            for i, future in enumerate(as_completed(futures), 1):
                row = future.result()
                if row is None:
                    n_skipped += 1
                    continue
                n_err += row["error"] is not None
                spent += row.get("cost_usd") or 0.0
                if args.max_usd is not None and spent >= args.max_usd and not stop_paid.is_set():
                    print(f"!! --max-usd {args.max_usd:.2f} spent; stopping paid calls")
                    stop_paid.set()
                with lock:
                    handles[row["decider"]].write(json.dumps(row) + "\n")
                    handles[row["decider"]].flush()
                if i % 25 == 0 or i == len(futures):
                    print(f"   {i}/{len(futures)} calls ({n_err} errors, ${spent:.3f} spent)")
    finally:
        for fh in handles.values():
            fh.close()

    if stop_paid.is_set():
        print(f"!! paid calls stopped early (out of credits or --max-usd); {n_skipped} calls not attempted. "
              f"Re-run the same command to resume.")
    if metered_only:
        n_metered = len(futures) - n_err - n_skipped
        block = {
            "decider": deciders[0].name,  # the one metered decider (Kev or a local LLM)
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
