# CHECKS.md — Phase 1 report (2026-09-21)

Legend: **PASS** verified with evidence · **UNCERTAIN** partially verified · **FAIL** blocked · **ACTION-ON-USER** needs you on the cluster.

| # | Check | Status |
|---|---|---|
| 1 | Node egress / API reachability | **PASS (login node)** / **ACTION-ON-USER (compute node)** — top blocking risk |
| 2 | Jev API reality-check | **PASS** (schema) / **UNCERTAIN** (context limit, calibration, rate limits, access) |
| 3 | LiteLLM pin | **PASS**, with a **design conflict** (see below) |
| 4 | smolagents / ToolCallingAgent / Model interface | **PASS** |
| 5 | tau2-bench & GAIA | **PASS** with constraints (py3.12, gated GAIA) |
| 6 | GPU sizing & serving | **PASS** (sizing) / **UNCERTAIN** (vLLM on this CUDA stack) |
| 7 | Slurm templates | **PASS** (written; two partition/account TODOs) |
| 8 | Energy measurement | **PASS** (`nvidia-smi` power query works) |

## Blockers to decide before building calling code

1. **Compute-node egress is untested.** Login node reaches everything (below). Run the probe inside a job (instructions in #1). If it fails, every API decider (Jev, frontier) and GAIA/tau2 user-simulator calls need a proxy or must run from the login node/off-cluster.
2. **LiteLLM pin vs. tau2-bench vs. current models.** tau2-bench 1.0.1 requires `litellm>=1.80.15,<1.82.7` and `python>=3.12`. The vendor-audited clean ceiling is 1.82.6 (1.82.7/1.82.8 were the malicious releases). 1.82.6 dates from 2026-03-22, so its bundled price map will likely **lack** claude-opus-5 / gpt-5.6 / current Gemini entries (unverified; check at install). Proposed: one env, litellm==1.82.6, plus our own price table in `configs/deciders.yaml` for $ cost. Alternative: separate env for tau2 and newer litellm (1.83.x+) for everything else.
3. **Jev is not chat-shaped.** It answers typed questions (choice/score/noul) over a `state` string. A smolagents `Model` subclass can only fake this by mapping `tools_to_call_from` → a Choice question. Proposed agent-control design: a `ControlledModel` wrapper that asks the decider *which tool (or final_answer)*, then has the generative LLM fill in arguments for that tool only.
4. **Jev access.** Docs say early access / waitlist (also via Vercel AI Gateway per MarkTechPost). I have no key; `JevDecider` will be tested against recorded fixtures only until you have one.

## 1. Egress / reachability
`scripts/check_connectivity.py` (stdlib-only). Login node `gilbreth-fe02`, run 2026-09-21:

```
PASS jev/typesafe http=405 3.48s   (POST-only endpoint; 405 proves the path)
PASS openai 401 · anthropic 401 · google 404 · huggingface 200 · pypi 200
```
**ACTION-ON-USER — compute node:**
```bash
srun -A <acct> -p a100-80gb --gres=gpu:1 -t 00:05:00 python3 scripts/check_connectivity.py   # GPU node
srun -A <acct> -p <cpu-partition> -t 00:05:00 python3 scripts/check_connectivity.py           # CPU node
```
If FAIL: ask RCAC for the approved proxy and set `HTTPS_PROXY`/`HTTP_PROXY` in `.env` (do not guess a host; template line is in `run_rollouts.slurm`). Anvil compute nodes are commonly egress-restricted too; probe there separately.

## 2. Jev API (source: docs.typesafe.ai `llms.txt`, quickstart, primitives, SDK pages; MarkTechPost 2026-09-19)
- **Endpoint:** `POST https://api.typesafe.ai/v1/systemone`; `Authorization: Bearer $TYPESAFE_API_KEY`; JSON body. Optional `TYPESAFE_API_BASE` override. No streaming.
- **Request:** `{"state": <str|json|array>, "model": "jev-latest", "questions": {name: {type: "choice"|"score"|"noul", instructions, criteria}}}`. Choice `criteria` is `{option: description}` (up to 255 options); Score `criteria` is an ordered list; Noul has none.
- **Response:** `{"model": "jev-1.13.0", "answers": {name: ...}, "usage": {"input_tokens", "output_tokens"}}` — `choice` → `{choice, confidence, probabilities{opt:p}}`; `noul` → `{noul: P(yes)}` (**no `confidence` field**); `score` → `{score, confidence, legend, probabilities}`.
- **Typed, not chat: confirmed.** Constrained typed answers + probabilities.
- **(a) Discrete choice:** one `choice` question with the N options as `criteria`; read `answers[q].choice`.
  **(b) Confidence:** `answers[q].confidence` (a statistic of the probability spread, e.g. ≈(3·p_max−1)/2 for 3 options — *not* p_max) and `probabilities`. For reuse yes/no use a `noul` question: `noul` is P(yes); derive confidence as `max(p,1-p)` ourselves, or use a 2-option `choice` to get vendor `confidence`. **Decision needed:** which one is "Jev's confidence" for calibration (logged in DECISIONS.md; I default to `probabilities[choice]` for cross-decider comparability and log vendor `confidence` too).
- **Model id:** `jev-latest` route; response reports concrete `jev-1.13.0`. Log the returned `model` on every call.
- **Pricing:** $0.042/M input tokens, output free (MarkTechPost; the docs I fetched did not state pricing). **Context:** *not stated* in docs I could reach; the project plan's "~64k" is **unverified**. Rate limits: not documented.
- **Calibration:** docs give **no ECE/Brier/validation numbers** — only "start with conservative thresholds" (0.9+ act, 0.5–0.9 confirm, <0.5 escalate). Vendor's own claims ("193.6x faster / 444.6x cheaper") are vendor-run against a reference = avg of two other LLMs. Hypotheses to test, as planned.
- **SDK:** `typesafe-sdk==0.7.1` (py≥3.10) exists; **I plan a thin `requests`-style client instead** (fewer deps, exact latency control, response cached raw). LiteLLM also has a `/typesafe` pass-through, not needed.

## 3. LiteLLM
- Incident: 1.82.7 and 1.82.8 malicious (2026-03-24, `.pth` credential stealer). Sources disagree on exposure window (vendor: ~40 min; press: <5 h) — irrelevant to us since we avoid both.
- Vendor-audited clean: 1.78.0–1.82.6, and 1.83.0+ (new CI). **Pin `litellm==1.82.6`** (satisfies tau2's `<1.82.7`):
  - wheel sha256 `164a3ef3e19f309e3cabc199bef3d2045212712fefdfa25fc7f75884a5b5b205`
  - sdist sha256 `2aa1c2da21fe940c33613aa447119674a3ad4d2ad5eb064e4d5ce5ee42420136`
  - Install with `pip install --require-hashes` and check `find $VIRTUAL_ENV -name '*.pth'` for `litellm_init.pth`.
  - Latest on PyPI is 1.102.0 (2026-09-20), wheel `manylinux_2_28_x86_64` sha256 `76cd80a9…f31c`; not pinned because of tau2.
- Current LiteLLM (main) map contains: `claude-opus-5`, `claude-fable-5-1`, `gpt-5.2`, `gpt-5.6`, `gemini-3-pro-preview`, `gemini-3.1-pro-preview`, etc. with per-token prices. **UNCERTAIN whether 1.82.6 has them** → own price table.
- Structured output (`response_format`) and usage/cost (`response.usage`, `litellm.completion_cost`) are standard LiteLLM APIs from my prior knowledge, **not re-verified against 1.82.6 docs**; the smoke test will assert their shape when a key is present.
- Model ids in the brief ("GPT-5.x / Claude Opus / Gemini 3 Pro") are placeholders; concrete ids go in `configs/deciders.yaml` and are chosen by you.

## 4. smolagents (latest 1.26.0, 2026-05-29, py≥3.10)
- `ToolCallingAgent` exists; `LiteLLMModel` wraps `litellm.completion` with retries/rate-limit.
- **`Model` interface to subclass:** `generate(self, messages: list[ChatMessage], stop_sequences=None, response_format=None, tools_to_call_from: list[Tool]|None=None, **kw) -> ChatMessage`; `ChatMessage(role, content, tool_calls, raw, token_usage)`.
- **Interception:** the agent asks the model for `tool_calls` each step via `tools_to_call_from`; stop = a `final_answer` tool call; retry/limit = `max_steps`. Hooks: `step_callbacks`, `final_answer_checks`, `planning_interval`. Cleanest seam = wrap the `Model` (blocker 3), not patch the agent.

## 5. Benchmarks
- **tau2-bench** (github.com/sierra-research/tau2-bench): MIT; v1.0.1 (2026-07-22); domains airline/retail/telecom(+mock, banking_knowledge); `uv sync` then `tau2 run --domain retail --agent-llm … --user-llm … --num-trials N`; ground-truth task success. **Requires py≥3.12 and litellm<1.82.7.** The *user simulator* is also an LLM → extra API cost/egress.
- **GAIA** (`gaia-benchmark/GAIA` on HF): **gated (auto-approve)** — needs `HF_TOKEN` and acceptance of terms; must not re-share validation/test in crawlable form (so `results/` and caches with GAIA text stay git-ignored). Dev set public with answers, ~450 questions, 3 levels; quasi-exact-match scoring. Many GAIA tasks need web/file tools → keep to a documented subset.

## 6. GPU sizing & serving
- Exact IDs (HF API, ungated, Apache-2.0): `Qwen/Qwen3-8B` (8.19B params, rev `b968826d…`), `Qwen/Qwen3-14B` (14.77B, rev `40c06982…`), `Qwen/Qwen3-8B-FP8`. Pin the revs.
- bf16 weights ≈ 16.4 GB (8B) / 29.5 GB (14B). 8B fits an A100-40GB with room for KV cache; 14B on 40 GB leaves ~6 GB after runtime overhead (too tight) → **use 80 GB for 14B**.
- Cluster (`sinfo`): partitions `a100-40gb`, `a100-80gb`, `h100`, `a30`, `a10`, `training`; constraint tags e.g. `a100-80gb`. Login node shows an A30 (24 GB) — not a serving target.
- Serving: vLLM 0.29.0 (py 3.10–3.14). **UNCERTAIN**: wheel/CUDA compatibility with Gilbreth's driver — verify on a node; fallback is `transformers` (implemented behind the same `OpenLLMDecider`).
- Qwen3 note: use non-thinking mode / constrained decoding for decisions; log the setting.

## 7. Slurm templates (written, not yet submitted)
`scripts/serve_qwen3.slurm` (GPU only), `scripts/measure.slurm` (`--exclusive`, `--constraint a100-80gb`), `scripts/run_rollouts.slurm` (CPU only). TODOs: confirm `--account` (sacctmgr shows `davisjam`) and the CPU partition name. Conda modules available: `conda/2025.09`, `anaconda/2025.06-py313`; system python is 3.9 → **all envs must be created via conda (py3.12)**. Note `~/.local` has broken `pypdf`/`pymupdf` namespace stubs shadowing the real packages; the project env must not use `--user` site.

## 8. Energy
`nvidia-smi --query-gpu=power.draw` works on the login node (A30 read 179.7 W). Sampler will poll it and integrate (trapezoid) J over each call window, for **local deciders only** (Qwen3, classifier). Limitations: whole-GPU (not per-process) power, so `--exclusive`/dedicated GPU is required for clean numbers; ~10 Hz polling limits resolution of very short calls (batch or subtract idle baseline). API deciders (Jev, frontier): latency + $ only, energy = `N/A (hosted)`. DCGM not checked.
