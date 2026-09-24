# Benchmark table (mock-pilot)

| Decider | Accuracy | 95% CI | Median latency (ms) | p95 latency (ms) | ECE |
|---|---|---|---|---|---|
| Jev | 77.2% | [66.8%, 86.8%] | 373.8 | 510.2 | 0.087 |
| GPT-OSS-20B | 85.2% | [77.8%, 91.7%] | 872.8 | 1736.6 | 0.111 |
| Kev-0.8B | 35.4% | [24.6%, 47.7%] | 130.7 | 181.8 | 0.350 |
| Kev-4B | 61.5% | [49.2%, 73.8%] | 86.0 | 100.6 | 0.307 |
| Kev-9B | 63.1% | [50.8%, 75.4%] | 92.8 | 120.0 | 0.321 |
| Cascade (t=0.9) | 69.8% | [59.1%, 79.7%] | 249.2 | 2004.8 | 0.264 |

Qwen3: not yet benchmarked (PLAN.md G3 not started — no local Qwen3 decider run exists).
