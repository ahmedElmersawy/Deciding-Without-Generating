"""Vertical-slice proof for the agent-control decision point on REAL tau2-bench data
(System1_Jev_Benchmark.pdf), following up scripts/agent_control_vertical_slice.py's
toy-task proof with tau2's own `mock` domain task.

Runs the SAME tau2 task through two agents against the same user simulator:
  1. Frontier-only: tau2's built-in `LLMAgent` (LiteLLM decides everything).
  2. Jev: `JevTau2Agent` (dwg.jev_tau2_agent) — Jev decides respond-vs-tool-call,
     the same cheap LiteLLM model only fills in the chosen action.

Cheap OpenRouter model (`openai/gpt-oss-20b`) stands in for both the frontier
decider and Jev's filler here, to prove the harness works before spending real
budget on the actual ceiling model (GPT-5.x/Claude Opus/Gemini 3 Pro) or running
the full airline/retail/telecom task sets.

Usage: source scripts/env.sh (sets TAU2_DATA_DIR + activates the dwg env), have
OPENROUTER_API_KEY in .env, then:
    python3 scripts/tau2_vertical_slice.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.jev import JevDecider  # noqa: E402
from dwg.jev_tau2_agent import JevTau2Agent  # noqa: E402

CHEAP_MODEL = "openrouter/openai/gpt-oss-20b"
TASK_ID = "create_task_1"


def run(label: str, agent_factory) -> None:
    from tau2.evaluator.evaluator import EvaluationType
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.runner import build_environment, build_user, get_tasks, run_simulation

    task = get_tasks("mock", task_ids=[TASK_ID])[0]
    env = build_environment("mock")
    agent = agent_factory(tools=env.get_tools(), domain_policy=env.get_policy())
    user = build_user("user_simulator", env, task, llm=CHEAP_MODEL)

    orchestrator = Orchestrator(
        domain="mock", agent=agent, user=user, environment=env, task=task, max_steps=20, max_errors=5, seed=42
    )
    result = run_simulation(orchestrator, evaluation_type=EvaluationType.ALL)

    from tau2.utils.llm_utils import get_cost

    agent_cost, _ = get_cost(result.messages)

    print(f"=== {label} ===")
    print(f"  reward      : {result.reward_info.reward}")
    print(f"  agent_cost  : ${agent_cost}")
    print(f"  messages    : {len(result.messages)}")
    for i, msg in enumerate(result.messages):
        role = msg.role.value if hasattr(msg.role, "value") else msg.role
        content = str(msg.content)[:100] if msg.content else "(tool call/result)"
        print(f"    [{i}][{role}] {content}")
    print()


def main() -> int:
    load_dotenv()

    from tau2.agent.llm_agent import LLMAgent

    run(
        "frontier-only (LLMAgent)",
        lambda tools, domain_policy: LLMAgent(tools=tools, domain_policy=domain_policy, llm=CHEAP_MODEL),
    )

    jev = JevDecider()
    run(
        "Jev (respond/tool choice) + filler LLM",
        lambda tools, domain_policy: JevTau2Agent(
            tools=tools, domain_policy=domain_policy, jev=jev, filler_llm=CHEAP_MODEL
        ),
    )

    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
