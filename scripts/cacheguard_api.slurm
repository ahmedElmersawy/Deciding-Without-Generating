#!/bin/bash
# PLAN.md CG5: the API deciders on one cache-guard dataset, full test split. Jev and GPT-OSS-20B
# x 5 repeats, GPT-5.6-sol x 3 (it is ~90% of the cost), plus Jev x 5 on the dev split (tunes the
# threshold -> Jev cascade's band). API calls only; the GPU is held because every Gilbreth
# partition is a GPU one. Resumes: the pilot's calls (repeat 0 of a 200-query subset) are kept.
# Each decider's $ is estimated from its pilot calls and capped (MAX_*); the first 402 or key-limit
# refusal stops paid calls.
#
# Submit from repo root, one job per dataset:
#   sbatch --export=ALL,DATASET=gsmplus scripts/cacheguard_api.slurm
#SBATCH --job-name=dwg-cacheguard-api
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
: "${DATASET:?set DATASET=lmarena|searchqueries|gsmplus}" "${WORKERS:=6}"
: "${MAX_JEV:=1}" "${MAX_OSS:=2}" "${MAX_GPT56:=14}"
# $/call estimates for the spending guard when the run folder has no call history yet (a fresh run,
# e.g. after the v1 runs were archived): each decider's mean $/call in that dataset's
# v1-answer-question/ run. The query-only prompts are shorter, so these are upper bounds.
case "$DATASET" in
  lmarena)       est_jev=3.5e-5; est_oss=6.1e-5; est_gpt56=1.74e-3 ;;
  searchqueries) est_jev=1.8e-5; est_oss=3.7e-5; est_gpt56=9.0e-4 ;;
  *)             est_jev=2.3e-5; est_oss=5.1e-5; est_gpt56=1.11e-3 ;;
esac
: "${EST_JEV:=$est_jev}" "${EST_OSS:=$est_oss}" "${EST_GPT56:=$est_gpt56}"
source scripts/env.sh
python3 scripts/check_connectivity.py || { echo "!! OpenRouter unreachable; aborting before any paid calls" >&2; exit 1; }

STATES="results/states/cacheguard-$DATASET.jsonl"; RUN="results/replay/cacheguard-$DATASET"
common=(--task cacheguard --states "$STATES" --out "$RUN" --workers "$WORKERS")
python scripts/replay_decisions.py "${common[@]}" --split test --deciders jev --repeats 5 --max-usd "$MAX_JEV" --est-cost-per-call "$EST_JEV"
python scripts/replay_decisions.py "${common[@]}" --split dev --deciders jev --repeats 5 --max-usd "$MAX_JEV" --est-cost-per-call "$EST_JEV"
python scripts/replay_decisions.py "${common[@]}" --split test --deciders llm --llm-model openrouter/openai/gpt-oss-20b \
  --provider-sort price --repeats 5 --max-usd "$MAX_OSS" --est-cost-per-call "$EST_OSS"
python scripts/replay_decisions.py "${common[@]}" --split test --deciders llm --llm-model openrouter/openai/gpt-5.6-sol \
  --provider-sort price --repeats 3 --max-usd "$MAX_GPT56" --est-cost-per-call "$EST_GPT56"
python scripts/analyze_cacheguard.py "$RUN"
