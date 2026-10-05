"""vCache baseline for the cache guard (PLAN.md CG3): vCache's verified policy (per-embedding
thresholds learned online, error bound delta), run UNMODIFIED through its public classes on our
streams. Our code only drives it; nothing of vCache's is copied (its code is CC BY-NC-ND,
DECISIONS.md 2026-10-05).

Runs in its own environment (vCache pins numpy/pandas/vllm versions that conflict with the
project's): /scratch/gilbreth/$USER/dwg-data/vcache_env, with vCache installed from
github.com/vcache-project/vCache @ 50694eeb (`pip install --no-deps -e`).

Driven as vCache's own benchmark mode drives it: precomputed GTE embeddings and responses are
injected (BenchmarkEmbeddingEngine / BenchmarkInferenceEngine), and correctness feedback compares
id_sets (BenchmarkComparisonSimilarityEvaluator), our rule too.
  - vCache sets: the whole stream in file order up to the last sampled query, as vCache's
    benchmark runs it; decisions are recorded at our dev / test query positions.
  - GSM-Plus: the 1,319 seed questions first (the cache), then our sampled variants in a fixed
    shuffled order; id_set = the numeric answer, so a hit is right iff the answers match.
vCache only stores prompts it missed, so it is scored as a system: a hit is right iff the served
answer's id_set matches; a miss is a needless regeneration iff our label says reuse was right.

Output: <out>/scores-vcache.jsonl (state_id, split, reuse, served_correct).

Usage (vCache env python):
    /scratch/gilbreth/$USER/dwg-data/vcache_env/bin/python scripts/cacheguard_vcache.py \\
        --dataset gsmplus --out results/replay/cacheguard-gsmplus
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np

DELTA = 0.05


def make_vcache(delta: float, capacity: int):
    from vcache.config import VCacheConfig
    from vcache.inference_engine.strategies.benchmark import BenchmarkInferenceEngine
    from vcache.main import VCache
    from vcache.vcache_core.cache.embedding_engine.strategies.benchmark import BenchmarkEmbeddingEngine
    from vcache.vcache_core.cache.embedding_store.embedding_metadata_storage import InMemoryEmbeddingMetadataStorage
    from vcache.vcache_core.cache.embedding_store.vector_db.strategies.hnsw_lib import HNSWLibVectorDB
    from vcache.vcache_core.similarity_evaluator.strategies.benchmark_comparison import (
        BenchmarkComparisonSimilarityEvaluator,
    )
    from vcache.vcache_policy.strategies.verified import VerifiedDecisionPolicy

    config = VCacheConfig(
        inference_engine=BenchmarkInferenceEngine(),
        embedding_engine=BenchmarkEmbeddingEngine(),
        vector_db=HNSWLibVectorDB(max_capacity=capacity),
        embedding_metadata_storage=InMemoryEmbeddingMetadataStorage(),
        similarity_evaluator=BenchmarkComparisonSimilarityEvaluator(),
    )
    return VCache(config, VerifiedDecisionPolicy(delta=delta))


def step(vc, prompt: str, emb, response: str, id_set: int):
    vc.vcache_config.embedding_engine.set_next_embedding([float(x) for x in emb])
    vc.vcache_config.inference_engine.set_next_response(response)
    hit, _, response_meta, _ = vc.infer_with_cache_info(prompt=prompt, system_prompt="", id_set=id_set)
    time.sleep(0.002)  # let vCache's asynchronous threshold updates run, as its benchmark loop does
    return bool(hit), (response_meta.id_set if (hit and response_meta is not None) else None)


def main() -> int:
    import pandas as pd

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True, choices=["lmarena", "searchqueries", "gsmplus"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--delta", type=float, default=DELTA)
    parser.add_argument("--data-dir", type=Path,
                        default=Path(f"/scratch/gilbreth/{os.environ.get('USER', 'user')}/dwg-data/cacheguard"))
    args = parser.parse_args()

    stream = [json.loads(line) for line in open(f"results/states/cacheguard-{args.dataset}.jsonl") if line.strip()]
    records = []
    if args.dataset == "gsmplus":
        z = np.load(args.data_dir / "gsmplus-gte.npz")
        df = pd.read_json(next((args.data_dir / "gsmplus").rglob("*.jsonl")), lines=True)
        seeds = df.drop_duplicates("seed_question")[["seed_question", "seed_answer"]].reset_index(drop=True)
        answer_ids: dict[str, int] = {}
        no_answer = iter(range(-1, -10**9, -1))

        def answer_id(a) -> int:
            """Same matching as build_cacheguard_streams.same_answer: numeric when it parses, else the
            text; no answer (critical-thinking variants) never matches anything."""
            text = "" if a is None else str(a).strip()
            if text.lower() in ("", "none", "nan"):
                return next(no_answer)
            try:
                key = f"num:{float(text.replace(',', '')):.6g}"
            except ValueError:
                key = f"text:{text}"
            return answer_ids.setdefault(key, len(answer_ids))

        vc = make_vcache(args.delta, capacity=len(seeds) + len(stream) + 10)
        for i, r in seeds.iterrows():
            step(vc, r["seed_question"], z["seed"][i], str(r["seed_answer"]), answer_id(r["seed_answer"]))
        order = list(stream)
        random.Random(0).shuffle(order)
        for r in order:
            qid = answer_id(r["query_answer"])
            hit, served = step(vc, r["query"], z["variant"][r["query_id"]], str(r["query_answer"]), qid)
            records.append((r, hit, hit and served is not None and served == qid))
    else:
        cls_col = "ID_Set" if args.dataset == "lmarena" else "id_set"
        resp_col = "response_gpt-4o-mini" if args.dataset == "lmarena" else "response_llama_3_8b"
        cols = pd.read_parquet(args.data_dir / f"{args.dataset}-columns.parquet")
        at = {r["position"]: r for r in stream}
        last = max(at)
        vc = make_vcache(args.delta, capacity=last + 10)
        t0 = time.time()
        for p in range(last + 1):
            emb = np.asarray(json.loads(cols["emb_gte"].iat[p]), dtype=np.float32)
            cls = int(cols[cls_col].iat[p])
            hit, served = step(vc, cols["prompt"].iat[p], emb / np.linalg.norm(emb), str(cols[resp_col].iat[p]), cls)
            if p in at:
                records.append((at[p], hit, hit and served == cls))
            if p % 5000 == 0:
                print(f"   {p}/{last} ({time.time() - t0:.0f}s)", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / "scores-vcache.jsonl"
    with out.open("w") as fh:
        for r, hit, served_correct in records:
            fh.write(json.dumps({"state_id": f"{r['dataset']}:{r['split']}:{r['query_id']}", "split": r["split"],
                                 "reuse": hit, "served_correct": bool(served_correct), "delta": args.delta}) + "\n")
    hits = [h for _, h, _ in records]
    print(f"==> vCache (delta {args.delta}) on {args.dataset}: {len(records)} queries, hit rate {np.mean(hits):.3f} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
