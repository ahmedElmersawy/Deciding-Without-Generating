# Decision replay — airline

- states: 689 (reward=1 episodes only)
- accuracy = agreement with the reference action from a successful trajectory (a lower bound: other actions may also be acceptable)
- 95% CIs: cluster bootstrap over states. Latency = client wall clock per call, network included.

## Deciders

| decider | model | repeats | concurrency | host | GPU energy |
|---|---|---|---|---|---|
| kev-4b | — | 5 | 1 | gilbreth-k019.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 64.0 W |
| kev-9b | — | 5 | 1 | gilbreth-k019.rcac.purdue.edu | NVIDIA A100 80GB PCIe, idle 62.6 W |

## Decision quality

| decider | calls | errors | accuracy [95% CI] | consistency [95% CI] | all repeats agree | ECE | Brier |
|---|---|---|---|---|---|---|---|
| kev-4b | 3445 | 135 | 0.289 [0.255, 0.323] | 1.000 [1.000, 1.000] | 1.00 | 0.199 | 0.268 |
| kev-9b | 3445 | 135 | 0.411 [0.375, 0.449] | 1.000 [1.000, 1.000] | 1.00 | 0.197 | 0.292 |

## Decision cost

| decider | latency mean | p50 | p95 | min | max | outliers (IQR) | $ / decision [95% CI] | $ total | input tokens p50 |
|---|---|---|---|---|---|---|---|---|---|
| kev-4b | 0.489s | 0.437s | 0.832s | 0.296s | 5.505s | 80 | n/a (local) | n/a | 3099 |
| kev-9b | 0.618s | 0.547s | 1.064s | 0.370s | 4.918s | 84 | n/a (local) | n/a | 3099 |

## Local deciders: model time vs. overhead, and energy

Energy is whole-GPU (GPU per decider in the Deciders table). Block = counter delta over the whole metered run / calls (headline); net subtracts the idle baseline.

| decider | server (model) latency p50 | client latency p50 | HTTP/client overhead p50 | J / decision gross [95% CI] | J / decision net [95% CI] |
|---|---|---|---|---|---|
| kev-4b | 0.429s | 0.437s | 0.007s | 131.81 [131.81, 131.81] | 99.97 [99.97, 99.97] |
| kev-9b | 0.540s | 0.547s | 0.008s | 166.54 [166.54, 166.54] | 127.28 [127.28, 127.28] |
