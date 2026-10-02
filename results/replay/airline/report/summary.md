# Decision replay — airline

- states: 1076 (reward=1 episodes only)
- accuracy = agreement with the reference action from a successful trajectory (a lower bound: other actions may also be acceptable)
- 95% CIs: cluster bootstrap over states. Latency = client wall clock per call, network included.

## Deciders

| decider | model | repeats | concurrency | host | GPU energy |
|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | openrouter/openai/gpt-oss-20b | 5 | 4 | gilbreth-i003.rcac.purdue.edu | not measured: not measured live for the cascade run: the fast stage's GPU energy is reused post-hoc from that decider's own standalone replay, not re-metered here |
| jev | — | 5 | 4 | gilbreth-fe01.rcac.purdue.edu | n/a (hosted) |
| kev-0.8b | — | 5 | 1 | gilbreth-k033.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 71.6 W |
| kev-4b | — | 5 | 1 | gilbreth-i003.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 65.2 W |
| kev-9b | — | 5 | 1 | gilbreth-k025.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 64.1 W |
| llm:local/qwen3-8b | hosted_vllm/Qwen/Qwen3-8B | 5 | 1 | gilbreth-k002.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 61.0 W |
| llm:openrouter/openai/gpt-5.6-sol | openrouter/openai/gpt-5.6-sol | 5 | 4 | amar-alazizy | n/a (hosted) |
| llm:openrouter/openai/gpt-oss-20b | openrouter/openai/gpt-oss-20b | 5 | 4 | amar-alazizy | n/a (hosted) |

## Decision quality

- calls = (state, repeat) pairs attempted; each counts once, as its first attempt that was not an infra error. Decider failures = calls that did not produce a valid decision (no tool call, malformed output, input too long for the model); they are final, never retried (`dwg.errors`). Infra errors = billing/rate-limit/network errors, retried on resume and not counted against the decider. Still missing = states x repeats not yet completed (infra-failed, or never attempted).
- strict accuracy = matches the reference action; lenient also accepts a read-only lookup (tau2 `ToolType.READ`) that is in the task's gold actions, or that comes where the reference is a state-changing (`WRITE`) tool, i.e. checking before acting (`dwg.labels`, PLAN.md U1).

| decider | calls | decider failures | still missing (infra) | strict accuracy [95% CI] | lenient accuracy [95% CI] | consistency [95% CI] | all repeats agree | ECE | Brier |
|---|---|---|---|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 3169 | 228 (7.2%) | 4005 | 0.669 [0.634, 0.704] | 0.685 [0.652, 0.719] | 0.951 [0.941, 0.961] | 0.89 | 0.287 | 0.304 |
| jev | 5380 | 0 (0.0%) | 1 | 0.814 [0.791, 0.836] | 0.826 [0.804, 0.848] | 0.985 [0.980, 0.988] | 0.95 | 0.029 | 0.129 |
| kev-0.8b | 5380 | 175 (3.3%) | 0 | 0.273 [0.247, 0.300] | 0.418 [0.388, 0.447] | 1.000 [1.000, 1.000] | 1.00 | 0.088 | 0.206 |
| kev-4b | 5380 | 170 (3.2%) | 0 | 0.321 [0.294, 0.350] | 0.445 [0.415, 0.476] | 1.000 [1.000, 1.000] | 1.00 | 0.124 | 0.259 |
| kev-9b | 5380 | 170 (3.2%) | 0 | 0.401 [0.371, 0.431] | 0.546 [0.515, 0.577] | 1.000 [1.000, 1.000] | 1.00 | 0.179 | 0.288 |
| llm:local/qwen3-8b | 5380 | 0 (0.0%) | 0 | 0.396 [0.368, 0.425] | 0.442 [0.413, 0.472] | 0.967 [0.961, 0.973] | 0.89 | 0.599 | 0.596 |
| llm:openrouter/openai/gpt-5.6-sol | 5380 | 3 (0.1%) | 0 | 0.885 [0.868, 0.901] | 0.897 [0.881, 0.912] | 0.958 [0.951, 0.965] | 0.86 | 0.103 | 0.110 |
| llm:openrouter/openai/gpt-oss-20b | 5380 | 584 (10.9%) | 0 | 0.670 [0.646, 0.693] | 0.686 [0.663, 0.709] | 0.867 [0.855, 0.877] | 0.60 | 0.286 | 0.304 |

