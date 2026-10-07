# Cache guard: cacheguard-gsmplus

- test queries answered by the deciders: 2000 (reuse would be correct for 33.6%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 10000 | 0.012 [0.008, 0.017] | 0.055 [0.045, 0.066] | 0.933 [0.921, 0.944] | 0.293 | 0.958 | 0 | 2.30e-05 | 0.13s |
| kev-4b | 10000 | 0.067 [0.056, 0.078] | 0.074 [0.063, 0.086] | 0.859 [0.843, 0.874] | 0.328 | 0.797 | 0 | — | 0.07s |
| llm:local/qwen3-8b | 10000 | 0.039 [0.031, 0.048] | 0.121 [0.107, 0.136] | 0.840 [0.823, 0.856] | 0.254 | 0.847 | 0 | — | 0.40s |
| llm:openrouter/openai/gpt-5.6-sol | 6000 | 0.009 [0.006, 0.013] | 0.022 [0.016, 0.029] | 0.969 [0.961, 0.976] | 0.323 | 0.971 | 0 | 1.11e-03 | 1.40s |
| llm:openrouter/openai/gpt-oss-20b | 9962 | 0.011 [0.007, 0.016] | 0.026 [0.020, 0.032] | 0.963 [0.956, 0.970] | 0.322 | 0.964 | 38 | 5.08e-05 | 1.10s |
| threshold @95% precision (tau inf) | 2000 | 0.000 [0.000, 0.000] | 0.336 [0.318, 0.355] | 0.664 [0.645, 0.682] | 0.000 | nan | 0 | local/free | — |
| threshold max accuracy (tau 0.999) | 2000 | 0.003 [0.001, 0.006] | 0.336 [0.318, 0.355] | 0.661 [0.642, 0.679] | 0.003 | 0.000 | 0 | local/free | — |
| cross-encoder @95% precision (tau inf) | 2000 | 0.000 [0.000, 0.000] | 0.336 [0.318, 0.355] | 0.664 [0.645, 0.682] | 0.000 | nan | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.961) | 2000 | 0.003 [0.001, 0.005] | 0.335 [0.316, 0.353] | 0.663 [0.645, 0.681] | 0.004 | 0.375 | 0 | local/free | — |
| floor (trained on dev) | 2000 | 0.029 [0.022, 0.036] | 0.155 [0.140, 0.171] | 0.817 [0.800, 0.833] | 0.209 | 0.864 | 0 | local/free | — |
| vCache (delta 0.05) | 2000 | 0.007 [0.004, 0.012] | 0.331 [0.313, 0.349] | 0.661 [0.643, 0.680] | 0.013 | 0.400 | 0 | local/free | — |
| threshold -> Jev cascade (band [-inf, inf); Jev asked 100%) | 10000 | 0.012 [0.008, 0.017] | 0.055 [0.045, 0.066] | 0.933 [0.921, 0.944] | 0.293 | 0.958 | 0 | 2.30e-05 | — |
