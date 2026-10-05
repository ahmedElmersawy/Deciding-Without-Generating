"""Build the cache-guard decision streams (PLAN.md CG1): for each benchmark, which queries the
deciders see, the cached prompt each would reuse, and whether reusing it is correct.

A cache-guard decision: a new query arrives, the semantic cache returns the most similar
earlier prompt (cosine over GTE-large-en-v1.5 embeddings, the one embedding all three
datasets share), and a decider says `reuse` (serve the cached answer) or `regenerate`.

- vCache SemBenchmarkLmArena / SemBenchmarkSearchQueries: the stream is the file's own order,
  as vCache's benchmark runs it (a cache that holds every earlier prompt). A query's candidate
  is its nearest earlier prompt; reuse is correct iff both share an id_set (vCache's own rule).
  The file is downloaded whole to --data-dir (2.4-6.6 GB, resumable; a ranged read of just
  the columns timed out mid-stream on Gilbreth) and only the needed columns are kept, as a
  small parquet next to it.
- GSM-Plus: the cache holds the 1,319 GSM8K seed questions; queries are the perturbed
  variants; the candidate is the nearest seed. Reuse is correct iff the candidate's answer
  equals the variant's (never for "critical thinking" variants, which have no answer).
  Embeddings are computed here with the same model, pinned to a revision.

Queries are split dev / test by class (id_set, or the GSM-Plus seed), so nothing tuned on dev
shares a class with test. Query positions are sampled uniformly over the stream (seeded).
Output: results/states/cacheguard-<dataset>.jsonl (+ .meta.json); DECISIONS.md 2026-10-05.

Usage (from repo root; GSM-Plus embedding wants a GPU, the vCache sets don't):
    python3 scripts/build_cacheguard_streams.py --dataset lmarena --check-embeddings
    python3 scripts/build_cacheguard_streams.py --dataset lmarena
    python3 scripts/build_cacheguard_streams.py --dataset searchqueries
    python3 scripts/build_cacheguard_streams.py --dataset gsmplus
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

EMBED_MODEL = "Alibaba-NLP/gte-large-en-v1.5"
EMBED_REVISION = "104333d6af6f97649377c2afbde10a7704870c7b"  # model weights + config
EMBED_CODE_REVISION = "40ced75c3017eb27626c9d4ea981bde21a2662f4"  # Alibaba-NLP/new-impl (remote code)

VCACHE = {
    "lmarena": dict(repo="vCache/SemBenchmarkLmArena", cls="ID_Set", response="response_gpt-4o-mini"),
    "searchqueries": dict(repo="vCache/SemBenchmarkSearchQueries", cls="id_set", response="response_llama_3_8b"),
}
GSMPLUS = dict(repo="qintongli/GSM-Plus", file="data/test-00000-of-00001.jsonl")
# Answers that change under each GSM-Plus perturbation are a property of the data, not assumed:
# labels always compare the actual answers.


def vcache_columns(name: str, data_dir: Path):
    """The needed columns of a vCache benchmark, read from the Hub once and cached locally."""
    import pandas as pd
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    spec = VCACHE[name]
    local = data_dir / f"{name}-columns.parquet"
    cols = ["id", "prompt", spec["cls"], "emb_gte", spec["response"], spec["response"] + "_lat"]
    if not local.exists():
        print(f"==> downloading {spec['repo']} train.parquet, keeping {cols}")
        full = hf_hub_download(spec["repo"], "train.parquet", repo_type="dataset", local_dir=data_dir / name)
        pq.write_table(pq.read_table(full, columns=cols), local)
    df = pd.read_parquet(local)
    emb = np.stack([np.asarray(json.loads(s), dtype=np.float32) for s in df["emb_gte"]])
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    return df.drop(columns=["emb_gte"]), emb


def _extended_attention_mask(self, attention_mask, input_shape=None, device=None, dtype=None):
    """transformers 4.x's ModuleUtilsMixin.get_extended_attention_mask (encoder case), which the
    pinned GTE remote code calls and transformers 5 no longer provides: 1/0 padding mask ->
    additive mask (0 keep, dtype-min drop), broadcast over heads and query positions."""
    import torch

    dtype = dtype or next(self.parameters()).dtype
    ext = attention_mask[:, None, :, :] if attention_mask.dim() == 3 else attention_mask[:, None, None, :]
    return (1.0 - ext.to(dtype)) * torch.finfo(dtype).min


def load_embedder(device: str):
    """GTE-large-en-v1.5 at the pinned revisions. Built from its config and then given the
    checkpoint's weights, rather than `from_pretrained`: transformers 5 initializes on the meta
    device, which leaves the remote code's non-persistent buffers (position_ids, rotary
    inv_freq / cos / sin caches; not in the checkpoint) as uninitialized memory -> garbage
    indices and a CUDA device-side assert. Correctness is checked by --check-embeddings
    against vCache's stored GTE vectors."""
    import torch
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    from transformers import AutoConfig, AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(EMBED_MODEL, revision=EMBED_REVISION)
    config = AutoConfig.from_pretrained(EMBED_MODEL, revision=EMBED_REVISION, trust_remote_code=True,
                                        code_revision=EMBED_CODE_REVISION)
    # transformers 5 drops `rope_scaling` (NTK, factor 2) from this remote config ("hasn't set it
    # as attribute"), silently changing the rotary positions; put back what config.json says.
    raw = json.loads(Path(hf_hub_download(EMBED_MODEL, "config.json", revision=EMBED_REVISION)).read_text())
    for key in ("rope_scaling", "rope_theta"):
        setattr(config, key, raw[key])
    model = AutoModel.from_config(config, trust_remote_code=True, code_revision=EMBED_CODE_REVISION)
    state = load_file(hf_hub_download(EMBED_MODEL, "model.safetensors", revision=EMBED_REVISION))
    res = model.load_state_dict(state, strict=False)
    if res.missing_keys or res.unexpected_keys:
        raise RuntimeError(f"GTE weights don't match the model: missing {res.missing_keys}, unexpected {res.unexpected_keys}")
    if not hasattr(model, "get_extended_attention_mask"):
        type(model).get_extended_attention_mask = _extended_attention_mask
    model = model.to(device).eval()

    def embed(texts: list[str], batch: int = 64) -> np.ndarray:
        out = []
        with torch.inference_mode():
            for i in range(0, len(texts), batch):
                enc = tok(texts[i:i + batch], padding=True, truncation=True, max_length=8192,
                          return_tensors="pt").to(device)
                cls = model(**enc).last_hidden_state[:, 0]  # CLS pooling, per the model card
                out.append(torch.nn.functional.normalize(cls, dim=-1).float().cpu().numpy())
        return np.concatenate(out)

    return embed


