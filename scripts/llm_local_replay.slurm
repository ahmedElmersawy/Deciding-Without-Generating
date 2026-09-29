#!/bin/bash
# PLAN.md G3 (arm D-local): replay saved decision states through a LOCAL generative LLM decider
# (Qwen3-8B on vLLM, same A100 type as Kev), measuring latency and GPU energy the same way as
# kev_replay.slurm. Answers the core energy claim: a System-One-style decider (Kev) vs. a
# generative LLM decider, same GPU, both local, no API. Makes no API calls, costs no credits.
#
# Same fairness settings as Kev:
# - prefix caching OFF: replay asks about the same state 5 times, so a prefix cache would make
#   repeats 2-5 nearly free (serve_kev.sh defaults KEV_PREFIX_CACHE=0 for the same reason).
# - one request at a time (--workers 1): energy is whole-GPU and must not overlap calls.
# - tool-call parser `hermes` (Qwen3's format) + --enable-auto-tool-choice: vLLM 0.29 rejects a named
#   tool_choice without a parser, and only loads the parser when auto tool choice is on
#   (vllm/parser/parser_manager.py). Requests still force the one named tool, so 'auto' is unused.
# - thinking OFF (enable_thinking=false): the decision is forced to one `decide_next_action`
#   call; vLLM's structured output for a named tool_choice constrains the reply from the first
#   token, so a <think> block could not be emitted anyway. The template flag makes that explicit.
#
# Submit from repo root, into the SAME run dir as the other deciders:
#   sbatch --export=ALL,STATES=results/states/mock-pilot.jsonl,RUN=results/replay/mock-pilot scripts/llm_local_replay.slurm
#SBATCH --job-name=dwg-llm-local-replay
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
: "${STATES:?set STATES=<states.jsonl>}" "${RUN:?set RUN=<replay run dir>}" "${REPEATS:=5}"
: "${MODEL:=Qwen/Qwen3-8B}" "${LLM_NAME:=llm:local/qwen3-8b}" "${PORT:=8000}"

source scripts/env.sh
nvidia-smi --query-gpu=name,driver_version,power.draw,clocks.sm --format=csv   # provenance

python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --port "$PORT" --host 127.0.0.1 --seed 0 \
  --max-model-len 32768 --gpu-memory-utilization 0.90 --no-enable-prefix-caching --enable-auto-tool-choice --tool-call-parser hermes \
  > "results/logs/vllm-server-$SLURM_JOB_ID.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 240); do   # first start downloads ~16 GB of weights; allow up to 20 min
  curl -sf "http://127.0.0.1:$PORT/v1/models" > /dev/null && break
  kill -0 $SERVER_PID 2>/dev/null || { echo "!! vLLM server exited; see results/logs/vllm-server-$SLURM_JOB_ID.log" >&2; exit 1; }
  sleep 5
done

python scripts/replay_decisions.py --states "$STATES" --out "$RUN" --deciders llm \
  --llm-model "hosted_vllm/$MODEL" --llm-name "$LLM_NAME" --llm-api-base "http://127.0.0.1:$PORT/v1" \
  --llm-extra-body '{"chat_template_kwargs": {"enable_thinking": false}}' \
  --repeats "$REPEATS" --workers 1
python scripts/analyze_decisions.py "$RUN"
