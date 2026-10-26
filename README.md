# Deciding Without Generating

Code for *Deciding Without Generating: When Does a Standalone Decision Model Pay Off in LLM Systems?*

We compare standalone decision models (Jev, hosted; Kev, open weights) with LLM deciders and
non-LLM baselines at three decision points: agent control (tau2-bench airline), the cache
guard (vCache LMArena / SearchQueries, GSM-Plus), and the router (RouterBench).

## Layout

| Path | Contents |
|---|---|
| `src/dwg/` | Deciders (`jev.py`, `jev_model.py`, `decisions.py`), task logic (`cacheguard.py`, `router.py`, `labels.py`), tau2 agents, statistics (`stats.py`), energy metering, cost accounting |
| `scripts/` | Data building, replay, in-loop runs, analysis and figures (see below); `*.slurm` are the cluster jobs |
| `tests/` | Unit tests (`pytest`) |
| `results/` | Run outputs; not in this repository (see **Results**) |

## Setup

Python 3.12. For API deciders only (laptop):

```bash
pip install -r requirements-common.txt -r requirements-local.txt
cp .env.example .env    # set OPENROUTER_API_KEY (Jev and every hosted LLM go through OpenRouter)
```

For local models and energy measurement (Linux + NVIDIA GPU, conda), `setup.sh` builds the
pinned environment (`environment.yml`, `constraints-gpu.txt`, `requirements-gpu.txt`) and
`scripts/env.sh` activates it. Set two variables in `.env` first (see `.env.example`):

```bash
DWG_SCRATCH=/path/to/large/disk   # conda env, HF cache, datasets, tau2-bench checkout
SBATCH_ACCOUNT=<your account>     # Slurm account
```

`setup.sh`, `scripts/env.sh` (sourced by every job) and the submit scripts load `.env`. A plain
`sbatch scripts/<job>.slurm` reads the account before any of our code runs, so for that pass
`-A <your account>` or export `SBATCH_ACCOUNT` in your shell.

tau2-bench is installed from a checkout at `$DWG_SCRATCH/repos/tau2-bench` (override with
`TAU2_REPO_PREFIX`). Kev runs in its own environment and is served over HTTP by
`scripts/serve_kev.sh`, which pins the Kev commit. The vCache baseline also needs its own
environment (see `scripts/cacheguard_vcache.py`). Slurm partitions in `scripts/*.slurm` are
for our cluster; adjust them to yours.

## Reproducing the paper

Every command reads and writes under `results/`. Analysis and figure scripts only read run
outputs, so with the released results they run without API keys or GPUs.

**Agent control (Section 4).**

```bash
python3 scripts/collect_decision_states.py --domain airline        # tau2 episodes -> results/states/airline.jsonl
python3 scripts/replay_decisions.py --states results/states/airline.jsonl --repeats 5 --out results/replay/airline
python3 scripts/analyze_decisions.py results/replay/airline         # Table (decision-only replay)
python3 scripts/post_experiment_analysis.py results/replay/airline  # significance, cascade simulation
python3 scripts/make_paper_figures.py results/replay/airline        # Figs: accuracy vs latency, accuracy vs energy
python3 scripts/make_cascade_figure.py results/replay/airline       # Fig: cascade threshold sweep
python3 scripts/run_inloop.py --domain airline --arms A B C D E    # in-loop; exact jobs: scripts/inloop_{frontier,local}.slurm
python3 scripts/analyze_inloop.py results/inloop/airline-frontier-gpt-5.6-sol    # Table (in-loop)
python3 scripts/make_inloop_figures.py results/inloop/airline-frontier-gpt-5.6-sol  # Figs: cost vs reward, pass^k
```

**Cache guard (Section 5).**

```bash
python3 scripts/build_cacheguard_streams.py --dataset {lmarena,searchqueries,gsmplus}
python3 scripts/apply_cacheguard_label_corrections.py      # corrected labels (results/label-corrections/)
python3 scripts/replay_decisions.py --task cacheguard --states results/states/cacheguard-<dataset>.jsonl \
    --split test --deciders jev llm --out results/replay/cacheguard-<dataset>
python3 scripts/cacheguard_crossencoder.py; python3 scripts/cacheguard_floor.py; python3 scripts/cacheguard_vcache.py   # baselines
python3 scripts/cacheguard_regen_cost.py                  # cost of a regeneration
python3 scripts/analyze_cacheguard.py results/replay/cacheguard-<dataset>   # Table (cache guard)
python3 scripts/compare_cacheguard.py                     # paired confidence intervals
python3 scripts/make_cacheguard_figures.py                # Fig: reuse vs wrong reuse; appendix accuracy figure
```

**Router (Section 6).**

```bash
python3 scripts/build_router_streams.py
python3 scripts/router_floor.py                           # trained baseline
python3 scripts/replay_decisions.py --task router --states results/states/router-routerbench.jsonl \
    --out results/replay/router-routerbench   # exact jobs: scripts/router_api.slurm
python3 scripts/analyze_router.py results/replay/router-routerbench   # Table (router) and quality-vs-cost figure
```

Each script's docstring gives its full options; the `scripts/*.slurm` files are the exact jobs
we ran (deciders, repeats, seeds).

## Results

The run outputs (decision states, every decider call, in-loop episodes, label corrections)
are released separately: https://figshare.com/s/97da8537a6a4e8758f1b Unpack them as `results/` in the repository root.
Decision states contain text from the source datasets, which keep their own terms:

| Dataset | Source | License |
|---|---|---|
| tau2-bench airline | sierra-research/tau2-bench | MIT |
| LMArena | vCache/SemBenchmarkLmArena (prompts from LMArena's human-preference data, CC BY 4.0) | Apache-2.0 |
| SearchQueries | vCache/SemBenchmarkSearchQueries (queries from MS MARCO ORCAS) | Apache-2.0; ORCAS is for non-commercial research use only |
| GSM-Plus | qintongli/GSM-Plus | CC BY-SA 4.0 (files derived from it are shared under the same license) |
| RouterBench | withmartian/routerbench | no license stated for the data; prompts come from public benchmarks (MMLU, GSM8K, MBPP, ...) |

LLM outputs in the run files are subject to their providers' terms. Our own code is MIT (`LICENSE`).

## Tests

```bash
pytest
```

Tests of the tau2 agents need tau2-bench and smolagents installed.
