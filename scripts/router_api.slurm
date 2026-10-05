#!/bin/bash
# PLAN.md R5: the API deciders on the router stream's full test split: Jev and GPT-OSS-20B x 5,
# GPT-5.6-sol x 3. API calls only; the GPU is held because every Gilbreth partition is a GPU one.
# Resumes (the R4 pilot's calls are kept); each decider's $ is estimated from its pilot calls and
# capped (MAX_*); the first 402 / key-limit refusal stops paid calls.
# Submit from repo root: sbatch scripts/router_api.slurm
#SBATCH --job-name=dwg-router-api
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
: "${WORKERS:=6}" "${MAX_JEV:=1}" "${MAX_OSS:=3}" "${MAX_GPT56:=15}"
source scripts/env.sh
python3 scripts/check_connectivity.py || { echo "!! OpenRouter unreachable; aborting before any paid calls" >&2; exit 1; }
common=(--task router --states results/states/router-routerbench.jsonl --out results/replay/router-routerbench --split test --workers "$WORKERS")
python scripts/replay_decisions.py "${common[@]}" --deciders jev --repeats 5 --max-usd "$MAX_JEV"
python scripts/replay_decisions.py "${common[@]}" --deciders llm --llm-model openrouter/openai/gpt-oss-20b \
  --provider-sort price --repeats 5 --max-usd "$MAX_OSS"
python scripts/replay_decisions.py "${common[@]}" --deciders llm --llm-model openrouter/openai/gpt-5.6-sol \
  --provider-sort price --repeats 3 --max-usd "$MAX_GPT56"
python scripts/analyze_router.py results/replay/router-routerbench
