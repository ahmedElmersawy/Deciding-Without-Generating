"""Collect agent-control decision states from real tau2-bench episodes (arm 0, step 1).

Runs tau2's built-in `LLMAgent` (the reference agent) on every task of a domain, N trials
each, and records at every agent turn exactly what the agent saw (system prompt + history)
and which action it took (a tool name, or respond_to_user). Each state is tagged with the
episode's final reward, so replay can restrict labels to trajectories that passed tau2's
grader.

Label semantics (DECISIONS.md 2026-09-23): the reference action at a state from a reward=1
episode is ONE acceptable next action, not the only one — tau2 grades final outcomes, and
another path could also succeed. "Accuracy" in replay is therefore agreement with a
successful reference trajectory, a conservative lower bound.

Usage (from repo root, venv active):
    python3 scripts/collect_decision_states.py --domain mock --trials 3
    -> results/states/<domain>-<model-slug>-<timestamp>.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.decisions import action_label  # noqa: E402

DEFAULT_MODEL = "openrouter/openai/gpt-oss-20b"


def rate_limit_tau2_llm_calls(max_calls_per_minute: float) -> None:
    """Throttle every LLM call tau2 makes (agent + user simulator both go through
    tau2.utils.llm_utils.generate -> the `completion` name bound there) to at most
    `max_calls_per_minute`, spaced evenly.

    Needed because tau2's own retry (DEFAULT_MAX_RETRIES=3) assumes transient errors,
    not a hard per-minute account quota: found live 2026-09-23 collecting airline states
    with a fresh OpenRouter account — every one of 15 episodes was rate-limited to death
    (litellm.RateLimitError, "new accounts are limited to 20 requests per minute") because
    3 retries can't outlast a 60s window that 4 concurrent workers were all hammering at
    once. Must patch the NAME `tau2.utils.llm_utils.completion`, not `litellm.completion`:
    that module did `from litellm import completion`, which copies the reference at import
    time, so reassigning litellm.completion afterward would not affect it.
    """
    import threading
    import time as time_module

    import tau2.utils.llm_utils as llm_utils

    original = llm_utils.completion
    min_interval = 60.0 / max_calls_per_minute
    lock = threading.Lock()
    last_call = [0.0]

    def throttled(*args, **kwargs):
        with lock:
            wait = min_interval - (time_module.monotonic() - last_call[0])
            if wait > 0:
                time_module.sleep(wait)
            last_call[0] = time_module.monotonic()
        return original(*args, **kwargs)

    llm_utils.completion = throttled


def cap_max_tokens(max_tokens: int) -> None:
    """Cap every tau2 LLM call's max_tokens (default: uncapped -> the model's own ceiling,
    e.g. 65536 for gpt-5.6).

    Found live 2026-09-23 collecting airline states: OpenRouter pre-authorizes credits
    against the WORST CASE max_tokens on every call, before any tokens are generated or
    billed -- "you requested up to 65536 tokens, but can only afford 32405" (HTTP 402). A
    single conversational turn or tool call realistically needs a few hundred tokens, not
    65536; leaving it uncapped means the account's remaining balance gates far below what
    it can actually afford in real usage. Same monkeypatch target as
    rate_limit_tau2_llm_calls, for the same reason (the bound name, not the module).
    """
    import tau2.utils.llm_utils as llm_utils

    original = llm_utils.completion

    def capped(*args, **kwargs):
        kwargs.setdefault("max_tokens", max_tokens)
        return original(*args, **kwargs)

    llm_utils.completion = capped


def make_recording_agent_class():
    from tau2.agent.llm_agent import LLMAgent

    class RecordingLLMAgent(LLMAgent):
        """LLMAgent that records (history it saw, action it took) at every turn."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.records: list[dict] = []

        def generate_next_message(self, message, state):
            assistant_message, new_state = super().generate_next_message(message, state)
            history = new_state.messages[:-1]  # everything before the message just generated
            self.records.append(
                {
                    "system_prompt": new_state.system_messages[0].content,
                    "history": [m.model_dump(mode="json", exclude={"raw_data"}) for m in history],
                    "label": action_label(assistant_message),
                    "n_tool_calls": len(assistant_message.tool_calls or []),
                }
            )
            return assistant_message, new_state

    return RecordingLLMAgent


def run_episode(domain: str, task, trial: int, model: str, seed: int) -> list[dict]:
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.runner import build_environment, build_user, run_simulation

    env = build_environment(domain)
    agent = make_recording_agent_class()(tools=env.get_tools(), domain_policy=env.get_policy(), llm=model)
    user = build_user("user_simulator", env, task, llm=model)
    orchestrator = Orchestrator(
        domain=domain, agent=agent, user=user, environment=env, task=task, max_steps=40, max_errors=5, seed=seed
    )
    result = run_simulation(orchestrator, evaluation_type=EvaluationType.ALL)
    reward = result.reward_info.reward if result.reward_info else None
    return [
        {
            "state_id": f"{task.id}/t{trial}/turn{turn}",
            "domain": domain,
            "task_id": task.id,
            "trial": trial,
            "turn": turn,
            "episode_reward": reward,
            "reference_model": model,
            **record,
        }
        for turn, record in enumerate(agent.records)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain", default="mock")
    parser.add_argument("--trials", type=int, default=3, help="episodes per task")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="reference agent + user simulator model")
    parser.add_argument("--task-ids", nargs="*", default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-rpm", type=float, default=None,
                         help="throttle tau2's own LLM calls (agent+user) to at most this many per minute "
                              "(set below the provider's account-level rate limit, e.g. an OpenRouter "
                              "'new account' cap; see rate_limit_tau2_llm_calls)")
    parser.add_argument("--max-tokens", type=int, default=None,
                         help="cap max_tokens on every tau2 LLM call (default: model's own ceiling, e.g. "
                              "65536 for gpt-5.6 -- OpenRouter pre-authorizes credits against that worst "
                              "case, not real usage; see cap_max_tokens)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    load_dotenv()
    from tau2.runner import get_tasks

    if args.max_rpm:
        rate_limit_tau2_llm_calls(args.max_rpm)
    if args.max_tokens:
        cap_max_tokens(args.max_tokens)

    tasks = get_tasks(args.domain, task_ids=args.task_ids)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = args.model.replace("/", "_")
    out = args.out or Path("results/states") / f"{args.domain}-{slug}-{stamp}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    lock = threading.Lock()
    jobs = [(task, trial) for task in tasks for trial in range(args.trials)]
    n_states = 0
    with out.open("w") as fh, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_episode, args.domain, task, trial, args.model, seed=1000 + trial): (task.id, trial)
            for task, trial in jobs
        }
        for future in as_completed(futures):
            task_id, trial = futures[future]
            try:
                rows = future.result()
            except Exception as exc:  # one broken episode must not kill the whole collection
                print(f"!! {task_id} trial {trial} failed: {exc!r}", file=sys.stderr)
                continue
            with lock:
                for row in rows:
                    fh.write(json.dumps(row) + "\n")
                fh.flush()
                n_states += len(rows)
            reward = rows[0]["episode_reward"] if rows else None
            print(f"   {task_id} trial {trial}: reward={reward} states={len(rows)}")

    print(f"==> {n_states} states from {len(jobs)} episodes -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
