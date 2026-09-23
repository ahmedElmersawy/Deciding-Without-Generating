# Decision replay — mock-pilot

- states: 65 (reward=1 episodes only), repeats per state: 5, concurrency: 1
- LLM decider model: `openrouter/openai/gpt-oss-20b`
- accuracy = agreement with the reference action from a successful trajectory (a lower bound: other actions may also be acceptable)
- 95% CIs: cluster bootstrap over states. Latency = client wall clock per call, network included.

## Decision quality

| decider | calls | errors | accuracy [95% CI] | consistency [95% CI] | all repeats agree | ECE | Brier |
|---|---|---|---|---|---|---|---|
| jev | 325 | 0 | 0.772 [0.668, 0.868] | 0.982 [0.960, 0.997] | 0.94 | 0.087 | 0.112 |
| kev-0.8b | 325 | 0 | 0.354 [0.246, 0.477] | 1.000 [1.000, 1.000] | 1.00 | 0.350 | 0.329 |
| llm:openrouter/openai/gpt-oss-20b | 325 | 1 | 0.855 [0.782, 0.920] | 0.932 [0.900, 0.960] | 0.74 | 0.108 | 0.131 |

## Decision cost

| decider | latency mean | p50 | p95 | min | max | outliers (IQR) | $ / decision [95% CI] | $ total | input tokens p50 |
|---|---|---|---|---|---|---|---|---|---|
| jev | 0.391s | 0.374s | 0.510s | 0.284s | 0.871s | 10 | 3.13e-05 [3.03e-05, 3.23e-05] | 0.0102 | 725 |
| kev-0.8b | 0.137s | 0.131s | 0.182s | 0.105s | 0.233s | 14 | n/a (local) | n/a | 430 |
| llm:openrouter/openai/gpt-oss-20b | 0.994s | 0.873s | 1.706s | 0.542s | 2.759s | 19 | 8.09e-05 [7.74e-05, 8.47e-05] | 0.0262 | 622 |

## Local deciders: model time vs. overhead, and energy

GPU: energy not measured (energy counter implausible on NVIDIA GeForce RTX 3050 Ti Laptop GPU: 718 W implied under polling vs 9.3 W reported by NVML power usage). Energy is whole-GPU over each (serialized) call; net subtracts the idle baseline.

| decider | server (model) latency p50 | client latency p50 | HTTP/client overhead p50 | J / decision gross [95% CI] | J / decision net [95% CI] |
|---|---|---|---|---|---|
| kev-0.8b | 0.127s | 0.131s | 0.004s | n/a | n/a |

## Jev relative to each other decider

- vs `kev-0.8b`: median latency 0.35x, no $ cost (local) (>1 means Jev is faster/cheaper); accuracy difference +0.418
- vs `llm:openrouter/openai/gpt-oss-20b`: median latency 2.33x, mean $/decision 2.58x (>1 means Jev is faster/cheaper); accuracy difference -0.083
