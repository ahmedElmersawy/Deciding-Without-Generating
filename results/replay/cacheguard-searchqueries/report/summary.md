# Cache guard: cacheguard-searchqueries

- test queries answered by the deciders: 2000 (reuse would be correct for 58.2%); dev queries for tuning: 600.
- wrong reuse = served a wrong cached answer; needless regen = regenerated although reuse was right; both as a share of all queries, 95% CI clustered by class. Baseline taus are picked on dev only.

| decider | n | wrong reuse | needless regen | accuracy | reuse rate | reuse precision | failures | $/decision | p50 latency |
|---|---|---|---|---|---|---|---|---|---|
| jev | 9987 | 0.038 [0.030, 0.047] | 0.106 [0.093, 0.120] | 0.856 [0.840, 0.871] | 0.515 | 0.926 | 13 | 1.83e-05 | 0.19s |
| kev-4b | 10000 | 0.086 [0.074, 0.099] | 0.060 [0.050, 0.071] | 0.854 [0.838, 0.869] | 0.609 | 0.858 | 0 | — | 0.07s |
| llm:local/qwen3-8b | 10000 | 0.065 [0.054, 0.076] | 0.087 [0.075, 0.099] | 0.848 [0.832, 0.864] | 0.560 | 0.884 | 0 | — | 0.40s |
| llm:openrouter/openai/gpt-5.6-sol | 5998 | 0.015 [0.010, 0.021] | 0.133 [0.119, 0.148] | 0.852 [0.837, 0.866] | 0.464 | 0.968 | 2 | 8.77e-04 | 1.24s |
| llm:openrouter/openai/gpt-oss-20b | 9959 | 0.034 [0.028, 0.042] | 0.130 [0.117, 0.143] | 0.836 [0.822, 0.850] | 0.487 | 0.929 | 41 | 3.48e-05 | 1.16s |
| threshold @95% precision (tau 0.949) | 2000 | 0.021 [0.014, 0.027] | 0.195 [0.178, 0.212] | 0.784 [0.767, 0.802] | 0.408 | 0.950 | 0 | local/free | — |
| threshold max accuracy (tau 0.879) | 2000 | 0.144 [0.128, 0.160] | 0.044 [0.035, 0.053] | 0.812 [0.794, 0.829] | 0.682 | 0.789 | 0 | local/free | — |
| cross-encoder @95% precision (tau 0.957) | 2000 | 0.024 [0.018, 0.031] | 0.282 [0.262, 0.302] | 0.694 [0.674, 0.714] | 0.325 | 0.926 | 0 | local/free | — |
| cross-encoder max accuracy (tau 0.071) | 2000 | 0.171 [0.155, 0.188] | 0.044 [0.036, 0.054] | 0.784 [0.766, 0.802] | 0.709 | 0.759 | 0 | local/free | — |
| floor (trained on dev) | 2000 | 0.126 [0.112, 0.141] | 0.103 [0.090, 0.116] | 0.771 [0.752, 0.789] | 0.606 | 0.792 | 0 | local/free | — |
| vCache (delta 0.05) | 2000 | 0.019 [0.014, 0.026] | 0.477 [0.455, 0.500] | 0.503 [0.481, 0.525] | 0.120 | 0.838 | 0 | local/free | — |
| threshold -> Jev cascade (band [0.798, 0.985); Jev asked 72%) | 9987 | 0.038 [0.029, 0.047] | 0.106 [0.093, 0.119] | 0.857 [0.841, 0.871] | 0.515 | 0.927 | 13 | 1.32e-05 | — |
