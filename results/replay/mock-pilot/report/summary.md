# Decision replay — mock-pilot

- states: 65 (reward=1 episodes only)
- accuracy = agreement with the reference action from a successful trajectory (a lower bound: other actions may also be acceptable)
- 95% CIs: cluster bootstrap over states. Latency = client wall clock per call, network included.

## Deciders

| decider | model | repeats | concurrency | host | GPU energy |
|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | openrouter/openai/gpt-oss-20b | 5 | 4 | gilbreth-k043.rcac.purdue.edu | not measured: not measured live for the cascade run: the fast stage's GPU energy is reused post-hoc from that decider's own standalone replay, not re-metered here |
| jev | — | 5 | 4 | amar-alazizy | n/a (hosted) |
| kev-0.8b | — | 5 | 1 | amar-alazizy | not measured: energy counter implausible on NVIDIA GeForce RTX 3050 Ti Laptop GPU: 718 W implied under polling vs 9.3 W reported by NVML power usage |
| kev-4b | — | 5 | 1 | gilbreth-k009.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 67.0 W |
| kev-9b | — | 5 | 1 | gilbreth-k002.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 63.6 W |
| llm:local/qwen3-8b | hosted_vllm/Qwen/Qwen3-8B | 5 | 1 | gilbreth-k015.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 70.7 W |
| llm:openrouter/openai/gpt-oss-20b | openrouter/openai/gpt-oss-20b | 5 | 4 | amar-alazizy | n/a (hosted) |

## Decision quality

- calls = (state, repeat) pairs attempted; each counts once, as its first attempt that was not an infra error. Decider failures = calls that did not produce a valid decision (no tool call, malformed output, input too long for the model); they are final, never retried (`dwg.errors`). Infra errors = billing/rate-limit/network errors, retried on resume and not counted against the decider. Still missing = states x repeats not yet completed (infra-failed, or never attempted).
- strict accuracy = matches the reference action; lenient also accepts a read-only lookup (tau2 `ToolType.READ`) that is in the task's gold actions, or that comes where the reference is a state-changing (`WRITE`) tool, i.e. checking before acting (`dwg.labels`, PLAN.md U1).

| decider | calls | decider failures | still missing (infra) | strict accuracy [95% CI] | lenient accuracy [95% CI] | consistency [95% CI] | all repeats agree | ECE | Brier |
|---|---|---|---|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 325 | 2 (0.6%) | 0 | 0.697 [0.590, 0.797] | 0.746 [0.640, 0.843] | 0.946 [0.911, 0.977] | 0.85 | 0.265 | 0.277 |
| jev | 325 | 0 (0.0%) | 0 | 0.772 [0.668, 0.868] | 0.877 [0.797, 0.948] | 0.982 [0.960, 0.997] | 0.94 | 0.087 | 0.112 |
| kev-0.8b | 325 | 0 (0.0%) | 0 | 0.354 [0.246, 0.477] | 0.354 [0.246, 0.477] | 1.000 [1.000, 1.000] | 1.00 | 0.350 | 0.329 |
| kev-4b | 325 | 0 (0.0%) | 0 | 0.615 [0.492, 0.738] | 0.615 [0.492, 0.738] | 1.000 [1.000, 1.000] | 1.00 | 0.307 | 0.321 |
| kev-9b | 325 | 0 (0.0%) | 0 | 0.631 [0.508, 0.754] | 0.631 [0.508, 0.754] | 1.000 [1.000, 1.000] | 1.00 | 0.321 | 0.300 |
| llm:local/qwen3-8b | 325 | 0 (0.0%) | 0 | 0.929 [0.865, 0.985] | 0.929 [0.865, 0.985] | 0.991 [0.972, 1.000] | 0.98 | 0.067 | 0.069 |
| llm:openrouter/openai/gpt-oss-20b | 325 | 1 (0.3%) | 0 | 0.855 [0.782, 0.920] | 0.935 [0.892, 0.972] | 0.932 [0.900, 0.960] | 0.74 | 0.108 | 0.131 |

## Decision cost

| decider | latency mean | p50 | p95 | min | max | outliers (IQR) | $ / decision [95% CI] | $ total | input tokens p50 |
|---|---|---|---|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 0.613s | 0.249s | 1.927s | 0.078s | 12.169s | 16 | 3.52e-05 [2.39e-05, 4.70e-05] | 0.0114 | 558 |
| jev | 0.391s | 0.374s | 0.510s | 0.284s | 0.871s | 10 | 3.13e-05 [3.03e-05, 3.23e-05] | 0.0102 | 725 |
| kev-0.8b | 0.137s | 0.131s | 0.182s | 0.105s | 0.233s | 14 | n/a (local) | n/a | 430 |
| kev-4b | 0.089s | 0.086s | 0.101s | 0.081s | 0.276s | 15 | n/a (local) | n/a | 430 |
| kev-9b | 0.096s | 0.093s | 0.120s | 0.080s | 0.159s | 15 | n/a (local) | n/a | 430 |
| llm:local/qwen3-8b | 0.424s | 0.423s | 0.442s | 0.403s | 0.450s | 15 | n/a (local) | n/a | 676 |
| llm:openrouter/openai/gpt-oss-20b | 0.994s | 0.873s | 1.706s | 0.542s | 2.759s | 19 | 8.09e-05 [7.74e-05, 8.47e-05] | 0.0262 | 622 |

## Local deciders: model time vs. overhead, and energy

Energy is whole-GPU (GPU per decider in the Deciders table). Block = counter delta over the whole metered run / calls (headline); net subtracts the idle baseline.

| decider | server (model) latency p50 | client latency p50 | HTTP/client overhead p50 | J / decision gross [95% CI] | J / decision net [95% CI] |
|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 0.083s | 0.249s | 0.166s | n/a | n/a |
| kev-0.8b | 0.127s | 0.131s | 0.004s | n/a | n/a |
| kev-4b | 0.083s | 0.086s | 0.003s | 18.33 [18.33, 18.33] | 11.95 [11.95, 11.95] |
| kev-9b | 0.090s | 0.093s | 0.003s | 24.44 [24.44, 24.44] | 17.93 [17.93, 17.93] |
| llm:local/qwen3-8b | n/a | 0.423s | n/a | 125.80 [125.80, 125.80] | 95.30 [95.30, 95.30] |

## Jev relative to each other decider

- vs `cascade-kev-4b-t0.9`: median latency 0.67x, mean $/decision 1.12x (>1 means Jev is faster/cheaper); accuracy difference +0.076
- vs `kev-0.8b`: median latency 0.35x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.418
- vs `kev-4b`: median latency 0.23x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.157
- vs `kev-9b`: median latency 0.25x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.142
- vs `llm:local/qwen3-8b`: median latency 1.13x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference -0.157
- vs `llm:openrouter/openai/gpt-oss-20b`: median latency 2.33x, mean $/decision 2.58x (>1 means Jev is faster/cheaper); accuracy difference -0.083
