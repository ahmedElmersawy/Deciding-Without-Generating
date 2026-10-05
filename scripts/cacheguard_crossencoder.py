"""Cross-encoder baseline for the cache guard (PLAN.md CG3): an off-the-shelf duplicate-question
model scores every stream row (dev and test), so the analysis can tune its threshold on dev and
report it on test, like the similarity threshold.

Model: cross-encoder/quora-roberta-large (Apache-2.0), trained on Quora Question Pairs to judge
"same question?"; chosen before any cache-guard results (DECISIONS.md 2026-10-05). It is the
honest bar for Jev's "no training needed": general-purpose, untrained on our data, local.
Input is (new query, cached query); one logit -> sigmoid = P(duplicate). No API cost; GPU time
per pair is recorded as latency.

Output: <out>/scores-crossencoder.jsonl (state_id, split, score, latency_s), with state ids as in
replay_decisions.py --task cacheguard.

Usage: python3 scripts/cacheguard_crossencoder.py --states results/states/cacheguard-gsmplus.jsonl \\
           --out results/replay/cacheguard-gsmplus
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

MODEL = "cross-encoder/quora-roberta-large"
REVISION = "d3f224f29852aa5bc5e9dc77f37f13b85e19d3e0"


def main() -> int:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.states.open() if line.strip()]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL, revision=REVISION).to(device).eval()
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / "scores-crossencoder.jsonl"
    with torch.inference_mode(), out.open("w") as fh:
        for i in range(0, len(rows), args.batch):
            batch = rows[i:i + args.batch]
            enc = tok([r["query"] for r in batch], [r["cand_prompt"] for r in batch], padding=True,
                      truncation=True, max_length=512, return_tensors="pt").to(device)
            if device == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            scores = torch.sigmoid(model(**enc).logits[:, 0]).float().cpu().tolist()
            if device == "cuda":
                torch.cuda.synchronize()
            per_pair = (time.perf_counter() - t0) / len(batch)
            for r, s in zip(batch, scores):
                fh.write(json.dumps({"state_id": f"{r['dataset']}:{r['split']}:{r['query_id']}", "split": r["split"],
                                     "score": round(s, 6), "latency_s": per_pair, "device": device}) + "\n")
    print(f"==> {len(rows)} pairs scored with {MODEL}@{REVISION[:8]} on {device} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