Infra errors retried (raw attempts in the calls files, not decider failures): `cascade-kev-4b-t0.9` 1794 of 3169 attempts, `jev` 1 of 5380 attempts, `llm:openrouter/openai/gpt-oss-20b` 719 of 6099 attempts

## Decision cost

| decider | latency mean | p50 | p95 | min | max | outliers (IQR) | $ / decision [95% CI] | $ total | input tokens p50 |
|---|---|---|---|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 2.352s | 2.100s | 4.635s | 0.727s | 12.436s | 48 | 3.28e-04 [3.18e-04, 3.37e-04] | 0.3756 | 6354 |
| jev | 0.184s | 0.176s | 0.251s | 0.112s | 1.011s | 179 | 1.73e-04 [1.69e-04, 1.77e-04] | 0.9311 | 3563 |
| kev-0.8b | 0.244s | 0.218s | 0.384s | 0.157s | 8.740s | 142 | n/a (local) | n/a | 3159 |
| kev-4b | 0.495s | 0.439s | 0.832s | 0.293s | 10.050s | 133 | n/a (local) | n/a | 3148 |
| kev-9b | 0.631s | 0.548s | 1.053s | 0.363s | 31.003s | 133 | n/a (local) | n/a | 3148 |
| llm:local/qwen3-8b | 0.716s | 0.656s | 1.076s | 0.549s | 4.192s | 294 | n/a (local) | n/a | 3434 |
| llm:openrouter/openai/gpt-5.6-sol | 4.899s | 3.909s | 11.444s | 1.210s | 42.192s | 469 | 3.83e-03 [3.73e-03, 3.92e-03] | 20.5680 | 3192 |
| llm:openrouter/openai/gpt-oss-20b | 1.991s | 1.299s | 6.069s | 0.323s | 43.077s | 431 | 3.11e-04 [3.04e-04, 3.18e-04] | 1.4929 | 3224 |

## Local deciders: model time vs. overhead, and energy

Energy is whole-GPU (GPU per decider in the Deciders table). Block = counter delta over the whole metered run / calls (headline); net subtracts the idle baseline.

| decider | server (model) latency p50 | client latency p50 | HTTP/client overhead p50 | J / decision gross [95% CI] | J / decision net [95% CI] |
|---|---|---|---|---|---|
| kev-0.8b | 0.211s | 0.218s | 0.007s | 47.22 [47.22, 47.22] | 29.30 [29.30, 29.30] |
| kev-4b | 0.432s | 0.439s | 0.007s | 132.39 [132.39, 132.39] | 99.96 [99.96, 99.96] |
| kev-9b | 0.540s | 0.548s | 0.008s | 170.48 [170.48, 170.48] | 129.97 [129.97, 129.97] |
| llm:local/qwen3-8b | n/a | 0.656s | n/a | 211.20 [211.20, 211.20] | 167.13 [167.13, 167.13] |

## Jev relative to each other decider

- vs `cascade-kev-4b-t0.9`: median latency 11.91x, mean $/decision 1.89x (>1 means Jev is faster/cheaper); accuracy difference +0.145
- vs `kev-0.8b`: median latency 1.23x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.541
- vs `kev-4b`: median latency 2.49x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.492
- vs `kev-9b`: median latency 3.11x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.413
- vs `llm:local/qwen3-8b`: median latency 3.72x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.417
- vs `llm:openrouter/openai/gpt-5.6-sol`: median latency 22.17x, mean $/decision 22.10x (>1 means Jev is faster/cheaper); accuracy difference -0.071
- vs `llm:openrouter/openai/gpt-oss-20b`: median latency 7.37x, mean $/decision 1.80x (>1 means Jev is faster/cheaper); accuracy difference +0.144
