#!/bin/bash
# PLAN.md CG3: cross-encoder baseline scores for every cache-guard stream row (dev + test), on one
# A100. No API cost. Submit from repo root: sbatch scripts/cacheguard_crossencoder.slurm
#SBATCH --job-name=dwg-cacheguard-xenc
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
  python scripts/cacheguard_crossencoder.py --states "results/states/cacheguard-$d.jsonl" --out "results/replay/cacheguard-$d"
done
