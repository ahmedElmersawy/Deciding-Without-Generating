"""Label-audit sheet for the cache guard (PLAN.md CG7): test cases where most LLM deciders disagree
with the dataset's label, for a human to judge. vCache's labels are GPT-4.1-nano's (DECISIONS.md
2026-10-05), so a strong decider "disagreeing" may be a label error; this measures how often.

A case qualifies when the majority vote of Jev, GPT-5.6 and GPT-OSS-20B (each the majority over its
own repeats) differs from the label. Sample (seeded): 40 LmArena, 40 SearchQueries, 20 GSM-Plus
(GSM-Plus labels are exact numeric answers: a control, expected to be right).

Columns: case, dataset, new_query, cached_query, cached_answer (cut at 600 chars), dataset_says,
deciders_say, then blank `your_verdict` (reuse / regenerate / unsure) and `notes` to fill in by hand.
Fill it without looking at the two "says" columns first if you can.

Usage: python3 scripts/cacheguard_audit.py  ->  results/replay/cacheguard-label-audit.csv
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dwg import cacheguard as cg  # noqa: E402
from dwg.runfiles import load_outcomes  # noqa: E402

DECIDERS = ["jev", "llm:openrouter/openai/gpt-5.6-sol", "llm:openrouter/openai/gpt-oss-20b"]
PER_DATASET = {"lmarena": 40, "searchqueries": 40, "gsmplus": 20}


def main() -> int:
    out_rows = []
    for dataset, n in PER_DATASET.items():
        run = ROOT / f"results/replay/cacheguard-{dataset}"
        stream = {f"{r['dataset']}:{r['split']}:{r['query_id']}": r
                  for r in (json.loads(line) for line in open(ROOT / f"results/states/cacheguard-{dataset}.jsonl"))
                  if r["split"] == "test"}
        votes = defaultdict(lambda: defaultdict(Counter))
        for o in load_outcomes(run):
            if o["decider"] in DECIDERS and o["error"] is None and o["state_id"] in stream:
                votes[o["state_id"]][o["decider"]][o["choice"]] += 1
        disagree = []
        for sid, by_d in votes.items():
            if len(by_d) < len(DECIDERS):
                continue
            majority = Counter(c.most_common(1)[0][0] for c in by_d.values()).most_common(1)[0][0]
            if majority != cg.reference(stream[sid]):
                disagree.append((sid, majority))
        print(f"==> {dataset}: {len(disagree)} of {len(votes)} test cases where the deciders' majority disagrees with the label")
        for sid, majority in random.Random(0).sample(disagree, min(n, len(disagree))):
            r = stream[sid]
            answer = (r.get("cand_response") or "").strip() if cg.has_answer(r) else "(dataset has no answers)"
            out_rows.append({
                "case": sid, "dataset": dataset, "new_query": r["query"], "cached_query": r["cand_prompt"],
                "cached_answer": answer[:600] + (" [...]" if len(answer) > 600 else ""),
                "dataset_says": cg.reference(r), "deciders_say": majority, "your_verdict": "", "notes": "",
            })
    out = ROOT / "results/replay/cacheguard-label-audit.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    print(f"==> {len(out_rows)} cases -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
