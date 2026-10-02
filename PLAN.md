# PLAN.md: agent-control benchmark, split into two parallel tracks

Written 2026-09-23. Decisions and their reasons go in `DECISIONS.md`; this file says **who does what next**.
When a step is done, tick it here and push.

## The experiment in one table

Every arm runs on the same tau2 tasks, with the same user simulator and the same generator model **G** doing the execution.

| Arm | Decides | Executes | Answers | Owner |
|---|---|---|---|---|
| **0** | each decider, on saved states (**nothing is executed**) | — | Decision quality and decision cost only | both |
| **A** | Jev (API) | G | the system under test, inside a real agent loop | laptop |
| **B** | G itself, as a constrained choice call | G | A − B = the decision-cost difference | laptop |
| **C** | G, in the same call as execution | (same call) | the usual production setup; the honest baseline | laptop |
| **D** | a small LLM | G | the "light decider, strong executor" pattern (AgentFlux, TinyAgent) | laptop (API) / Gilbreth (local Qwen3) |
| **E** | Kev, open weights, run locally | G | model-only latency and energy, with no API in the path | Gilbreth |

Done so far: arm 0 pilot on the **mock** domain with Jev, gpt-oss-20b and Kev-0.8B (`results/replay/mock-pilot/`).
Arm A works on one task (`scripts/tau2_vertical_slice.py`).

---

## Step 0: unblock parallel work (laptop, before Gilbreth starts adding results)

- [x] **U0. One calls file per decider** (done 2026-09-23). A run is now `meta.json` (run-level, written once), plus a
  `calls-<decider>.jsonl` and a `meta-<decider>.json` for each decider (`src/dwg/runfiles.py`). `mock-pilot` has been migrated;
  its numbers are unchanged. Resuming keeps earlier run records under `previous_runs`.
  *Why:* both machines used to append to one `calls.jsonl` and rewrite one `meta.json`, so any parallel push conflicted.

---

## Track G: Gilbreth (GPU, clean energy)

Setup (once): `git pull`; the `dwg` env from `setup.sh` already exists.
Clone Kev to `/scratch/gilbreth/$USER/repos/kev`, `git checkout 557598f`, then `uv sync --frozen --extra serve`
(Kev needs its own env: it pins `torch<2.9`).

- [x] **G1. Kev-4B and Kev-9B on the mock pilot** (arm 0 / E; done 2026-09-23: 325 calls each on the A100, `validate()` passed, 18.3 / 24.4 J per decision). One job per size:
  ```
  sbatch --export=ALL,KEV_MODEL=kev-4b,STATES=results/states/mock-pilot.jsonl,RUN=results/replay/mock-pilot scripts/kev_replay.slurm
  ```
  Check in the job log that `validate()` **passed** on the A100 (no `!! GPU energy not measured`). If it failed, stop and report:
  the laptop GPU's counter was unusable (DECISIONS.md, 2026-09-23). Push the new calls/meta files.
  *Answers:* is any Kev size accurate enough to stand in for Jev? The laptop's 0.8B scored 0.35 vs Jev's 0.77.
