"""In-loop evaluation, arms A–E (PLAN.md U4): full tau2 episodes, same tasks, same user
simulator, same generator G; the arms differ only in who decides the next action.

    A  Jev decides                       + G executes   (DeciderTau2Agent)
    B  G decides (separate constrained call) + G executes
    C  G alone, one call per turn (tau2's LLMAgent) — the honest production baseline
    D  a small LLM decides               + G executes   (--small-model; local with --small-api-base)
    E  Kev decides (local)               + G executes   (--kev-url)

Every (arm, task, trial) is one row in <out>/episodes-<arm>.jsonl with the reward, tau2's
termination reason, and per-turn decision vs. execution latency/$/tokens (`steps`). Trial t
uses seed 2000+t for every arm, so arms face the same user-simulator seed. Re-running with
the same --out resumes: episodes that finished (or failed for a non-infra reason) are kept,
infra failures (402/429/5xx/network, `dwg.errors`) are retried.

$: tau2 prices G and the user simulator with litellm's own price map; decider $ is what
OpenRouter reports per call (as in arm 0). Energy isn't measured here: episodes run
concurrently on a shared GPU, so per-decision energy comes from arm 0 (replay_decisions.py).

Spending guard (dwg.billing): paid runs are estimated from earlier successful episodes of
the same arm in --out (or --est-cost-per-episode) and refused if they don't fit --max-usd or
the live OpenRouter balance; the first 402 stops new paid episodes.

Usage:
    python3 scripts/run_inloop.py --domain mock --arms A C E --trials 5 --dry-run
    python3 scripts/analyze_inloop.py results/inloop/mock
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.billing import check_budget  # noqa: E402
from dwg.errors import is_infra_error, is_out_of_credits  # noqa: E402
from dwg.runfiles import decider_slug  # noqa: E402
from dwg.tau2_llm import cap_max_tokens, rate_limit_tau2_llm_calls  # noqa: E402

DEFAULT_G = "openrouter/openai/gpt-oss-20b"
ARMS = ("A", "B", "C", "D", "E")
SEED_BASE = 2000


def llm_args(api_base: Optional[str], extra_body: Optional[str]) -> dict:
    """litellm kwargs for a model: a local OpenAI-compatible server and/or extra request fields."""
    out = {}
    if api_base:
        out.update(api_base=api_base, api_key="local")
    if extra_body:
        out["extra_body"] = json.loads(extra_body)
    return out


def is_paid_model(model: str, api_base: Optional[str]) -> bool:
    return api_base is None and model.startswith("openrouter/")


def arm_is_paid(arm: str, args) -> bool:
    if is_paid_model(args.g_model, args.g_api_base) or is_paid_model(args.user_model, args.user_api_base):
        return True
    return arm == "A" or (arm == "D" and is_paid_model(args.small_model, args.small_api_base))


def decider_is_paid(arm: str, args) -> bool:
    return {"A": True, "B": is_paid_model(args.g_model, args.g_api_base),
            "D": is_paid_model(args.small_model, args.small_api_base)}.get(arm, False)


def build_decider(arm: str, args):
    from dwg.decisions import JevChoiceDecider, LLMChoiceDecider, make_kev_decider

    if arm == "A":
        return JevChoiceDecider()
    if arm == "B":
        return LLMChoiceDecider(model=args.g_model, name=f"llm:{args.g_model}",
                                extra_body=json.loads(args.g_extra_body) if args.g_extra_body else None,
                                **({"api_base": args.g_api_base, "api_key": "local"} if args.g_api_base else {}))
    if arm == "D":
        return LLMChoiceDecider(model=args.small_model, name=f"llm:{args.small_model}",
                                extra_body=json.loads(args.small_extra_body) if args.small_extra_body else None,
                                **({"api_base": args.small_api_base, "api_key": "local"} if args.small_api_base else {}))
    if arm == "E":
        return make_kev_decider(base_url=args.kev_url, name=args.kev_name)
    raise ValueError(arm)


def run_episode(arm: str, decider, task, trial: int, args) -> dict:
    from tau2.data_model.message import UserMessage
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.runner import build_environment, build_user, run_simulation

    from dwg.decider_tau2_agent import DeciderTau2Agent, TimedLLMAgent

    env = build_environment(args.domain)
    g_args = llm_args(args.g_api_base, args.g_extra_body)
    if arm == "C":
        agent = TimedLLMAgent(tools=env.get_tools(), domain_policy=env.get_policy(), llm=args.g_model, llm_args=g_args)
    else:
        agent = DeciderTau2Agent(tools=env.get_tools(), domain_policy=env.get_policy(), decider=decider,
                                 filler_llm=args.g_model, filler_llm_args=g_args)
    user = build_user("user_simulator", env, task, llm=args.user_model,
                      llm_args=llm_args(args.user_api_base, args.user_extra_body))
    seed = SEED_BASE + trial
    orchestrator = Orchestrator(domain=args.domain, agent=agent, user=user, environment=env, task=task,
                                max_steps=args.max_steps, max_errors=5, seed=seed)
    t0 = time.perf_counter()
    result = run_simulation(orchestrator, evaluation_type=EvaluationType.ALL)
    steps = agent.steps

    def total(key):
        vals = [s.get(key) for s in steps if s.get(key) is not None]
        return float(sum(vals)) if vals else None

    user_costs = [m.cost for m in (result.messages or []) if isinstance(m, UserMessage) and m.cost is not None]
    return {
        "reward": result.reward_info.reward if result.reward_info else None,
        "termination_reason": str(getattr(result.termination_reason, "value", result.termination_reason)),
        "wall_s": time.perf_counter() - t0,
        "seed": seed,
        "n_turns": len(steps),
        "n_decider_failed": sum(1 for s in steps if s.get("decider_failed")),
        "decision_latency_s": total("decision_latency_s"),
        "exec_latency_s": total("exec_latency_s"),
        "decision_cost_usd": total("decision_cost_usd"),
        "exec_cost_usd": total("exec_cost_usd"),
        "user_cost_usd": float(sum(user_costs)) if user_costs else None,
        "decision_tokens": (total("decision_input_tokens") or 0) + (total("decision_output_tokens") or 0),
        "exec_tokens": (total("exec_input_tokens") or 0) + (total("exec_output_tokens") or 0),
        "steps": steps,
    }


def episode_cost(row: dict) -> Optional[float]:
    parts = [row.get(k) for k in ("decision_cost_usd", "exec_cost_usd", "user_cost_usd")]
    return float(sum(p for p in parts if p is not None)) if any(p is not None for p in parts) else None


def load_episodes(out: Path) -> list[dict]:
    rows = []
    for path in sorted(out.glob("episodes-*.jsonl")):
        with path.open() as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain", default="mock")
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    parser.add_argument("--task-ids", nargs="*", default=None)
    parser.add_argument("--num-tasks", type=int, default=None)
    parser.add_argument("--trials", type=int, default=5, help="episodes per (arm, task); PLAN.md rule: >=5")
    parser.add_argument("--g-model", default=DEFAULT_G, help="generator G: executes in every arm, decides in B and C")
    parser.add_argument("--g-api-base", default=None, help="local OpenAI-compatible server for G (vLLM)")
    parser.add_argument("--g-extra-body", default=None, help='JSON, e.g. \'{"chat_template_kwargs": {"enable_thinking": false}}\'')
    parser.add_argument("--user-model", default=None, help="user simulator (default: G)")
    parser.add_argument("--user-api-base", default=None)
    parser.add_argument("--user-extra-body", default=None)
    parser.add_argument("--small-model", default="openrouter/openai/gpt-oss-20b", help="arm D's decider")
    parser.add_argument("--small-api-base", default=None)
    parser.add_argument("--small-extra-body", default=None)
    parser.add_argument("--kev-url", default="http://127.0.0.1:8009")
    parser.add_argument("--kev-name", default="kev-4b")
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--warmup", type=int, default=3,
                        help="discarded decider calls before any episode: the first call to a local model pays "
                             "one-off CUDA/allocator setup (8.3 s vs 0.2 s for Kev-4B in the first local run)")
    parser.add_argument("--workers", type=int, default=4, help="concurrent episodes")
    parser.add_argument("--max-rpm", type=float, default=None, help="throttle tau2's own LLM calls (dwg.tau2_llm)")
    parser.add_argument("--max-tokens", type=int, default=2048, help="cap max_tokens on G/user calls (dwg.tau2_llm)")
    parser.add_argument("--max-usd", type=float, default=None)
    parser.add_argument("--est-cost-per-episode", type=float, default=None,
                        help="$ per episode for a paid arm with no earlier episodes in --out to estimate from")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    args.user_model = args.user_model or args.g_model
    if args.user_model == args.g_model and args.user_api_base is None:
        args.user_api_base, args.user_extra_body = args.g_api_base, args.user_extra_body or args.g_extra_body

    load_dotenv()
    from tau2.runner import get_tasks

    if args.max_rpm:
        rate_limit_tau2_llm_calls(args.max_rpm)
    if args.max_tokens:
        cap_max_tokens(args.max_tokens)

    tasks = get_tasks(args.domain, task_ids=args.task_ids, num_tasks=args.num_tasks)
    out = args.out or Path("results/inloop") / args.domain
    out.mkdir(parents=True, exist_ok=True)
    earlier = load_episodes(out)
    done = {(r["arm"], str(r["task_id"]), r["trial"]) for r in earlier
            if r.get("error") is None or not is_infra_error(r["error"])}
    jobs = [(arm, task, trial) for arm in args.arms for task in tasks for trial in range(args.trials)
            if (arm, str(task.id), trial) not in done]
    print(f"==> {len(tasks)} tasks x {args.trials} trials x arms {' '.join(args.arms)}: "
          f"{len(jobs)} episodes to run ({len(done)} already done)")

    # Spending guard, per arm, from that arm's own finished episodes.
    est_total = 0.0
    for arm in args.arms:
        n = sum(1 for j in jobs if j[0] == arm)
        if not n or not arm_is_paid(arm, args):
            continue
        costs = [c for r in earlier if r["arm"] == arm and r.get("error") is None
                 for c in [episode_cost(r)] if c is not None]
        per_ep = (sum(costs) / len(costs)) if len(costs) >= 5 else args.est_cost_per_episode
        if per_ep is None:
            raise SystemExit(f"!! no cost history for arm {arm} in {out}; pass --est-cost-per-episode "
                             f"(e.g. from a 1-task pilot with --task-ids)")
        print(f"==> $ estimate arm {arm}: {n} episodes x ${per_ep:.4f} = ${n * per_ep:.2f}")
        est_total += n * per_ep
    if est_total:
        print(f"==> $ estimate total: ${est_total:.2f}")
        check_budget(est_total, args.max_usd)
    if args.dry_run:
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    deciders = {arm: (None if arm == "C" else build_decider(arm, args)) for arm in args.arms}
    if args.warmup:
        from dwg.decisions import decision_options
        from tau2.runner import build_environment

        options = decision_options(build_environment(args.domain).get_tools())
        for arm, decider in deciders.items():
            if decider is None or decider_is_paid(arm, args):
                continue  # warm only free (local) deciders; a paid warmup call is wasted $
            for _ in range(args.warmup):
                try:
                    decider.decide("user: hello", options)
                except Exception as exc:
                    print(f"!! warmup call to {decider.name} failed: {exc!r}")
            print(f"==> {decider.name}: {args.warmup} warmup calls discarded")
    for arm in args.arms:
        meta_path = out / f"meta-{arm}.json"
        meta = {
            "arm": arm, "domain": args.domain, "decider": getattr(deciders[arm], "name", None),
            "g_model": args.g_model, "g_api_base": args.g_api_base, "g_extra_body": args.g_extra_body,
            "user_model": args.user_model, "user_api_base": args.user_api_base,
            "small_model": args.small_model if arm == "D" else None,
            "kev_url": args.kev_url if arm == "E" else None,
            "trials": args.trials, "max_steps": args.max_steps, "max_tokens": args.max_tokens,
            "workers": args.workers, "seed_base": SEED_BASE, "started": stamp, "host": platform.node(),
        }
        if meta_path.exists():
            prev = json.loads(meta_path.read_text())
            meta["previous_runs"] = prev.pop("previous_runs", []) + [prev]
        meta_path.write_text(json.dumps(meta, indent=2))

    stop_paid = threading.Event()
    lock = threading.Lock()
    handles = {arm: (out / f"episodes-{decider_slug(arm)}.jsonl").open("a") for arm in args.arms}

    def one(arm, task, trial) -> Optional[dict]:
        if stop_paid.is_set() and arm_is_paid(arm, args):
            return None
        row = {"arm": arm, "domain": args.domain, "task_id": str(task.id), "trial": trial,
               "decider": getattr(deciders[arm], "name", None), "g_model": args.g_model,
               "timestamp": time.time(), "error": None}
        try:
            row.update(run_episode(arm, deciders[arm], task, trial, args))
        except Exception as exc:
            row["error"] = repr(exc)[:500]
            if is_out_of_credits(row["error"]):
                stop_paid.set()
        return row

    n_done = n_err = n_skip = 0
    spent = 0.0
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(one, *j) for j in jobs]
            for future in as_completed(futures):
                row = future.result()
                if row is None:
                    n_skip += 1
                    continue
                n_done += 1
                n_err += row["error"] is not None
                spent += episode_cost(row) or 0.0
                if args.max_usd is not None and spent >= args.max_usd and not stop_paid.is_set():
                    print(f"!! --max-usd {args.max_usd:.2f} spent; stopping paid episodes")
                    stop_paid.set()
                with lock:
                    handles[row["arm"]].write(json.dumps(row) + "\n")
                    handles[row["arm"]].flush()
                print(f"   [{n_done}/{len(jobs)}] arm {row['arm']} {row['task_id']} t{row['trial']}: "
                      f"reward={row.get('reward')} turns={row.get('n_turns')} "
                      f"{'ERROR ' + row['error'][:80] if row['error'] else ''} (${spent:.3f} spent)")
    finally:
        for fh in handles.values():
            fh.close()
    if stop_paid.is_set():
        print(f"!! paid episodes stopped early; {n_skip} not attempted. Re-run the same command to resume.")
    print(f"==> {n_done} episodes ({n_err} errors) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
