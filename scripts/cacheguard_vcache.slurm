#!/bin/bash
# PLAN.md CG3: vCache's verified policy over the two vCache streams (file order, up to the last
# sampled query: ~64k LmArena / ~150k SearchQueries prompts). CPU work; the GPU is held only
# because every Gilbreth partition is a GPU one. Uses the separate vCache env (see
# scripts/cacheguard_vcache.py). Submit from repo root: sbatch scripts/cacheguard_vcache.slurm
#SBATCH --job-name=dwg-cacheguard-vcache
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
VPY="/scratch/gilbreth/$USER/dwg-data/vcache_env/bin/python"
for d in lmarena searchqueries; do
  "$VPY" scripts/cacheguard_vcache.py --dataset "$d" --out "results/replay/cacheguard-$d"
done
