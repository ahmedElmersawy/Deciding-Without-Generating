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
| llm:openrouter/openai/gpt-oss-20b | openrouter/openai/gpt-oss-20b | 5 | 4 | amar-alazizy | n/a (hosted) |

## Decision quality

| decider | calls | errors | accuracy [95% CI] | consistency [95% CI] | all repeats agree | ECE | Brier |
|---|---|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 327 | 2 | 0.698 [0.591, 0.797] | 0.948 [0.914, 0.978] | 0.85 | 0.264 | 0.276 |
| jev | 325 | 0 | 0.772 [0.668, 0.868] | 0.982 [0.960, 0.997] | 0.94 | 0.087 | 0.112 |
| kev-0.8b | 325 | 0 | 0.354 [0.246, 0.477] | 1.000 [1.000, 1.000] | 1.00 | 0.350 | 0.329 |
| kev-4b | 325 | 0 | 0.615 [0.492, 0.738] | 1.000 [1.000, 1.000] | 1.00 | 0.307 | 0.321 |
| kev-9b | 325 | 0 | 0.631 [0.508, 0.754] | 1.000 [1.000, 1.000] | 1.00 | 0.321 | 0.300 |
| llm:openrouter/openai/gpt-oss-20b | 326 | 1 | 0.852 [0.778, 0.917] | 0.929 [0.895, 0.960] | 0.74 | 0.111 | 0.134 |

## Decision cost

| decider | latency mean | p50 | p95 | min | max | outliers (IQR) | $ / decision [95% CI] | $ total | input tokens p50 |
|---|---|---|---|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 0.624s | 0.249s | 2.005s | 0.078s | 12.169s | 16 | 8.82e-05 [7.76e-05, 1.00e-04] | 0.0115 | 558 |
| jev | 0.391s | 0.374s | 0.510s | 0.284s | 0.871s | 10 | 3.13e-05 [3.03e-05, 3.23e-05] | 0.0102 | 725 |
| kev-0.8b | 0.137s | 0.131s | 0.182s | 0.105s | 0.233s | 14 | n/a (local) | n/a | 430 |
| kev-4b | 0.089s | 0.086s | 0.101s | 0.081s | 0.276s | 15 | n/a (local) | n/a | 430 |
| kev-9b | 0.096s | 0.093s | 0.120s | 0.080s | 0.159s | 15 | n/a (local) | n/a | 430 |
| llm:openrouter/openai/gpt-oss-20b | 1.004s | 0.873s | 1.737s | 0.542s | 3.998s | 17 | 8.09e-05 [7.74e-05, 8.46e-05] | 0.0263 | 622 |

## Local deciders: model time vs. overhead, and energy

Energy is whole-GPU (GPU per decider in the Deciders table). Block = counter delta over the whole metered run / calls (headline); net subtracts the idle baseline.

| decider | server (model) latency p50 | client latency p50 | HTTP/client overhead p50 | J / decision gross [95% CI] | J / decision net [95% CI] |
|---|---|---|---|---|---|
| cascade-kev-4b-t0.9 | 0.083s | 0.249s | 0.166s | n/a | n/a |
| kev-0.8b | 0.127s | 0.131s | 0.004s | n/a | n/a |
| kev-4b | 0.083s | 0.086s | 0.003s | 18.33 [18.33, 18.33] | 11.95 [11.95, 11.95] |
| kev-9b | 0.090s | 0.093s | 0.003s | 24.44 [24.44, 24.44] | 17.93 [17.93, 17.93] |

## Jev relative to each other decider

- vs `cascade-kev-4b-t0.9`: median latency 0.67x, mean $/decision 2.82x (>1 means Jev is faster/cheaper); accuracy difference +0.074
- vs `kev-0.8b`: median latency 0.35x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.418
- vs `kev-4b`: median latency 0.23x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.157
- vs `kev-9b`: median latency 0.25x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.142
- vs `llm:openrouter/openai/gpt-oss-20b`: median latency 2.33x, mean $/decision 2.58x (>1 means Jev is faster/cheaper); accuracy difference -0.080
