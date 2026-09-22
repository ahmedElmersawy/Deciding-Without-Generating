#!/bin/bash
# Confirms the env setup.sh built actually works on a GPU node, before any harness code
# is written on top of it. Run this once after setup.sh and check its output.
#SBATCH --job-name=dwg-verify-env
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs

source scripts/env.sh
nvidia-smi --query-gpu=name,driver_version,power.draw,clocks.sm --format=csv  # provenance
python scripts/verify_env.py
