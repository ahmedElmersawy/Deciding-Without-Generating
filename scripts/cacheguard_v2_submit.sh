#!/bin/bash
# Re-run every cache-guard decider with the query-only question on the corrected labels
# (DECISIONS.md 2026-10-07; handoff #8). Submits, from the repo root on Gilbreth:
#   - API deciders (Jev x5 test + x5 dev, GPT-OSS-20B x5, GPT-5.6 x3), one job per dataset
#   - Kev-4B x5 and Qwen3-8B x5 (local, A100, energy measured), one job each per dataset
#   - the floor classifier, retrained on the corrected dev labels (all three datasets)
#   - one analysis job that waits for all of them: per-dataset tables, paired CIs, figures 15-16
# The old runs are archived in results/replay/cacheguard-<dataset>/v1-answer-question/ and are not
# read, so every job starts fresh. Re-running this script resumes: finished calls are kept.
#
# Usage: bash scripts/cacheguard_v2_submit.sh            (all three datasets)
#        DATASETS="lmarena" bash scripts/cacheguard_v2_submit.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATASETS:=lmarena searchqueries gsmplus}" "${LOCAL_TIME:=08:00:00}"
mkdir -p results/logs
jobs=()
submit() { local id; id=$(sbatch --parsable "$@"); jobs+=("$id"); echo "  submitted $id: $*"; }

for d in $DATASETS; do
  states="results/states/cacheguard-$d.jsonl" run="results/replay/cacheguard-$d"
  echo "==> $d"
  submit --export=ALL,DATASET="$d" scripts/cacheguard_api.slurm
  submit --time="$LOCAL_TIME" --export=ALL,KEV_MODEL=kev-4b,STATES="$states",RUN="$run",EXTRA_ARGS="--task cacheguard --split test" \
    scripts/kev_replay.slurm
  submit --time="$LOCAL_TIME" --export=ALL,STATES="$states",RUN="$run",EXTRA_ARGS="--task cacheguard --split test" \
    scripts/llm_local_replay.slurm
done
echo "==> floor (retrained on corrected dev labels)"
submit scripts/cacheguard_floor.slurm

dep=$(IFS=:; echo "${jobs[*]}")
echo "==> analysis after all of: $dep"
sbatch --dependency=afterany:"$dep" --job-name=dwg-cacheguard-v2-analysis --account=davisjam \
  --partition=a100-80gb --constraint=a100-80gb --gres=gpu:1 --cpus-per-task=2 --mem=16G --time=00:30:00 \
  --output=results/logs/%x-%j.out --wrap "set -e; source scripts/env.sh; \
  for d in $DATASETS; do python scripts/analyze_cacheguard.py results/replay/cacheguard-\$d; done; \
  python scripts/compare_cacheguard.py; python scripts/make_cacheguard_figures.py"
echo "Done. Watch with: squeue -u \$USER ; logs in results/logs/"
