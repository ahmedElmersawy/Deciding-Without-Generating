# Cache guard: cacheguard-lmarena

- test queries answered by the deciders: 2000 (reuse would be correct for 92.5%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 10000 | 0.012 [0.008, 0.017] | 0.025 [0.018, 0.033] | 0.963 [0.954, 0.971] | 0.912 | 0.987 | 0 | 2.15e-05 | 0.18s |
| kev-4b | 10000 | 0.019 [0.013, 0.025] | 0.013 [0.007, 0.019] | 0.969 [0.960, 0.977] | 0.932 | 0.980 | 0 | — | 0.07s |
| llm:local/qwen3-8b | 10000 | 0.018 [0.012, 0.024] | 0.026 [0.018, 0.033] | 0.957 [0.947, 0.966] | 0.918 | 0.980 | 0 | — | 0.39s |
| llm:openrouter/openai/gpt-5.6-sol | 6000 | 0.004 [0.002, 0.007] | 0.084 [0.071, 0.097] | 0.912 [0.899, 0.925] | 0.846 | 0.995 | 0 | 1.03e-03 | 1.19s |
| llm:openrouter/openai/gpt-oss-20b | 9975 | 0.010 [0.006, 0.014] | 0.057 [0.048, 0.067] | 0.933 [0.923, 0.943] | 0.878 | 0.989 | 25 | 4.36e-05 | 1.66s |
| threshold @95% precision (tau 0.650) | 2000 | 0.044 [0.035, 0.054] | 0.000 [0.000, 0.000] | 0.956 [0.946, 0.965] | 0.970 | 0.954 | 0 | local/free | — |
| threshold max accuracy (tau 0.766) | 2000 | 0.029 [0.022, 0.037] | 0.003 [0.001, 0.005] | 0.969 [0.960, 0.976] | 0.952 | 0.970 | 0 | local/free | — |
| cross-encoder @95% precision (tau 0.005) | 2000 | 0.048 [0.038, 0.057] | 0.001 [0.000, 0.003] | 0.952 [0.942, 0.961] | 0.972 | 0.951 | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.005) | 2000 | 0.033 [0.025, 0.041] | 0.003 [0.001, 0.005] | 0.965 [0.956, 0.973] | 0.956 | 0.965 | 0 | local/free | — |
| floor (trained on dev) | 2000 | 0.025 [0.018, 0.032] | 0.018 [0.012, 0.025] | 0.957 [0.947, 0.966] | 0.931 | 0.974 | 0 | local/free | — |
| vCache (delta 0.05) | 2000 | 0.003 [0.000, 0.005] | 0.452 [0.427, 0.476] | 0.546 [0.522, 0.570] | 0.479 | 0.995 | 0 | local/free | — |
| threshold -> Jev cascade (band [0.678, 0.844); Jev asked 3%) | 10000 | 0.025 [0.018, 0.033] | 0.001 [0.000, 0.002] | 0.974 [0.966, 0.981] | 0.950 | 0.973 | 0 | 5.91e-07 | — |