def class_split(classes, dev_frac: float, rng) -> dict:
    uniq = np.array(sorted(set(classes)))
    dev = set(rng.permutation(uniq)[: int(round(len(uniq) * dev_frac))].tolist())
    return {c: ("dev" if c in dev else "test") for c in uniq.tolist()}


def nearest_earlier(emb: np.ndarray, positions: np.ndarray, chunk: int = 16384):
    """For each query position p, the most similar prompt among positions < p (cosine)."""
    q = emb[positions]
    best = np.full(len(positions), -np.inf, dtype=np.float32)
    arg = np.full(len(positions), -1, dtype=np.int64)
    for start in range(0, int(positions.max()), chunk):
        block = emb[start:start + chunk]
        sims = q @ block.T
        idx = np.arange(start, start + len(block))
        sims[idx[None, :] >= positions[:, None]] = -np.inf  # only earlier prompts
        j = sims.argmax(axis=1)
        val = sims[np.arange(len(positions)), j]
        better = val > best
        best[better], arg[better] = val[better], idx[j[better]]
    return arg, best


def build_vcache(name: str, args) -> list[dict]:
    spec = VCACHE[name]
    df, emb = vcache_columns(name, args.data_dir)
    rng = np.random.default_rng(args.seed)
    classes = df[spec["cls"]].to_numpy()
    split_of = class_split(classes, args.dev_frac, rng)
    rows = []
    for split, n in (("test", args.n_test), ("dev", args.n_dev)):
        eligible = np.array([p for p in range(1, len(df)) if split_of[classes[p]] == split])
        positions = np.sort(rng.choice(eligible, size=min(n, len(eligible)), replace=False))
        cand, sim = nearest_earlier(emb, positions)
        for p, c, s in zip(positions.tolist(), cand.tolist(), sim.tolist()):
            rows.append(dict(
                dataset=name, split=split, query_id=int(df["id"].iat[p]), position=p,
                query=df["prompt"].iat[p], query_class=int(classes[p]),
                query_regen_latency_s=float(df[spec["response"] + "_lat"].iat[p]),
                cand_id=int(df["id"].iat[c]), cand_position=c, cand_prompt=df["prompt"].iat[c],
                cand_class=int(classes[c]), cand_response=df[spec["response"]].iat[c],
                similarity=round(s, 6), reuse_correct=bool(classes[p] == classes[c]),
            ))
    return rows


def same_answer(a, b) -> bool:
    if a is None or b is None or str(a).strip().lower() in ("", "none"):
        return False
    try:
        return abs(float(str(a).replace(",", "")) - float(str(b).replace(",", ""))) < 1e-6
    except ValueError:
        return str(a).strip() == str(b).strip()


