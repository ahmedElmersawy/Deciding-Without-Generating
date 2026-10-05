"""Live smoke test of the cache-guard question (PLAN.md CG2): each API decider answers the six
hand-made cases in tests/test_cacheguard.py once. Checks the question reads as intended before
the harness spends real money; not a measurement (~$0.02).

Usage: python3 scripts/smoke_cacheguard.py [--deciders jev gpt-oss gpt-5.6]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from dwg import cacheguard as cg  # noqa: E402
from test_cacheguard import HAND_CASES  # noqa: E402

DECIDERS = {
    "jev": lambda: cg.jev_decider(),
    "gpt-oss": lambda: cg.llm_decider("openrouter/openai/gpt-oss-20b", name="gpt-oss", provider_sort="price"),
    "gpt-5.6": lambda: cg.llm_decider("openrouter/openai/gpt-5.6-sol", name="gpt-5.6", provider_sort="price"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deciders", nargs="+", default=list(DECIDERS), choices=list(DECIDERS))
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    spent, right, total = 0.0, 0, 0
    for name in args.deciders:
        decider = DECIDERS[name]()
        for case in HAND_CASES:
            try:
                d = decider.decide(cg.render_state(case), cg.OPTIONS)
            except Exception as exc:  # a smoke test reports, it doesn't stop
                print(f"  {name:8s} {case['name']:32s} ERROR {exc!r}"[:200])
                continue
            ok = d.choice == cg.reference(case)
            right += ok
            total += 1
            spent += d.cost_usd or 0.0
            conf = "n/a" if d.confidence is None else f"{d.confidence:.2f}"
            print(f"  {name:8s} {case['name']:32s} -> {d.choice:10s} conf {conf}  {'ok' if ok else 'WRONG'}  {d.latency_s:.2f}s")
    print(f"==> {right}/{total} as expected, ${spent:.4f} spent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
