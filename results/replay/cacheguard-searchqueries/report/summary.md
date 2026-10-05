# Cache guard: cacheguard-searchqueries

- test queries answered by the deciders: 200 (reuse would be correct for 54.0%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 200 | 0.085 [0.049, 0.126] | 0.200 [0.146, 0.260] | 0.715 [0.650, 0.777] | 0.425 | 0.800 | 0 | 1.78e-05 | 0.14s |
| llm:openrouter/openai/gpt-5.6-sol | 200 | 0.055 [0.025, 0.089] | 0.190 [0.137, 0.250] | 0.755 [0.692, 0.814] | 0.405 | 0.864 | 0 | 8.67e-04 | 1.31s |
| llm:openrouter/openai/gpt-oss-20b | 198 | 0.086 [0.050, 0.127] | 0.182 [0.131, 0.237] | 0.732 [0.667, 0.793] | 0.444 | 0.807 | 2 | 3.62e-05 | 0.75s |
| threshold @95% precision (tau 0.992) | 200 | 0.005 [0.000, 0.015] | 0.465 [0.394, 0.535] | 0.530 [0.460, 0.600] | 0.080 | 0.938 | 0 | local/free | — |
| threshold @95% precision (full test) (tau 0.992) | 2000 | 0.006 [0.003, 0.010] | 0.475 [0.452, 0.497] | 0.519 [0.496, 0.542] | 0.072 | 0.917 | 0 | local/free | — |
| threshold max accuracy (tau 0.879) | 200 | 0.205 [0.151, 0.263] | 0.080 [0.045, 0.121] | 0.715 [0.652, 0.776] | 0.665 | 0.692 | 0 | local/free | — |
| threshold max accuracy (full test) (tau 0.879) | 2000 | 0.219 [0.200, 0.238] | 0.077 [0.066, 0.090] | 0.704 [0.683, 0.724] | 0.682 | 0.679 | 0 | local/free | — |
| cross-encoder @95% precision (tau 0.961) | 200 | 0.015 [0.000, 0.035] | 0.525 [0.455, 0.594] | 0.460 [0.391, 0.530] | 0.030 | 0.500 | 0 | local/free | — |
| cross-encoder @95% precision (full test) (tau 0.961) | 2000 | 0.011 [0.007, 0.016] | 0.508 [0.485, 0.530] | 0.481 [0.459, 0.504] | 0.044 | 0.750 | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.108) | 200 | 0.220 [0.164, 0.279] | 0.050 [0.020, 0.084] | 0.730 [0.667, 0.790] | 0.710 | 0.690 | 0 | local/free | — |
| cross-encoder max accuracy (full test) (tau 0.108) | 2000 | 0.234 [0.215, 0.254] | 0.076 [0.065, 0.088] | 0.690 [0.670, 0.710] | 0.699 | 0.665 | 0 | local/free | — |
