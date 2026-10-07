# Cache guard: cacheguard-lmarena

- test queries answered by the deciders: 2000 (reuse would be correct for 88.8%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 10000 | 0.041 [0.031, 0.052] | 0.247 [0.225, 0.268] | 0.712 [0.690, 0.736] | 0.683 | 0.940 | 0 | 3.50e-05 | 0.14s |
| kev-4b | 10000 | 0.058 [0.046, 0.070] | 0.074 [0.061, 0.087] | 0.869 [0.851, 0.886] | 0.872 | 0.934 | 0 | — | 0.10s |
| llm:local/qwen3-8b | 10000 | 0.057 [0.045, 0.069] | 0.087 [0.075, 0.101] | 0.856 [0.839, 0.873] | 0.858 | 0.934 | 0 | — | 0.41s |
| llm:openrouter/openai/gpt-5.6-sol | 6000 | 0.030 [0.022, 0.039] | 0.264 [0.243, 0.285] | 0.706 [0.684, 0.728] | 0.654 | 0.954 | 0 | 1.74e-03 | 1.73s |
| llm:openrouter/openai/gpt-oss-20b | 9950 | 0.048 [0.038, 0.059] | 0.179 [0.163, 0.196] | 0.773 [0.755, 0.791] | 0.757 | 0.937 | 50 | 6.07e-05 | 1.28s |
| threshold @95% precision (tau 0.942) | 2000 | 0.053 [0.042, 0.066] | 0.161 [0.144, 0.178] | 0.786 [0.766, 0.805] | 0.781 | 0.932 | 0 | local/free | — |
| threshold max accuracy (tau 0.766) | 2000 | 0.067 [0.055, 0.080] | 0.004 [0.001, 0.006] | 0.929 [0.916, 0.942] | 0.952 | 0.930 | 0 | local/free | — |
| cross-encoder @95% precision (tau 0.916) | 2000 | 0.047 [0.037, 0.058] | 0.284 [0.261, 0.307] | 0.669 [0.645, 0.693] | 0.651 | 0.928 | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.005) | 2000 | 0.070 [0.058, 0.084] | 0.003 [0.001, 0.006] | 0.926 [0.913, 0.939] | 0.956 | 0.926 | 0 | local/free | — |
| floor (trained on dev) | 2000 | 0.057 [0.045, 0.069] | 0.035 [0.026, 0.044] | 0.909 [0.894, 0.923] | 0.910 | 0.938 | 0 | local/free | — |
| vCache (delta 0.05) | 2000 | 0.003 [0.000, 0.005] | 0.412 [0.389, 0.436] | 0.586 [0.562, 0.609] | 0.479 | 0.995 | 0 | local/free | — |
| threshold -> Jev cascade (band [0.678, 0.844); Jev asked 3%) | 10000 | 0.065 [0.053, 0.078] | 0.009 [0.005, 0.013] | 0.926 [0.913, 0.939] | 0.944 | 0.931 | 0 | 9.62e-07 | — |
