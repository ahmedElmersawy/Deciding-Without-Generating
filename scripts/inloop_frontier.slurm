#!/bin/bash
# PLAN.md U4 with a frontier G: in-loop episodes where G (executes in every arm, decides in B and
# C) and the user simulator are GPT-5.6-sol on OpenRouter (DECISIONS.md 2026-10-01). Arm A's
# decider is Jev (API), D's is GPT-OSS-20B (API), E's is Kev-4B served on this node's A100; the
# Kev server is only started when E is in ARMS.
#
# - OpenRouter price routing for G/user and arm D (`provider.sort=price`), as in U3: default
#   routing billed GPT-OSS at 2.7-3.4x its listed price (DECISIONS.md 2026-09-25).
# - Spending guard: MAX_USD caps the run; EST_COST seeds the estimate until an arm has 5
#   finished episodes in OUT, after which run_inloop.py uses that arm's own average.
# - Resumes: re-submitting with the same OUT runs only the missing episodes.
#
# Submit from repo root (pilot: 4 tasks x 1 trial x 5 arms):
#   sbatch --export=ALL,TASK_IDS="0 12 25 38",TRIALS=1 scripts/inloop_frontier.slurm
#SBATCH --job-name=dwg-inloop-frontier
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
: "${DOMAIN:=airline}" "${TRIALS:=5}" "${ARMS:=A B C D E}" "${WORKERS:=4}" "${TASK_IDS:=}"
: "${G_MODEL:=openrouter/openai/gpt-5.6-sol}" "${MAX_USD:=8}" "${EST_COST:=0.12}"
: "${OUT:=results/inloop/$DOMAIN-frontier-gpt-5.6-sol}"
export KEV_PORT="${KEV_PORT:-8009}"

source scripts/env.sh
python3 scripts/check_connectivity.py || { echo "!! OpenRouter unreachable from this compute node; aborting before any paid calls" >&2; exit 1; }

if [[ " $ARMS " == *" E "* ]]; then
  nvidia-smi --query-gpu=name,driver_version,power.draw,clocks.sm --format=csv   # provenance
  scripts/serve_kev.sh kev-4b > "results/logs/kev-server-inloop-$SLURM_JOB_ID.log" 2>&1 &
  KEV_PID=$!
  trap 'kill $KEV_PID 2>/dev/null || true' EXIT
  for _ in $(seq 1 180); do
    curl -sf "http://127.0.0.1:$KEV_PORT/v1/models" > /dev/null && break
    kill -0 $KEV_PID 2>/dev/null || { echo "!! Kev exited; see results/logs/kev-server-inloop-$SLURM_JOB_ID.log" >&2; exit 1; }
    sleep 5
  done
fi

PRICE='{"provider": {"sort": "price"}}'
TASK_ARGS=()
[[ -n "$TASK_IDS" ]] && read -ra TASK_ARGS <<< "--task-ids $TASK_IDS"
# shellcheck disable=SC2086
python scripts/run_inloop.py --domain "$DOMAIN" --arms $ARMS --trials "$TRIALS" --workers "$WORKERS" \
  "${TASK_ARGS[@]}" --g-model "$G_MODEL" --g-extra-body "$PRICE" --small-extra-body "$PRICE" \
  --kev-url "http://127.0.0.1:$KEV_PORT" --kev-name kev-4b \
  --max-usd "$MAX_USD" --est-cost-per-episode "$EST_COST" --out "$OUT"
python scripts/analyze_inloop.py "$OUT"