def build_gsmplus(args) -> list[dict]:
    import pandas as pd
    import torch
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(GSMPLUS["repo"], GSMPLUS["file"], repo_type="dataset", local_dir=args.data_dir / "gsmplus")
    df = pd.read_json(path, lines=True)
    seeds = df.drop_duplicates("seed_question")[["seed_question", "seed_answer"]].reset_index(drop=True)
    cache_npz = args.data_dir / "gsmplus-gte.npz"
    if cache_npz.exists():
        z = np.load(cache_npz)
        seed_emb, var_emb = z["seed"], z["variant"]
    else:
        embed = load_embedder("cuda" if torch.cuda.is_available() else "cpu")
        seed_emb, var_emb = embed(seeds["seed_question"].tolist()), embed(df["question"].tolist())
        np.savez(cache_npz, seed=seed_emb, variant=var_emb)
    seed_index = {q: i for i, q in enumerate(seeds["seed_question"])}
    rng = np.random.default_rng(args.seed)
    split_of = class_split(range(len(seeds)), args.dev_frac, rng)
    df["seed_idx"] = df["seed_question"].map(seed_index)
    df["split"] = df["seed_idx"].map(split_of)
    rows = []
    for split, n in (("test", args.n_test), ("dev", args.n_dev)):
        part = df[df["split"] == split]
        types = sorted(part["perturbation_type"].unique())
        per_type = n // len(types)
        for t in types:
            sub = part[part["perturbation_type"] == t]
            pick = sub.iloc[np.sort(rng.choice(len(sub), size=min(per_type, len(sub)), replace=False))]
            for i, r in pick.iterrows():
                sims = seed_emb @ var_emb[i]
                c = int(sims.argmax())
                rows.append(dict(
                    dataset="gsmplus", split=split, query_id=int(i), perturbation_type=t,
                    query=r["question"], query_class=int(r["seed_idx"]), query_answer=None if pd.isna(r["answer"]) else str(r["answer"]),
                    cand_id=c, cand_prompt=seeds["seed_question"].iat[c], cand_class=c,
                    cand_response=str(seeds["seed_answer"].iat[c]),
                    similarity=round(float(sims[c]), 6),
                    reuse_correct=same_answer(r["answer"], seeds["seed_answer"].iat[c]),
                ))
    return rows


def check_embeddings(args) -> int:
    """Does our GTE embedder do the cache's job as well as vCache's stored GTE vectors?

    Exact vectors differ (cosine 0.89-0.95 on LmArena prompts; pooling, truncation, rope and the
    original GTE-large were ruled out; DECISIONS.md 2026-10-05), so the check is functional:
    on 100 LmArena classes x 3 prompts, how often each embedding's nearest neighbour is in the
    same class. Ours must be within 2 points of the stored vectors and at least 95%. Exit 3 = fail."""
    import pandas as pd
    import torch

    df, emb = vcache_columns("lmarena", args.data_dir)
    rng = np.random.default_rng(0)
    counts = df["ID_Set"].value_counts()
    classes = rng.choice(counts[counts >= 3].index.to_numpy(), 100, replace=False)
    sel = pd.concat([df[df["ID_Set"] == c].head(3) for c in classes])
    ours = load_embedder("cuda" if torch.cuda.is_available() else "cpu")(sel["prompt"].tolist())
    y = sel["ID_Set"].to_numpy()

    def top1_same_class(e):
        sims = e @ e.T
        np.fill_diagonal(sims, -np.inf)
        return float((y[sims.argmax(1)] == y).mean())

    stored, mine = top1_same_class(emb[sel.index.to_numpy()]), top1_same_class(ours)
    print(f"==> nearest neighbour in the same class: vCache stored {stored:.3f}, ours {mine:.3f}")
    return 0 if (mine >= 0.95 and stored - mine <= 0.02) else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True, choices=["lmarena", "searchqueries", "gsmplus"])
    parser.add_argument("--data-dir", type=Path,
                        default=Path(os.environ.get("DWG_DATA_DIR", f"/scratch/gilbreth/{os.environ.get('USER', 'user')}/dwg-data")) / "cacheguard")
    parser.add_argument("--n-test", type=int, default=2000)
    parser.add_argument("--n-dev", type=int, default=600)
    parser.add_argument("--dev-frac", type=float, default=0.3, help="share of classes held out for tuning")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--check-embeddings", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)

    if args.check_embeddings:
        return check_embeddings(args)
    rows = build_gsmplus(args) if args.dataset == "gsmplus" else build_vcache(args.dataset, args)
    out = args.out or Path("results/states") / f"cacheguard-{args.dataset}.jsonl"
    with out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    meta = dict(dataset=args.dataset, seed=args.seed, dev_frac=args.dev_frac, n_test=args.n_test, n_dev=args.n_dev,
                embedding=dict(model=EMBED_MODEL, revision=EMBED_REVISION, code_revision=EMBED_CODE_REVISION),
                counts={s: sum(r["split"] == s for r in rows) for s in ("dev", "test")},
                reuse_correct_rate={s: float(np.mean([r["reuse_correct"] for r in rows if r["split"] == s] or [np.nan]))
                                    for s in ("dev", "test")})
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
