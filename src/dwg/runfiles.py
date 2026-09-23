"""Layout of a replay run directory, shared by replay and analysis (PLAN.md U0).

    <run>/meta.json               run-level, written once: which states, how filtered
    <run>/calls-<decider>.jsonl   one row per call, for ONE decider
    <run>/meta-<decider>.json     that decider's run record: model, repeats, GPU, energy block

Each decider owns its own files, so machines adding different deciders to the same run (the
laptop adding API deciders, Gilbreth adding Kev) never edit the same file and never conflict
in git.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def decider_slug(decider: str) -> str:
    """`llm:openrouter/openai/gpt-oss-20b` -> `llm_openrouter_openai_gpt-oss-20b`."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", decider)


def calls_path(run: Path, decider: str) -> Path:
    return run / f"calls-{decider_slug(decider)}.jsonl"


def decider_meta_path(run: Path, decider: str) -> Path:
    return run / f"meta-{decider_slug(decider)}.json"


def load_calls(run: Path) -> list[dict]:
    rows = []
    for path in sorted(run.glob("calls-*.jsonl")):
        with path.open() as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def load_decider_metas(run: Path) -> dict[str, dict]:
    """decider name -> its meta record."""
    metas = {}
    for path in sorted(run.glob("meta-*.json")):
        meta = json.loads(path.read_text())
        metas[meta["decider"]] = meta
    return metas