- [x] **G2. Compute-node network check** (done 2026-09-25 from existing evidence: the mock cascade job made 325 OpenRouter calls from compute node `gilbreth-k043`; DECISIONS.md) (CHECKS.md #1).
  *Why:* arm E inside a real agent loop needs the API filler model G to be reachable from the compute node.
  If it's blocked, arm E stays decision-only (arm 0), or G has to be local too (G3).
- [x] **G3. A local LLM decider on the same A100** (arm D-local; mock pilot done 2026-09-25 with `scripts/llm_local_replay.slurm`): serve Qwen3-8B with vLLM (`scripts/serve_qwen3.slurm`, needs a small
  `LLMChoiceDecider` hook for a local `api_base`, which the laptop track adds in U4). Replay the same states with energy.
  *Answers the core energy claim:* a System-One-style decider (Kev) vs. a generative LLM decider, **same GPU, both local, no API**.
- [x] **G4. Repeat G1 + G3 on the airline states** (done 2026-09-25: Kev-4B, Kev-9B, Qwen3-8B, all 5,380 calls each, with energy; Kev-0.8B added 2026-09-26).

## Track L: laptop (API, via OpenRouter)

- [x] **U1. Fix the accuracy labels.** (done 2026-09-25: `src/dwg/labels.py`; lenient also accepts a READ lookup before a WRITE reference, since mock gold actions list only writes; DECISIONS.md) Report two accuracies. **Strict:** matches the reference action.
  **Lenient:** reference, or a read-only lookup (`get_*`/`find_*`) that the task's gold actions allow.
  *Why:* the pilot's largest "error" for both Jev and the LLM was a valid `get_users` before `create_task`.
- [x] **U2. Airline states** (done 2026-09-25: 50 tasks × 3 episodes, reference agent `openrouter/openai/gpt-5.6`, 1,076 reward=1 states in `results/states/airline.jsonl`) with the real ceiling model as the reference agent.
  Estimate $ with a 5-task dry run first. Push `results/states/airline-*.jsonl` for G4.
- [x] **U3. Arm 0 on airline:** (done 2026-10-02: GPT-5.6-sol 0.885, GPT-OSS-20B completed; DECISIONS.md) Jev, the frontier LLM and a small API LLM (arm D-API), 5 repeats each.
  Frontier = `openrouter/openai/gpt-5.6-sol` with `--provider-sort price` (DECISIONS.md 2026-10-01). After it lands: offline
  Jev→GPT-5.6 cascade sweep to pick the threshold, then the live `--deciders cascade` run (fast stage = Jev by default).
- [ ] **U4. In-loop harness, arms A–D.** (harness built 2026-09-26: `src/dwg/decider_tau2_agent.py`, `scripts/run_inloop.py`, `scripts/analyze_inloop.py`; free local run `scripts/inloop_local.slurm` with G = user = Qwen3-8B; airline B/C/E × 5 trials done 2026-09-26: reward B 0.308, C 0.196, E 0.048, see DECISIONS.md; paid frontier-G runs and arms A/D wait on credit) Generalize `JevTau2Agent` into a `DeciderTau2Agent` that works with any decider;
  arm C is tau2's own `LLMAgent`. Script `run_inloop.py`: arms × tasks × ≥5 trials. For each episode, log reward plus decision vs. execution
  latency, $ and tokens. Report pass^k (tau2's metric), reward with 95% CI, $ per successful task, and the decision share of cost.
- [ ] **U5. Paper tables and figures** from arms 0 and A–E. State the framing plainly: Kev is not Jev, and the laptop runs have no energy data.

## Order and hand-offs

```
U0 ──► G1 ──► G3 ──────────────► G4
 │                                ▲
 └──► U1 ──► U2 ──► U3 ───────────┘ (airline states)
              └──► U4 ──► U5
G2 (anytime, early): decides whether arm E can run inside the agent loop
```

## Rules both tracks follow

- Every decider gets **≥5 repeats per state** (arm 0) or **≥5 trials per task** (in the loop). Report mean with 95% CI, median, p95 and outliers.
- `results/states/` and `results/replay/` are in git; `results/logs/` is not. **Only add your own deciders' files**
  (`calls-<decider>.jsonl`, `meta-<decider>.json`). `report/` is derived: after pulling, rerun `analyze_decisions.py`.
  Figures are byte-reproducible, so a conflict in `report/` means the data differed. Resolve it by regenerating, never by hand-merging. **Never commit GAIA text**:
  any GAIA-derived path must contain "gaia" so it stays ignored (CHECKS.md #5).
- Pinned: tau2-bench v1.0.1 (`fc0055d`), Kev `557598f`, litellm 1.82.6 (hash-checked). Change a pin only with a `DECISIONS.md` row.
- Kev runs with prefix cache **off** (`serve_kev.sh` default). Energy numbers only count if `validate()` passed.
