#!/bin/bash
# Arm E on Gilbreth: replay saved decision states through LOCAL Kev, one model size per job,
# measuring latency (server + client) and GPU energy. Energy is whole-GPU, so the job must own
# its allocated GPU exclusively — but NOT the whole node: `--exclusive` reserves every GRES on
# the node (found 2026-09-23 live: a 2-GPU node handed both GPUs to a job that asked for 1,
# burning 2 of the account's 3-GPU group cap and starving a labmate's job). `--gres=gpu:1` alone
# already gives this job sole ownership of its one allocated GPU via SLURM's cgroup isolation,
# which is all the energy counter needs.
# The replay itself makes no API calls (only --deciders kev), so compute-node egress doesn't
# matter here (CHECKS.md #1).
#
# Submit from repo root, one job per size, into the SAME run dir as the Jev/LLM replay so
# analyze_decisions.py compares them side by side:
#   sbatch --mem=32G --export=ALL,KEV_MODEL=kev-4b,STATES=results/states/mock-pilot.jsonl,RUN=results/replay/mock-pilot scripts/kev_replay.slurm
#SBATCH --job-name=dwg-kev-replay
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
: "${KEV_MODEL:=kev-4b}" "${STATES:?set STATES=<states.jsonl>}" "${RUN:?set RUN=<replay run dir>}" "${REPEATS:=5}"
export KEV_PORT="${KEV_PORT:-8009}"

source scripts/env.sh
nvidia-smi --query-gpu=name,driver_version,power.draw,clocks.sm --format=csv   # provenance

scripts/serve_kev.sh "$KEV_MODEL" > "results/logs/kev-server-$SLURM_JOB_ID.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 180); do   # first start downloads weights; allow up to 15 min
  curl -sf "http://127.0.0.1:$KEV_PORT/v1/models" > /dev/null && break
  kill -0 $SERVER_PID 2>/dev/null || { echo "!! Kev server exited; see results/logs/kev-server-$SLURM_JOB_ID.log" >&2; exit 1; }
  sleep 5
done

# workers=1: calls are serialized for energy anyway; a single stream also gives the
# latency-oriented (not throughput-batched) number, which is what an agent loop sees.
python scripts/replay_decisions.py --states "$STATES" --out "$RUN" --deciders kev \
  --kev-name "$KEV_MODEL" --repeats "$REPEATS" --workers 1
python scripts/analyze_decisions.py "$RUN"
