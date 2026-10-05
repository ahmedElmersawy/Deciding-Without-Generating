#!/bin/bash
# PLAN.md CG3: floor classifier: fine-tune on each dataset's dev split, score its test split, on one
# A100. No API cost. Submit from repo root: sbatch scripts/cacheguard_crossencoder.slurm
#SBATCH --job-name=dwg-cacheguard-floor
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
source scripts/env.sh
for d in lmarena searchqueries gsmplus; do
  python scripts/cacheguard_floor.py --states "results/states/cacheguard-$d.jsonl" --out "results/replay/cacheguard-$d"
done
