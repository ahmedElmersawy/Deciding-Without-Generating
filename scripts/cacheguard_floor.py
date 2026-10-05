"""Floor decider for the cache guard (PLAN.md CG3): a small classifier trained on each dataset's
own dev split, i.e. what a team would build with a few hundred labelled examples, the barrier
Jev's "no training needed" claim is about.

Model: cross-encoder/quora-distilroberta-base (82M, Apache-2.0, pinned), fine-tuned on the dev
split's (new query, cached query) pairs with reuse_correct as the label, then scored on test.
Generic by design: no hand-made features (e.g. "do the numbers differ?"), which would encode
our own knowledge of a dataset's hard negatives. Hyperparameters fixed before seeing test:
4 epochs, lr 2e-5, batch 16, max length 256, seed 0; reuse iff P >= 0.5.

Output: <out>/scores-floor.jsonl (test rows; state_id, split, score, latency_s), like the
cross-encoder's, for analyze_cacheguard.py.

Usage: python3 scripts/cacheguard_floor.py --states results/states/cacheguard-gsmplus.jsonl \\
           --out results/replay/cacheguard-gsmplus
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

BASE = "cross-encoder/quora-distilroberta-base"
REVISION = "f62e7a4b20b97195c2868e53ec59126df5eac743"
EPOCHS, LR, BATCH, MAX_LEN, SEED = 4, 2e-5, 16, 256, 0


def main() -> int:
    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    rows = [json.loads(line) for line in args.states.open() if line.strip()]
    dev = [r for r in rows if r["split"] == "dev"]
    test = [r for r in rows if r["split"] == "test"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(BASE, revision=REVISION).to(device)

    def encode(batch):
        return tok([r["query"] for r in batch], [r["cand_prompt"] for r in batch], padding=True,
                   truncation=True, max_length=MAX_LEN, return_tensors="pt").to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    model.train()
    for epoch in range(EPOCHS):
        order = list(range(len(dev)))
        random.shuffle(order)
        total = 0.0
        for i in range(0, len(order), BATCH):
            batch = [dev[j] for j in order[i:i + BATCH]]
            labels = torch.tensor([float(r["reuse_correct"]) for r in batch], device=device)
            loss = loss_fn(model(**encode(batch)).logits[:, 0], labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += loss.item() * len(batch)
        print(f"   epoch {epoch + 1}: train loss {total / len(dev):.4f}")

    model.eval()
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / "scores-floor.jsonl"
    with torch.inference_mode(), out.open("w") as fh:
        for i in range(0, len(test), 32):
            batch = test[i:i + 32]
            enc = encode(batch)
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
    print(f"==> floor ({BASE}@{REVISION[:8]}, trained on {len(dev)} dev pairs) scored {len(test)} test pairs -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
