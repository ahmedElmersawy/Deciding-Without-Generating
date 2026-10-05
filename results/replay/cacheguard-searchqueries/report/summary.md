# Cache guard: cacheguard-searchqueries

- test queries answered by the deciders: 2000 (reuse would be correct for 54.1%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 10000 | 0.100 [0.087, 0.114] | 0.187 [0.170, 0.204] | 0.713 [0.693, 0.732] | 0.454 | 0.779 | 0 | 1.78e-05 | 0.13s |
| kev-4b | 10000 | 0.176 [0.160, 0.193] | 0.117 [0.103, 0.132] | 0.707 [0.687, 0.726] | 0.600 | 0.706 | 0 | — | 0.07s |
| llm:local/qwen3-8b | 10000 | 0.123 [0.109, 0.138] | 0.156 [0.139, 0.172] | 0.721 [0.701, 0.740] | 0.509 | 0.758 | 0 | — | 0.39s |
| llm:openrouter/openai/gpt-5.6-sol | 6000 | 0.091 [0.079, 0.104] | 0.199 [0.182, 0.216] | 0.710 [0.690, 0.729] | 0.434 | 0.789 | 0 | 9.02e-04 | 1.70s |
| llm:openrouter/openai/gpt-oss-20b | 9969 | 0.107 [0.094, 0.120] | 0.176 [0.161, 0.192] | 0.717 [0.700, 0.735] | 0.471 | 0.774 | 31 | 3.69e-05 | 0.80s |
| threshold @95% precision (tau 0.992) | 2000 | 0.006 [0.003, 0.010] | 0.475 [0.452, 0.497] | 0.519 [0.496, 0.542] | 0.072 | 0.917 | 0 | local/free | — |
| threshold max accuracy (tau 0.879) | 2000 | 0.219 [0.200, 0.238] | 0.077 [0.066, 0.090] | 0.704 [0.683, 0.724] | 0.682 | 0.679 | 0 | local/free | — |
| cross-encoder @95% precision (tau 0.961) | 2000 | 0.011 [0.007, 0.016] | 0.508 [0.485, 0.530] | 0.481 [0.459, 0.504] | 0.044 | 0.750 | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.108) | 2000 | 0.234 [0.215, 0.254] | 0.076 [0.065, 0.088] | 0.690 [0.670, 0.710] | 0.699 | 0.665 | 0 | local/free | — |
| floor (trained on dev) | 2000 | 0.162 [0.146, 0.179] | 0.160 [0.144, 0.177] | 0.678 [0.658, 0.698] | 0.543 | 0.702 | 0 | local/free | — |
| vCache (delta 0.05) | 2000 | 0.019 [0.014, 0.026] | 0.441 [0.418, 0.463] | 0.540 [0.518, 0.562] | 0.120 | 0.838 | 0 | local/free | — |
| threshold -> Jev cascade (band [0.869, 0.883); Jev asked 4%) | 10000 | 0.217 [0.198, 0.235] | 0.081 [0.069, 0.093] | 0.702 [0.683, 0.722] | 0.677 | 0.680 | 0 | 7.58e-07 | — |
