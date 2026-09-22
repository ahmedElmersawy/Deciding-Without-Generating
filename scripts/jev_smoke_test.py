"""One-shot live call to Jev via OpenRouter, to confirm the systemone request/response
schema (CHECKS.md #2) actually holds through the OpenRouter passthrough — this has not
been verified against a live call yet (DECISIONS.md 2026-09-22).

Usage: source scripts/env.sh (or just have OPENROUTER_API_KEY in your shell/.env), then:
    python3 scripts/jev_smoke_test.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dwg.jev import JevError, JevDecider  # noqa: E402


def main() -> int:
    load_dotenv()
    try:
        decider = JevDecider()
    except JevError as exc:
        print(f"SETUP FAIL: {exc}")
        return 1

    try:
        answer = decider.choice(
            state="The user says: 'What's the capital of France?' No tools have been called yet.",
            name="pick_tool",
            instructions="Should the agent answer directly or search the web first?",
            criteria={
                "final_answer": "Answer directly, no search needed",
                "web_search": "Search the web before answering",
            },
        )
    except JevError as exc:
        print(f"CALL FAIL: {exc}")
        return 1

    print("ALL CHECKS PASSED")
    print(f"  concrete model returned : {answer.model}")
    print(f"  choice                  : {answer.choice}")
    print(f"  vendor confidence       : {answer.vendor_confidence}")
    print(f"  calibration confidence  : {answer.confidence}  (= probabilities[choice])")
    print(f"  probabilities           : {answer.probabilities}")
    print(f"  usage                   : {answer.usage}")
    print(f"  raw response            : {decider.last_response}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
