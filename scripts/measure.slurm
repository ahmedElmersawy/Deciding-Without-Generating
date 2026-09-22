#!/bin/bash
# CLEAN latency/energy measurement of LOCAL deciders (Qwen3, classifier). GPU-bound only:
# --exclusive so no co-tenant perturbs latency or GPU power draw. No API calls in this job.
#SBATCH --job-name=dwg-measure
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --exclusive
#SBATCH --time=02:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
source scripts/env.sh
nvidia-smi --query-gpu=name,driver_version,power.draw,clocks.sm --format=csv   # provenance
python -m dwg.experiments.exp_router       --config configs/router.yaml       --measure-energy
python -m dwg.experiments.exp_cache_guard  --config configs/cache_guard.yaml  --measure-energy
