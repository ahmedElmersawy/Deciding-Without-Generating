#!/bin/bash
# PLAN.md U4, fully local: in-loop episodes (arms B, C, E) with G = user simulator = Qwen3-8B on
# vLLM and Kev-4B as arm E's decider, both on one A100. Makes no API calls and costs no
# credits: it validates the in-loop harness end to end and gives a local-G data point. The
# frontier-G runs (arms A-D with G on OpenRouter) use the same script, run_inloop.py.
#
# - thinking OFF for G and the user (enable_thinking=false): same setting as the arm-0 Qwen3
#   decider, and it keeps <think> blocks out of the conversation tau2 grades.
# - prefix caching ON here (vLLM default), unlike replay: an agent loop re-sends a growing
#   prefix every turn, which is exactly the regime a production deployment caches.
# - vLLM gets 60% of the GPU so Kev-4B (bf16, ~10 GB + activations) fits beside it.
#
# Submit from repo root:
#   sbatch scripts/inloop_local.slurm
#   sbatch --export=ALL,DOMAIN=airline,TRIALS=5,ARMS="B C E" scripts/inloop_local.slurm
#SBATCH --job-name=dwg-inloop-local
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
: "${DOMAIN:=mock}" "${TRIALS:=5}" "${ARMS:=B C E}" "${WORKERS:=4}"
: "${MODEL:=Qwen/Qwen3-8B}" "${PORT:=8000}"
: "${OUT:=results/inloop/$DOMAIN-local-qwen3-8b}"
export KEV_PORT="${KEV_PORT:-8009}"

source scripts/env.sh
nvidia-smi --query-gpu=name,driver_version,power.draw,clocks.sm --format=csv   # provenance

python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --port "$PORT" --host 127.0.0.1 --seed 0 \
  --max-model-len 32768 --gpu-memory-utilization 0.60 --enable-auto-tool-choice --tool-call-parser hermes \
  > "results/logs/vllm-server-$SLURM_JOB_ID.log" 2>&1 &
VLLM_PID=$!
scripts/serve_kev.sh kev-4b > "results/logs/kev-server-inloop-$SLURM_JOB_ID.log" 2>&1 &
KEV_PID=$!
trap 'kill $VLLM_PID $KEV_PID 2>/dev/null || true' EXIT

for _ in $(seq 1 240); do
  curl -sf "http://127.0.0.1:$PORT/v1/models" > /dev/null && curl -sf "http://127.0.0.1:$KEV_PORT/v1/models" > /dev/null && break
  kill -0 $VLLM_PID 2>/dev/null || { echo "!! vLLM exited; see results/logs/vllm-server-$SLURM_JOB_ID.log" >&2; exit 1; }
  kill -0 $KEV_PID 2>/dev/null || { echo "!! Kev exited; see results/logs/kev-server-inloop-$SLURM_JOB_ID.log" >&2; exit 1; }
  sleep 5
done

NO_THINK='{"chat_template_kwargs": {"enable_thinking": false}}'
# shellcheck disable=SC2086
python scripts/run_inloop.py --domain "$DOMAIN" --arms $ARMS --trials "$TRIALS" --workers "$WORKERS" \
  --g-model "hosted_vllm/$MODEL" --g-api-base "http://127.0.0.1:$PORT/v1" --g-extra-body "$NO_THINK" \
  --kev-url "http://127.0.0.1:$KEV_PORT" --kev-name kev-4b --out "$OUT"
python scripts/analyze_inloop.py "$OUT"
