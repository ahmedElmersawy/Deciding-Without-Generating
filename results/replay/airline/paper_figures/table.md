# Benchmark table (airline)

| Decider | Accuracy | 95% CI | Median latency (ms) | p95 latency (ms) | $ / decision | ECE |
|---|---|---|---|---|---|---|
| GPT-5.6† | 88.5% | [86.8%, 90.1%] | 3908.7 | 11444.3 | 3.83e-03 | 0.103 |
| Jev→GPT-5.6 | 84.9% | [82.8%, 86.9%] | 162.1 | 3184.1 | 8.16e-04 | 0.063 |
| Jev | 81.4% | [79.1%, 83.6%] | 176.3 | 251.0 | 1.73e-04 | 0.029 |
| GPT-OSS-20B | 67.0% | [64.6%, 69.3%] | 1299.0 | 6069.4 | 3.11e-04 | 0.286 |
| Qwen3-8B | 39.6% | [36.8%, 42.5%] | 655.9 | 1076.1 | local (no API $) | 0.599 |
| Kev-0.8B | 27.3% | [24.7%, 30.0%] | 217.6 | 384.4 | local (no API $) | 0.088 |
| Kev-4B | 32.1% | [29.4%, 35.0%] | 438.7 | 831.9 | local (no API $) | 0.124 |
| Kev-9B | 40.1% | [37.1%, 43.1%] | 547.5 | 1053.3 | local (no API $) | 0.179 |
| Kev-4B→GPT-OSS | 64.7% | [62.3%, 67.2%] | 2879.4 | 8746.6 | 2.11e-04 | 0.311 |

† Graded against its own reference trajectories (the airline labels are GPT-5.6's actions), so its accuracy is an upper bound.
