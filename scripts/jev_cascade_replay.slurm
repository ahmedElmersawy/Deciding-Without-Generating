#!/bin/bash
# Arm 0 cascade, Jev fast stage: replay saved decision states through a LIVE confidence-gated
# cascade — Jev (OpenRouter API) decides first; below --cascade-threshold, escalates to
# GPT-5.6-sol. Both stages are API calls on OPENROUTER_API_KEY from .env, so no model server
# and no GPU work: the GPU is only requested because every Gilbreth partition is a GPU one
# (one A100-80GB: davisjam's normal-QoS GPU cap is 0 for every other card type). Threshold
# 0.65 is the held-out pick from the simulated sweep (DECISIONS.md 2026-10-02). Runs on the cluster rather than the laptop so a sleeping laptop
# can't interrupt it; an interrupted run resumes (re-submit, only missing calls are made).
#
# Submit from repo root, into the SAME run dir as the rest of the airline replay:
#   sbatch --export=ALL,STATES=results/states/airline.jsonl,RUN=results/replay/airline \
#       scripts/jev_cascade_replay.slurm
#SBATCH --job-name=dwg-jev-cascade
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=03:00:00
#SBATCH --output=results/logs/%x-%j.out
# (3 h: ~5,380 Jev calls at ~0.2 s plus ~17% escalated to GPT-5.6 at ~4 s, over 4 workers ≈ 30 min;
#  slack for GPT-5.6 tail latency.)
set -euo pipefail
mkdir -p results/logs
: "${STATES:?set STATES=<states.jsonl>}" "${RUN:?set RUN=<replay run dir>}"
: "${THRESHOLD:=0.65}" "${REPEATS:=5}" "${MAX_USD:=10}" "${EST_COST:=8.4e-4}"
: "${LLM_MODEL:=openrouter/openai/gpt-5.6-sol}"

source scripts/env.sh

python3 scripts/check_connectivity.py || { echo "!! OpenRouter unreachable from this compute node; aborting before any cascade calls" >&2; exit 1; }

# EST_COST: the simulated Jev -> GPT-5.6 $/decision at t=0.65 (handoff #5); the spending guard
# stops at MAX_USD and on the first 402.
python scripts/replay_decisions.py --states "$STATES" --out "$RUN" --deciders cascade \
  --cascade-fast jev --cascade-threshold "$THRESHOLD" --llm-model "$LLM_MODEL" --provider-sort price \
  --est-cost-per-call "$EST_COST" --max-usd "$MAX_USD" --repeats "$REPEATS" --workers 4
python scripts/analyze_decisions.py "$RUN"
