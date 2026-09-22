#!/bin/bash
# GPU-ONLY job: serves Qwen3 via vLLM's OpenAI-compatible server. No API/rollout work here.
# Rollout jobs (run_rollouts.slurm) connect to it over the network; cancel this job when done.
#SBATCH --job-name=dwg-serve-qwen3
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
MODEL="${MODEL:-Qwen/Qwen3-8B}"   # or Qwen/Qwen3-14B (needs the 80 GB card; see CHECKS.md #6)
PORT="${PORT:-8000}"
source scripts/env.sh
echo "serving $MODEL on $(hostname):$PORT" | tee results/logs/serve_endpoint.txt
echo "http://$(hostname):$PORT/v1" >> results/logs/serve_endpoint.txt
# TODO: VERIFY vLLM flags against the pinned vLLM version (--max-model-len, --gpu-memory-utilization)
exec python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --port "$PORT" --host 0.0.0.0 \
  --max-model-len 8192 --gpu-memory-utilization 0.90 --seed 0
