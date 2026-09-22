"""Vertical-slice proof for the agent-control decision point (System1_Jev_Benchmark.pdf).

Runs the SAME toy tool-calling task through smolagents' `ToolCallingAgent` twice:
  1. Frontier-only: a plain `LiteLLMModel` decides tool choice AND writes arguments.
  2. Jev: `JevModel` (dwg.jev_model) has Jev decide tool choice; the same cheap
     LiteLLMModel only fills in arguments for the tool Jev picked.

This is a smoke test, not the real benchmark run: it uses a very cheap OpenRouter
model (`openai/gpt-oss-20b`) as both the frontier decider and the argument-filler,
to prove the JevModel harness actually works end-to-end before building out the
real router/cache-guard/agent-control benchmarks and the other three deciders.

Usage: source scripts/env.sh, have OPENROUTER_API_KEY in .env, then:
    python3 scripts/agent_control_vertical_slice.py
"""

import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from smolagents import LiteLLMModel, ToolCallingAgent, tool

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.jev import JevDecider  # noqa: E402
from dwg.jev_model import JevModel  # noqa: E402

CHEAP_MODEL = "openrouter/openai/gpt-oss-20b"
TASK = "What is 47 plus 89? Use the add tool to compute it, then give the final numeric answer."


@tool
def add(a: int, b: int) -> int:
    """Add two integers together.

    Args:
        a: first addend
        b: second addend
    """
    return a + b


def run(label: str, model) -> None:
    agent = ToolCallingAgent(tools=[add], model=model, max_steps=4)
    t0 = time.perf_counter()
    result = agent.run(TASK, return_full_result=True)
    elapsed = time.perf_counter() - t0

    print(f"=== {label} ===")
    print(f"  answer      : {result.output!r}")
    print(f"  correct     : {'136' in str(result.output)}")
    print(f"  elapsed     : {elapsed:.2f}s")
    print(f"  token_usage : {result.token_usage}")
    print(f"  steps       : {len(result.steps)}")
    print()


def main() -> int:
    load_dotenv()

    run("frontier-only (LiteLLMModel)", LiteLLMModel(model_id=CHEAP_MODEL))

    filler = LiteLLMModel(model_id=CHEAP_MODEL)
    run("Jev (tool choice) + filler LLM (arguments)", JevModel(jev=JevDecider(), filler_model=filler))

    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
