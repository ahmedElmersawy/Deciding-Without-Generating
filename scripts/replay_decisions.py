"""Decision-only replay (arm 0, step 2): ask every decider the same decision, R times per state.

Loads states from scripts/collect_decision_states.py, keeps those from reward=1 episodes by
default (so the reference action is a known-good one), and asks each decider "respond or
which tool?" on the identical rendered state. Nothing is executed — this measures the cost,
latency, accuracy, consistency, and calibration of DECIDING only.

Every call is one row in <out>/calls.jsonl (errors included, so error rate is reportable).
Re-running with the same --out resumes: (decider, state, repeat) rows already present are
skipped.

Usage:
    python3 scripts/replay_decisions.py --states results/states/mock-*.jsonl --repeats 5
    python3 scripts/analyze_decisions.py results/replay/<run>
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.decisions import JevChoiceDecider, LLMChoiceDecider, decision_options, render_transcript  # noqa: E402

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


def build_deciders(names: list[str], llm_model: str) -> list:
    deciders = []
    for name in names:
        if name == "jev":
            deciders.append(JevChoiceDecider())
        elif name == "llm":
            deciders.append(LLMChoiceDecider(model=llm_model))
        else:
            raise SystemExit(f"unknown decider {name!r} (known: jev, llm)")
    return deciders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--states", type=Path, nargs="+", required=True)
    parser.add_argument("--deciders", nargs="+", default=["jev", "llm"])
    parser.add_argument("--llm-model", default=DEFAULT_LLM)
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
    calls_path = out / "calls.jsonl"
    done = set()
    if calls_path.exists():
        with calls_path.open() as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("error") is None:
                    done.add((row["decider"], row["state_id"], row["repeat"]))

    deciders = build_deciders(args.deciders, args.llm_model)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "states": [str(p) for p in args.states],
                "n_states": len(states),
                "deciders": [d.name for d in deciders],
                "llm_model": args.llm_model,
                "repeats": args.repeats,
                "workers": args.workers,
                "include_failed": args.include_failed,
                "started": stamp,
            },
            indent=2,
        )
    )

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
    print(f"==> {len(states)} states x {len(deciders)} deciders x {args.repeats} repeats; {len(jobs)} calls to make")

    rendered = {s["state_id"]: render_transcript(rebuild_messages(s)) for s in states}
    lock = threading.Lock()

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
            decision = decider.decide(rendered[state["state_id"]], options_by_domain[state["domain"]])
            row.update(decision.to_dict())
            row["correct"] = decision.choice == state["label"]
        except Exception as exc:
            row["error"] = repr(exc)[:500]
        return row

    n_err = 0
    with calls_path.open("a") as fh, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one_call, *job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            row = future.result()
            n_err += row["error"] is not None
            with lock:
                fh.write(json.dumps(row) + "\n")
                fh.flush()
            if i % 25 == 0 or i == len(futures):
                print(f"   {i}/{len(futures)} calls ({n_err} errors)")

    print(f"==> wrote {calls_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
