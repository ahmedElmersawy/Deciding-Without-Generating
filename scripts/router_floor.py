"""Floor router (PLAN.md R3): a small classifier trained on RouterBench's own train split to predict
whether a prompt needs the large model, i.e. what RouteLLM-style learned routers do with the small
model's recorded correctness. Expected to beat Jev here (DECISIONS.md 2026-10-05): which prompts
*this* small model fails is learned from its record, not visible in the prompt to a general judge.

Model: distilbert/distilroberta-base (82M, Apache-2.0, pinned), one logit = P(large). Trained on
the train split (default up to 20,000 prompts, sampled with a fixed seed; the rest is unused),
hyperparameters fixed before seeing test: 2 epochs, lr 3e-5, batch 32, max length 256, seed 0.
Scores dev and test; the analysis sweeps its threshold (cost-quality curve) and reports P >= 0.5.

Output: <out>/scores-floor.jsonl (state_id, split, score = P(large), latency_s).
Usage: python3 scripts/router_floor.py --out results/replay/router-routerbench
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

BASE = "distilbert/distilroberta-base"
REVISION = "fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b"
EPOCHS, LR, BATCH, MAX_LEN, SEED = 2, 3e-5, 32, 256, 0


def main() -> int:
    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--states", type=Path, default=Path("results/states/router-routerbench.jsonl"))
    parser.add_argument("--train", type=Path,
                        default=Path(f"/scratch/gilbreth/{os.environ.get('USER', 'user')}/dwg-data/router/router-train.jsonl"))
    parser.add_argument("--max-train", type=int, default=20000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    train = [json.loads(line) for line in args.train.open() if line.strip()]
    train = random.Random(SEED).sample(train, min(args.max_train, len(train)))
    evals = [json.loads(line) for line in args.states.open() if line.strip()]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(BASE, revision=REVISION, num_labels=1).to(device)

    def encode(batch):
        return tok([r["query"] for r in batch], padding=True, truncation=True, max_length=MAX_LEN,
                   return_tensors="pt").to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    model.train()
    for epoch in range(EPOCHS):
        order = list(range(len(train)))
        random.shuffle(order)
        total = 0.0
        for i in range(0, len(order), BATCH):
            batch = [train[j] for j in order[i:i + BATCH]]
            y = torch.tensor([float(r["label"] == "large") for r in batch], device=device)
            loss = loss_fn(model(**encode(batch)).logits[:, 0], y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += loss.item() * len(batch)
        print(f"   epoch {epoch + 1}: train loss {total / len(train):.4f}", flush=True)

    model.eval()
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / "scores-floor.jsonl"
    with torch.inference_mode(), out.open("w") as fh:
        for i in range(0, len(evals), 64):
            batch = evals[i:i + 64]
            enc = encode(batch)
            if device == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            scores = torch.sigmoid(model(**enc).logits[:, 0]).float().cpu().tolist()
            if device == "cuda":
                torch.cuda.synchronize()
            per = (time.perf_counter() - t0) / len(batch)
            for r, s in zip(batch, scores):
                fh.write(json.dumps({"state_id": f"{r['dataset']}:{r['split']}:{r['query_id']}", "split": r["split"],
                                     "score": round(s, 6), "latency_s": per, "device": device}) + "\n")
    print(f"==> floor router ({BASE}@{REVISION[:8]}, {len(train)} train prompts) scored {len(evals)} dev+test -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
