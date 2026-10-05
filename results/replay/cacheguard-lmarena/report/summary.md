# Cache guard: cacheguard-lmarena

- test queries answered by the deciders: 200 (reuse would be correct for 89.0%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 200 | 0.035 [0.010, 0.062] | 0.170 [0.119, 0.225] | 0.795 [0.737, 0.851] | 0.755 | 0.954 | 0 | 3.48e-05 | 0.15s |
| llm:openrouter/openai/gpt-5.6-sol | 200 | 0.025 [0.005, 0.050] | 0.210 [0.155, 0.266] | 0.765 [0.706, 0.822] | 0.705 | 0.965 | 0 | 1.72e-03 | 1.26s |
| llm:openrouter/openai/gpt-oss-20b | 198 | 0.035 [0.010, 0.062] | 0.116 [0.071, 0.164] | 0.848 [0.797, 0.897] | 0.808 | 0.956 | 2 | 6.13e-05 | 0.87s |
| threshold @95% precision (tau 0.942) | 200 | 0.050 [0.020, 0.081] | 0.150 [0.101, 0.202] | 0.800 [0.742, 0.854] | 0.790 | 0.937 | 0 | local/free | — |
| threshold @95% precision (full test) (tau 0.942) | 2000 | 0.053 [0.042, 0.066] | 0.161 [0.144, 0.178] | 0.786 [0.766, 0.805] | 0.781 | 0.932 | 0 | local/free | — |
| threshold max accuracy (tau 0.766) | 200 | 0.065 [0.034, 0.101] | 0.000 [0.000, 0.000] | 0.935 [0.899, 0.966] | 0.955 | 0.932 | 0 | local/free | — |
| threshold max accuracy (full test) (tau 0.766) | 2000 | 0.067 [0.055, 0.080] | 0.004 [0.001, 0.006] | 0.929 [0.916, 0.942] | 0.952 | 0.930 | 0 | local/free | — |
| cross-encoder @95% precision (tau 0.916) | 200 | 0.040 [0.015, 0.070] | 0.260 [0.199, 0.323] | 0.700 [0.635, 0.764] | 0.670 | 0.940 | 0 | local/free | — |
| cross-encoder @95% precision (full test) (tau 0.916) | 2000 | 0.047 [0.037, 0.058] | 0.284 [0.261, 0.307] | 0.669 [0.645, 0.693] | 0.651 | 0.928 | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.005) | 200 | 0.075 [0.040, 0.113] | 0.000 [0.000, 0.000] | 0.925 [0.887, 0.960] | 0.965 | 0.922 | 0 | local/free | — |
| cross-encoder max accuracy (full test) (tau 0.005) | 2000 | 0.070 [0.058, 0.084] | 0.003 [0.001, 0.006] | 0.926 [0.913, 0.939] | 0.956 | 0.926 | 0 | local/free | — |
