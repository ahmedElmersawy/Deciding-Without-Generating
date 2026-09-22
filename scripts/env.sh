#!/bin/bash
# Activates the pinned `dwg` conda env and sets the four exports every job needs.
# SOURCE this (never execute it) from repo root, in every Slurm script and interactively:
#   source scripts/env.sh
#
# The LD_LIBRARY_PATH export is mandatory, not cosmetic: CentOS 7's system libstdc++
# lacks CXXABI_1.3.15, which vLLM's compiled extensions require (CHECKS.md #7).
set -uo pipefail  # no -e: safe to source into scripts that set their own error handling

DWG_ENV_PREFIX="${DWG_ENV_PREFIX:-/scratch/gilbreth/$USER/conda_envs/dwg}"

module load conda/2025.09 2>/dev/null || module load anaconda/2025.06-py313
source activate "$DWG_ENV_PREFIX"

export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
export HF_HOME="/scratch/gilbreth/$USER/hf_cache"
export VLLM_CACHE_ROOT="/scratch/gilbreth/$USER/vllm_cache"
export PYTHONNOUSERSITE=1
