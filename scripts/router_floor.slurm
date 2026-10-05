#!/bin/bash
# PLAN.md R3: floor router (fine-tuned on the RouterBench train split) scores dev + test, on one
# A100. No API cost. Submit from repo root: sbatch scripts/cacheguard_crossencoder.slurm
#SBATCH --job-name=dwg-router-floor
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
source scripts/env.sh
python scripts/router_floor.py --out results/replay/router-routerbench
