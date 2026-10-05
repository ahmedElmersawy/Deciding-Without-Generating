# Cache guard: cacheguard-gsmplus

- test queries answered by the deciders: 200 (reuse would be correct for 31.5%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 200 | 0.005 [0.000, 0.015] | 0.050 [0.024, 0.082] | 0.945 [0.911, 0.975] | 0.270 | 0.981 | 0 | 2.31e-05 | 0.13s |
| llm:openrouter/openai/gpt-5.6-sol | 200 | 0.005 [0.000, 0.015] | 0.010 [0.000, 0.025] | 0.985 [0.965, 1.000] | 0.310 | 0.984 | 0 | 1.09e-03 | 1.23s |
| llm:openrouter/openai/gpt-oss-20b | 199 | 0.000 [0.000, 0.000] | 0.020 [0.005, 0.041] | 0.980 [0.959, 0.995] | 0.296 | 1.000 | 1 | 4.98e-05 | 1.03s |
| threshold @95% precision (tau inf) | 200 | 0.000 [0.000, 0.000] | 0.315 [0.251, 0.380] | 0.685 [0.620, 0.749] | 0.000 | nan | 0 | local/free | — |
| threshold @95% precision (full test) (tau inf) | 2000 | 0.000 [0.000, 0.000] | 0.336 [0.318, 0.355] | 0.664 [0.645, 0.682] | 0.000 | nan | 0 | local/free | — |
| threshold max accuracy (tau 0.999) | 200 | 0.000 [0.000, 0.000] | 0.315 [0.251, 0.380] | 0.685 [0.620, 0.749] | 0.000 | nan | 0 | local/free | — |
| threshold max accuracy (full test) (tau 0.999) | 2000 | 0.003 [0.001, 0.006] | 0.336 [0.318, 0.355] | 0.661 [0.642, 0.679] | 0.003 | 0.000 | 0 | local/free | — |
| cross-encoder @95% precision (tau inf) | 200 | 0.000 [0.000, 0.000] | 0.315 [0.251, 0.380] | 0.685 [0.620, 0.749] | 0.000 | nan | 0 | local/free | — |
| cross-encoder @95% precision (full test) (tau inf) | 2000 | 0.000 [0.000, 0.000] | 0.336 [0.318, 0.355] | 0.664 [0.645, 0.682] | 0.000 | nan | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.961) | 200 | 0.000 [0.000, 0.000] | 0.310 [0.246, 0.376] | 0.690 [0.624, 0.754] | 0.005 | 1.000 | 0 | local/free | — |
| cross-encoder max accuracy (full test) (tau 0.961) | 2000 | 0.003 [0.001, 0.005] | 0.335 [0.316, 0.353] | 0.663 [0.645, 0.681] | 0.004 | 0.375 | 0 | local/free | — |
