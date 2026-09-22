#!/bin/bash
# CPU-ONLY orchestration: agent rollouts, Jev/frontier API calls. NEVER holds a GPU.
# Local-model decisions go to the vLLM endpoint from serve_qwen3.slurm (results/logs/serve_endpoint.txt).
# Needs outbound HTTPS from compute nodes -> run scripts/check_connectivity.py in this job class first.
#SBATCH --job-name=dwg-rollouts
#SBATCH --account=davisjam
#SBATCH --partition=cpu               # TODO: confirm CPU partition name (`sinfo -s`)
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=results/logs/%x-%j.out
set -euo pipefail
mkdir -p results/logs
source scripts/env.sh
# Uncomment if compute nodes lack egress (ask RCAC for the approved proxy; do not guess a host):
# export HTTPS_PROXY=http://<proxy-host>:<port>; export HTTP_PROXY=$HTTPS_PROXY
set -a; source .env; set +a          # keys from env only; .env is git-ignored
python scripts/check_connectivity.py || echo "WARNING: some endpoints unreachable; API deciders will be skipped"
python -m dwg.experiments.exp_agent_control --config configs/agent_control.yaml
