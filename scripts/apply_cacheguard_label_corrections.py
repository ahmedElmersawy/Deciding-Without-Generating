"""Apply the cache-guard label corrections (DECISIONS.md 2026-10-07) to the vCache streams.

Procedure (results/label-corrections/GUIDELINE.md): every dev + test pair of LmArena and
SearchQueries was judged blind by Claude Opus 5.5 (pass 1: no original label, similarity or
decider output shown). Pairs where pass 1 disagreed with the vCache label with high confidence were
judged again, blind, by a separate Opus 5.5 instance (pass 2). A label changes only when pass 2
agrees with pass 1 with high confidence. These are LLM corrections, not human ones.

Inputs:  results/label-corrections/<dataset>-pass1.jsonl, <dataset>-pass2.jsonl
         ({"id", "verdict": same|different, "confidence": high|low, "reason"})
Outputs: results/label-corrections/<dataset>-corrections.jsonl (one row per changed label, with
         both queries, both labels, both passes' reasons and who corrected it), and the stream
         results/states/cacheguard-<dataset>.jsonl rewritten in place with `reuse_correct` set to
         the corrected label, the vCache label kept as `reuse_correct_original` and `label_source`
         = "vcache" or "corrected:claude-opus-5-5". Idempotent: always starts from the original label.

Usage: python3 scripts/apply_cacheguard_label_corrections.py [--dataset lmarena searchqueries]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CORR = ROOT / "results/label-corrections"
CORRECTOR = "claude-opus-5-5"


def read(path: Path) -> dict[str, dict]:
    out = {}
    for line in path.open():
        r = json.loads(line)
        out[r["id"]] = r
    return out


def state_id(r: dict) -> str:
    return f"{r['dataset']}:{r['split']}:{r['query_id']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", nargs="+", default=["lmarena", "searchqueries"])
    args = parser.parse_args()
    for ds in args.dataset:
        stream_path = ROOT / f"results/states/cacheguard-{ds}.jsonl"
        rows = [json.loads(line) for line in stream_path.open()]
        p1, p2 = read(CORR / f"{ds}-pass1.jsonl"), read(CORR / f"{ds}-pass2.jsonl")
        missing = [state_id(r) for r in rows if state_id(r) not in p1]
        assert not missing, f"{ds}: {len(missing)} pairs without a pass-1 verdict, e.g. {missing[:3]}"
        changes, candidates = [], 0
        for r in rows:
            original = bool(r.get("reuse_correct_original", r["reuse_correct"]))
            sid = state_id(r)
            v1 = p1[sid]
            same1 = v1["verdict"] == "same"
            flip = False
            if same1 != original and v1["confidence"] == "high":
                candidates += 1
                v2 = p2.get(sid)
                assert v2 is not None, f"{ds}: flip candidate {sid} has no pass-2 verdict"
                flip = (v2["verdict"] == "same") == same1 and v2["confidence"] == "high"
            r["reuse_correct_original"] = original
            r["reuse_correct"] = (not original) if flip else original
            r["label_source"] = f"corrected:{CORRECTOR}" if flip else "vcache"
            if flip:
                changes.append(dict(
                    id=sid, split=r["split"], new_query=r["query"], cached_query=r["cand_prompt"],
                    vcache_label="reuse" if original else "regenerate",
                    corrected_label="reuse" if r["reuse_correct"] else "regenerate",
                    pass1_reason=v1.get("reason", ""), pass2_reason=p2[sid].get("reason", ""),
                    corrected_by=f"{CORRECTOR} (LLM, two blind passes)", human_checked=False,
                ))
        with stream_path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        with (CORR / f"{ds}-corrections.jsonl").open("w") as fh:
            for c in changes:
                fh.write(json.dumps(c) + "\n")
        meta_path = stream_path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text())
        meta["label_corrections"] = dict(
            corrector=CORRECTOR, guideline="results/label-corrections/GUIDELINE.md",
            reviewed=len(rows), flip_candidates=candidates, changed=len(changes),
            changed_by_split={s: sum(c["split"] == s for c in changes) for s in ("dev", "test")},
            to_reuse=sum(c["corrected_label"] == "reuse" for c in changes),
            to_regenerate=sum(c["corrected_label"] == "regenerate" for c in changes),
        )
        meta["reuse_correct_rate"] = {s: sum(r["reuse_correct"] for r in rows if r["split"] == s)
                                      / max(1, sum(r["split"] == s for r in rows)) for s in ("dev", "test")}
        meta["reuse_correct_rate_original"] = {s: sum(r["reuse_correct_original"] for r in rows if r["split"] == s)
                                               / max(1, sum(r["split"] == s for r in rows)) for s in ("dev", "test")}
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        print(f"==> {ds}: {len(rows)} reviewed, {candidates} flip candidates, {len(changes)} labels changed "
              f"({meta['label_corrections']['to_reuse']} -> reuse, {meta['label_corrections']['to_regenerate']} -> regenerate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
