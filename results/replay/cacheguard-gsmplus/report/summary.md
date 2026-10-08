# Cache guard: cacheguard-gsmplus

- test queries answered by the deciders: 2000 (reuse would be correct for 33.6%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 10000 | 0.011 [0.007, 0.016] | 0.055 [0.045, 0.066] | 0.933 [0.922, 0.944] | 0.292 | 0.961 | 0 | 2.32e-05 | 0.18s |
| kev-4b | 10000 | 0.053 [0.043, 0.064] | 0.066 [0.055, 0.077] | 0.881 [0.866, 0.896] | 0.323 | 0.836 | 0 | — | 0.07s |
| llm:local/qwen3-8b | 10000 | 0.025 [0.019, 0.032] | 0.111 [0.098, 0.125] | 0.863 [0.848, 0.878] | 0.250 | 0.898 | 0 | — | 0.39s |
| llm:openrouter/openai/gpt-5.6-sol | 6000 | 0.009 [0.005, 0.013] | 0.032 [0.024, 0.040] | 0.960 [0.951, 0.968] | 0.313 | 0.973 | 0 | 1.11e-03 | 1.32s |
| llm:openrouter/openai/gpt-oss-20b | 9965 | 0.013 [0.009, 0.017] | 0.037 [0.030, 0.046] | 0.950 [0.941, 0.959] | 0.311 | 0.959 | 35 | 4.39e-05 | 1.11s |
| threshold @95% precision (tau inf) | 2000 | 0.000 [0.000, 0.000] | 0.336 [0.318, 0.355] | 0.664 [0.645, 0.682] | 0.000 | nan | 0 | local/free | — |
| threshold max accuracy (tau 0.999) | 2000 | 0.003 [0.001, 0.006] | 0.336 [0.318, 0.355] | 0.661 [0.642, 0.679] | 0.003 | 0.000 | 0 | local/free | — |
| cross-encoder @95% precision (tau inf) | 2000 | 0.000 [0.000, 0.000] | 0.336 [0.318, 0.355] | 0.664 [0.645, 0.682] | 0.000 | nan | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.961) | 2000 | 0.003 [0.001, 0.005] | 0.335 [0.316, 0.353] | 0.663 [0.645, 0.681] | 0.004 | 0.375 | 0 | local/free | — |
| floor (trained on dev) | 2000 | 0.029 [0.022, 0.036] | 0.155 [0.140, 0.171] | 0.817 [0.800, 0.833] | 0.209 | 0.864 | 0 | local/free | — |
| vCache (delta 0.05) | 2000 | 0.007 [0.004, 0.012] | 0.331 [0.313, 0.349] | 0.661 [0.643, 0.680] | 0.013 | 0.400 | 0 | local/free | — |
| threshold -> Jev cascade (band [-inf, inf); Jev asked 100%) | 10000 | 0.011 [0.007, 0.016] | 0.055 [0.045, 0.066] | 0.933 [0.922, 0.944] | 0.292 | 0.961 | 0 | 2.32e-05 | — |
