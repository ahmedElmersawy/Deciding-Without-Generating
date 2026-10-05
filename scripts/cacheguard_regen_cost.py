"""What a regeneration costs (PLAN.md CG6): GPT-5.6-sol answers a seeded sample of each dataset's
test queries, recording OpenRouter's $ and the latency. Every `regenerate` decision pays this,
so it turns wrong-reuse / needless-regeneration rates into $ and seconds per query.

200 queries per dataset (not the planned 500, to fit the balance left after CG5; the mean of a
cost is stable at that size). LmArena and GSM-Plus only: SearchQueries has no answers, and its
regeneration latency comes from vCache's recorded llama-3-8b latencies.

Spending guard as in replay_decisions.py: the estimate (--est-cost-per-call x n) must fit
--max-usd and the live balance; the first 402 / key-limit refusal stops paid calls.

Output: results/replay/cacheguard-<dataset>/regen-gpt-5.6-sol.jsonl
Usage:  python3 scripts/cacheguard_regen_cost.py --dataset gsmplus --n 200 --max-usd 3
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dwg.billing import check_budget  # noqa: E402
from dwg.decisions import _openrouter_cost  # noqa: E402
from dwg.errors import is_out_of_credits  # noqa: E402

MODEL = "openrouter/openai/gpt-5.6-sol"


def main() -> int:
    import litellm

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True, choices=["lmarena", "gsmplus"])
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--est-cost-per-call", type=float, default=0.015)
    parser.add_argument("--max-usd", type=float, required=True)
    parser.add_argument("--max-tokens", type=int, default=4096, help="cap per answer (bounds OpenRouter's pre-authorization)")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    rows = [json.loads(line) for line in open(ROOT / f"results/states/cacheguard-{args.dataset}.jsonl") if line.strip()]
    rows = random.Random(0).sample([r for r in rows if r["split"] == "test"], args.n)
    check_budget(args.n * args.est_cost_per_call, args.max_usd)

    out = ROOT / f"results/replay/cacheguard-{args.dataset}/regen-gpt-5.6-sol.jsonl"
    stop = {"flag": False}

    def answer(r):
        if stop["flag"]:
            return None
        rec = {"state_id": f"{r['dataset']}:{r['split']}:{r['query_id']}", "model": MODEL, "error": None}
        t0 = time.perf_counter()
        try:
            resp = litellm.completion(model=MODEL, messages=[{"role": "user", "content": r["query"]}],
                                      max_tokens=args.max_tokens,
                                      extra_body={"usage": {"include": True}, "provider": {"sort": "price"}})
            usage = resp.usage
            rec.update(latency_s=time.perf_counter() - t0,
                       cost_usd=_openrouter_cost(resp),
                       input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens)
        except Exception as exc:
            rec["error"] = repr(exc)[:400]
            if is_out_of_credits(rec["error"]):
                stop["flag"] = True
        return rec

    spent = 0.0
    with ThreadPoolExecutor(max_workers=args.workers) as pool, out.open("a") as fh:
        for rec in pool.map(answer, rows):
            if rec is None:
                continue
            fh.write(json.dumps(rec) + "\n")
            spent += rec.get("cost_usd") or 0.0
            if spent >= args.max_usd:
                stop["flag"] = True
    done = [json.loads(line) for line in out.open() if line.strip()]
    ok = [d for d in done if d["error"] is None]
    if ok:
        print(f"==> {args.dataset}: {len(ok)} answers, mean ${sum(d['cost_usd'] or 0 for d in ok) / len(ok):.4f}, "
              f"mean {sum(d['latency_s'] for d in ok) / len(ok):.2f}s, ${spent:.2f} spent this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
