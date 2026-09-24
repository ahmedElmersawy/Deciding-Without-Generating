#!/bin/bash
# Arm E+cascade: replay saved decision states through a LIVE confidence-gated cascade —
# Kev-4B decides first; below --cascade-threshold, escalates to a hosted LLM (default
# GPT-OSS-20B via OpenRouter). Needs both a local Kev-4B server (GPU) AND outbound network
# from the compute node (confirmed reachable, G2/CHECKS.md #1) for the escalation calls.
#
# No --exclusive (see kev_replay.slurm's note: it silently grabs every GPU on a multi-GPU
# node and blows through the account's group GPU cap) and no NVML energy metering here —
# CascadeDecider intentionally doesn't live-meter GPU energy, since a window spanning a slow
# network escalation call would count GPU idle power as decision energy. Kev-4B's own
# already-validated energy/decision figure is reused post-hoc in analysis instead.
#
# Submit from repo root, into the SAME run dir as the rest of the mock-pilot replay:
#   sbatch --mem=32G --export=ALL,STATES=results/states/mock-pilot.jsonl,RUN=results/replay/mock-pilot,THRESHOLD=0.9 \
#       scripts/kev_cascade_replay.slurm
#SBATCH --job-name=dwg-cascade-replay
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
: "${STATES:?set STATES=<states.jsonl>}" "${RUN:?set RUN=<replay run dir>}" "${THRESHOLD:=0.9}" "${REPEATS:=5}"
export KEV_PORT="${KEV_PORT:-8009}"

source scripts/env.sh
nvidia-smi --query-gpu=name,driver_version,power.draw,clocks.sm --format=csv

scripts/serve_kev.sh kev-4b > "results/logs/kev-server-cascade-$SLURM_JOB_ID.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 180); do
  curl -sf "http://127.0.0.1:$KEV_PORT/v1/models" > /dev/null && break
  kill -0 $SERVER_PID 2>/dev/null || { echo "!! Kev server exited; see results/logs/kev-server-cascade-$SLURM_JOB_ID.log" >&2; exit 1; }
  sleep 5
done

# Network check before spending API calls: escalation needs OpenRouter reachable from here.
python3 scripts/check_connectivity.py || { echo "!! OpenRouter unreachable from this compute node; aborting before any cascade calls" >&2; exit 1; }

# workers=4 (not 1): no NVML lock to serialize on here, escalation is a normal API call.
python scripts/replay_decisions.py --states "$STATES" --out "$RUN" --deciders cascade \
  --kev-name kev-4b --cascade-threshold "$THRESHOLD" --repeats "$REPEATS" --workers 4
python scripts/analyze_decisions.py "$RUN"
