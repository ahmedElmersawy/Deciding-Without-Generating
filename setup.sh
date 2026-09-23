#!/bin/bash
# Builds the pinned `dwg` conda env on Gilbreth. Run ONCE from a LOGIN node (needs network +
# scratch disk; do not run this inside a compute job). After it finishes, submit
# scripts/verify_env.slurm on a GPU node to confirm the build before writing more code.
#
# Reproduces the exact package set recorded in dwg-working-freeze.txt (CHECKS.md #6/#7):
# python 3.12 (tau2-bench floor; system python is 3.9), CentOS7-compatible libstdc++,
# vLLM 0.29.0 / torch 2.13.0, plus the app-level deps (litellm, smolagents, ...) that
# freeze predates.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

USER_SCRATCH="/scratch/gilbreth/$USER"
DWG_ENV_PREFIX="${DWG_ENV_PREFIX:-$USER_SCRATCH/conda_envs/dwg}"
export CONDA_PKGS_DIRS="$USER_SCRATCH/conda_pkgs"

mkdir -p "$CONDA_PKGS_DIRS" "$USER_SCRATCH/hf_cache" "$USER_SCRATCH/vllm_cache" \
         "$USER_SCRATCH/conda_envs" results/logs

module load conda/2025.09 2>/dev/null || module load anaconda/2025.06-py313

if [ -d "$DWG_ENV_PREFIX" ]; then
  echo "!! $DWG_ENV_PREFIX already exists." >&2
  echo "   For a clean rebuild: conda env remove -p $DWG_ENV_PREFIX" >&2
  exit 1
fi

echo "==> creating conda env at $DWG_ENV_PREFIX (CONDA_PKGS_DIRS=$CONDA_PKGS_DIRS)"
conda env create -p "$DWG_ENV_PREFIX" -f environment.yml

# shellcheck source=scripts/env.sh
source scripts/env.sh

echo "==> installing litellm==1.82.6 from a sha256-verified artifact"
echo "    (1.82.7/1.82.8 shipped a credential-stealing .pth file — CHECKS.md #3)"
LITELLM_WHEEL_SHA256="164a3ef3e19f309e3cabc199bef3d2045212712fefdfa25fc7f75884a5b5b205"
LITELLM_SDIST_SHA256="2aa1c2da21fe940c33613aa447119674a3ad4d2ad5eb064e4d5ce5ee42420136"
LITELLM_DL_DIR="$(mktemp -d)"
trap 'rm -rf "$LITELLM_DL_DIR"' EXIT
pip download --no-deps --dest "$LITELLM_DL_DIR" 'litellm==1.82.6'
LITELLM_ARTIFACT="$(find "$LITELLM_DL_DIR" -maxdepth 1 -type f -print -quit)"
LITELLM_GOT_SHA256="$(sha256sum "$LITELLM_ARTIFACT" | cut -d' ' -f1)"
case "$LITELLM_GOT_SHA256" in
  "$LITELLM_WHEEL_SHA256" | "$LITELLM_SDIST_SHA256")
    echo "    sha256 OK: $LITELLM_GOT_SHA256" ;;
  *)
    echo "!! litellm==1.82.6 artifact sha256 ($LITELLM_GOT_SHA256) does not match the" >&2
    echo "   vendor-audited hash. Expected wheel $LITELLM_WHEEL_SHA256 or" >&2
    echo "   sdist $LITELLM_SDIST_SHA256 (CHECKS.md #3). Aborting — do not install." >&2
    exit 1 ;;
esac
pip install "$LITELLM_ARTIFACT"
rm -rf "$LITELLM_DL_DIR"
trap - EXIT
if find "$CONDA_PREFIX" -name 'litellm_init.pth' 2>/dev/null | grep -q .; then
  echo "!! found litellm_init.pth in $CONDA_PREFIX — this matches the known backdoor" >&2
  echo "   artifact from the 1.82.7/1.82.8 incident. Env is compromised; do not use it." >&2
  exit 1
fi

echo "==> installing the pinned GPU/vLLM stack"
echo "    TODO: VERIFY the cu130 wheel index is live — dwg-working-freeze.txt records a"
echo "    working torch 2.13.0+cu130 (matches Gilbreth's CUDA 13.1 driver, CHECKS.md #6);"
echo "    the original plan text said cu128, this deviates on empirical grounds (see"
echo "    DECISIONS.md). If this 404s, check https://download.pytorch.org/whl for the"
echo "    live index name before falling back to cu128."
pip install --extra-index-url https://download.pytorch.org/whl/cu130 \
  -c constraints-gpu.txt -r requirements-gpu.txt

echo "==> installing the shared app-level deps (frontier/Jev deciders, agent framework, tests)"
pip install -c constraints-gpu.txt -r requirements-common.txt

echo "==> cloning + installing tau2-bench (agent-control decision point; not on PyPI)"
echo "    pinned to the v1.0.1 release tag (DECISIONS.md 2026-09-22) — do not track main,"
echo "    v1.0.1 changed banking_knowledge grading in a way that's not comparable to older runs"
TAU2_REPO_PREFIX="${TAU2_REPO_PREFIX:-$USER_SCRATCH/repos/tau2-bench}"
if [ ! -d "$TAU2_REPO_PREFIX" ]; then
  mkdir -p "$(dirname "$TAU2_REPO_PREFIX")"
  git clone --branch v1.0.1 --depth 1 https://github.com/sierra-research/tau2-bench.git "$TAU2_REPO_PREFIX"
fi
pip install --no-deps "$TAU2_REPO_PREFIX"

echo "==> env ready at $DWG_ENV_PREFIX"
echo "Next: sbatch scripts/verify_env.slurm   (then check results/logs/dwg-verify-env-*.out)"
