#!/bin/bash
# PLAN.md CG1: build the cache-guard decision streams on one A100 (the GPU is only for embedding
# GSM-Plus with GTE-large-en-v1.5; the vCache sets ship their embeddings). Downloads only the
# needed columns of the vCache benchmarks to $DWG_DATA_DIR (scratch), checks that our GTE
# embeddings match vCache's stored ones before using them for GSM-Plus, then writes
# results/states/cacheguard-{lmarena,searchqueries,gsmplus}.jsonl (+ .meta.json).
#
# Submit from repo root:
#   sbatch scripts/cacheguard_build.slurm
#SBATCH --job-name=dwg-cacheguard-build
#SBATCH --account=davisjam
#SBATCH --partition=a100-80gb
#SBATCH --constraint=a100-80gb
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
source scripts/env.sh
export DWG_DATA_DIR="${DWG_DATA_DIR:-/scratch/gilbreth/$USER/dwg-data}"

# GSM-Plus is embedded by us; refuse to build it if our embeddings don't reproduce vCache's.
rc=0; python scripts/build_cacheguard_streams.py --dataset lmarena --check-embeddings || rc=$?
if [ "$rc" = 3 ]; then echo "!! our GTE embeddings don't match vCache's stored ones; not building streams" >&2; exit 3; fi
if [ "$rc" != 0 ]; then echo "!! embedding check crashed (exit $rc); see the traceback above" >&2; exit "$rc"; fi
for d in lmarena searchqueries gsmplus; do
  python scripts/build_cacheguard_streams.py --dataset "$d"
done
