"""Build the router decision stream (PLAN.md R1): RouterBench 0-shot prompts with Mixtral-8x7B's and
GPT-4's recorded scores and $ costs, split train / dev / test stratified by task family.

Label (DECISIONS.md 2026-10-05): `large` iff the small model is wrong and the large one right
(score >= 0.5 counts as right: GSM8K's scores come in quarters); else `small` (the small model
suffices, or the large one would fail too). Quality later uses the raw scores.

Input: the RouterBench 0-shot parquet on scratch (converted once from the pickle after a
pickletools check; see DECISIONS.md). Output: results/states/router-routerbench.jsonl (+ .meta.json)
with the dev and test rows; the ~32k train rows (only what the floor needs: prompt, family, label)
go to --train-out on scratch, not into git.

Usage: python3 scripts/build_router_streams.py
"""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path

import numpy as np

SMALL, LARGE = "mistralai/mixtral-8x7b-chat", "gpt-4-1106-preview"
FAMILIES = {"grade-school-math": "gsm8k", "arc-challenge": "arc", "hellaswag": "hellaswag",
            "winogrande": "winogrande", "mbpp": "mbpp"}


def family(eval_name: str):
    return "mmlu" if eval_name.startswith("mmlu") else FAMILIES.get(eval_name)


def prompt_text(raw: str) -> str:
    """RouterBench stores a prompt as the repr of a list of strings."""
    try:
        parts = ast.literal_eval(raw)
        return "\n\n".join(str(p) for p in parts) if isinstance(parts, list) else str(parts)
    except (ValueError, SyntaxError):
        return raw


def main() -> int:
    import pandas as pd

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path,
                        default=Path(f"/scratch/gilbreth/{os.environ.get('USER', 'user')}/dwg-data/router/routerbench_0shot.parquet"))
    parser.add_argument("--n-test", type=int, default=2000)
    parser.add_argument("--n-dev", type=int, default=600)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=Path("results/states/router-routerbench.jsonl"))
    parser.add_argument("--train-out", type=Path,
                        default=Path(f"/scratch/gilbreth/{os.environ.get('USER', 'user')}/dwg-data/router/router-train.jsonl"))
    args = parser.parse_args()

    df = pd.read_parquet(args.data)
    df["family"] = df["eval_name"].map(family)
    df = df[df["family"].notna()].reset_index(drop=True)
    rng = np.random.default_rng(args.seed)
    fams = sorted(df["family"].unique())
    split = np.array(["train"] * len(df), dtype=object)
    for f in fams:  # equal share per family for test and dev (MBPP has 427 prompts: it caps its own share)
        idx = rng.permutation(np.flatnonzero(df["family"].to_numpy() == f))
        n_t, n_d = args.n_test // len(fams), args.n_dev // len(fams)
        split[idx[:n_t]] = "test"
        split[idx[n_t:n_t + n_d]] = "dev"
    rows = []
    for i, r in df.iterrows():
        s_score, l_score = float(r[SMALL]), float(r[LARGE])
        label = "large" if (s_score < 0.5 and l_score >= 0.5) else "small"
        row = dict(dataset="routerbench", split=split[i], query_id=int(i), query_class=int(i), family=r["family"],
                   eval_name=r["eval_name"], query=prompt_text(r["prompt"]), label=label)
        if split[i] != "train":
            row.update(small_score=s_score, large_score=l_score,
                       small_cost=float(r[SMALL + "|total_cost"]), large_cost=float(r[LARGE + "|total_cost"]))
        rows.append(row)
    with args.out.open("w") as fh, args.train_out.open("w") as train_fh:
        for row in rows:
            (train_fh if row["split"] == "train" else fh).write(json.dumps(row) + "\n")
    meta = dict(small=SMALL, large=LARGE, seed=args.seed, families=fams,
                counts={s: int((split == s).sum()) for s in ("train", "dev", "test")},
                needs_large={s: float(np.mean([r["label"] == "large" for r in rows if r["split"] == s])) for s in ("dev", "test")})
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
