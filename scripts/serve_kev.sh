#!/bin/bash
# Serve Kev (github.com/jaredpalmer/kev) — the open-weights System One reproduction used as the
# local "Jev-like" decider (arm E, DECISIONS.md 2026-09-23) — on 127.0.0.1:$KEV_PORT.
#
# Kev runs in ITS OWN uv environment, not the `dwg` env: it pins torch<2.9, while dwg pins
# torch 2.13 for vLLM. The benchmark talks to it over HTTP only.
#
# One-time setup (laptop or Gilbreth login node):
#   git clone https://github.com/jaredpalmer/kev.git "$KEV_REPO"
#   git -C "$KEV_REPO" checkout "$KEV_COMMIT"
#   (cd "$KEV_REPO" && uv sync --frozen --extra serve)
#
# Usage:  scripts/serve_kev.sh [kev-0.8b|kev-4b|kev-9b]      (default kev-4b)
#
# KEV_PREFIX_CACHE defaults to 0 HERE (Kev's own default is 4): replay asks about the same
# state several times, and cache hits on repeats would make Kev look faster/cheaper than a
# real agent loop, where each decision's state is new. Set KEV_PREFIX_CACHE=4 to measure the
# cached regime deliberately — and say so in the results.
set -euo pipefail

MODEL="${1:-kev-4b}"
KEV_COMMIT="557598fced1dada75dfbf36ed144dce309ac6ceb"   # pinned 2026-09-23; weights updated 2026-09-21
if [ -d /scratch/gilbreth ]; then
  KEV_REPO="${KEV_REPO:-/scratch/gilbreth/$USER/repos/kev}"
  export HF_HOME="${HF_HOME:-/scratch/gilbreth/$USER/hf_cache}"
else
  KEV_REPO="${KEV_REPO:-$HOME/kev}"
fi
KEV_PORT="${KEV_PORT:-8009}"
export KEV_PREFIX_CACHE="${KEV_PREFIX_CACHE:-0}"

HEAD="$(git -C "$KEV_REPO" rev-parse HEAD)"
if [ "$HEAD" != "$KEV_COMMIT" ]; then
  echo "!! $KEV_REPO is at $HEAD, not the pinned $KEV_COMMIT — results would not be comparable." >&2
  echo "   git -C $KEV_REPO checkout $KEV_COMMIT   (or update KEV_COMMIT here deliberately)" >&2
  exit 1
fi

echo "==> Kev $MODEL on 127.0.0.1:$KEV_PORT (KEV_PREFIX_CACHE=$KEV_PREFIX_CACHE, commit ${KEV_COMMIT:0:7})"
cd "$KEV_REPO"
exec uv run --frozen --extra serve python -m kev.serve --run "jaredpalmer/$MODEL" --port "$KEV_PORT"
