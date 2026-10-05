# Router: router-routerbench (small = Mixtral-8x7B, large = GPT-4; 1998 test prompts)

- quality = mean recorded score of the routed model (small alone 0.589, large alone 0.792); $ = decider $ + routed model's recorded $ per query; 'vs random' = quality minus a random mix sending the same share to the large model; APGR = mean share of the quality gap recovered over all large-call rates (random mix = 0.5).

| router | n | quality [95% CI] | sent to large | $ / query | vs random mix | APGR | failures |
|---|---|---|---|---|---|---|---|
| Always small (Mixtral) | 1998 | 0.589 [0.589, 0.589] | 0.0% | 1.23e-04 | +0.000 | — | 0 |
| Always large (GPT-4) | 1998 | 0.792 [0.792, 0.792] | 100.0% | 3.82e-03 | +0.000 | — | 0 |
| Jev | 9990 | 0.589 [0.569, 0.609] | 0.0% | 1.47e-04 | +0.000 | 0.609 | 0 |
| Kev-4B | 9990 | 0.589 [0.569, 0.609] | 0.0% | 1.23e-04 | +0.000 | 0.582 | 0 |
| Qwen3-8B | 9990 | 0.619 [0.600, 0.638] | 20.6% | 1.58e-03 | -0.012 | 0.531 | 0 |
| GPT-5.6 | 5994 | 0.591 [0.572, 0.611] | 2.3% | 1.32e-03 | -0.003 | 0.529 | 0 |
| GPT-OSS-20B | 9938 | 0.600 [0.581, 0.620] | 4.7% | 3.25e-04 | +0.001 | 0.546 | 52 |
| Floor (trained on RouterBench) | 1998 | 0.613 [0.593, 0.633] | 3.9% | 2.18e-04 | +0.016 | 0.649 | 0 |

## APGR with 95% CI and paired differences (shared bootstrap over test prompts)

| router | APGR [95% CI] | − random (0.5) [95% CI] | − Jev [95% CI] | − floor [95% CI] |
|---|---|---|---|---|
| Jev | 0.609 [0.585, 0.642] | +0.109 [+0.085, +0.142] | — | -0.040 [-0.070, -0.001] |
| Kev-4B | 0.582 [0.553, 0.609] | +0.082 [+0.053, +0.109] | -0.027 [-0.055, -0.007] | -0.067 [-0.103, -0.030] |
| Qwen3-8B | 0.531 [0.488, 0.540] | +0.031 [-0.012, +0.040] | -0.078 [-0.130, -0.067] | -0.118 [-0.170, -0.099] |
| GPT-5.6 | 0.529 [0.510, 0.568] | +0.029 [+0.010, +0.068] | -0.080 [-0.106, -0.045] | -0.120 [-0.153, -0.070] |
| GPT-OSS-20B | 0.546 [0.516, 0.576] | +0.046 [+0.016, +0.076] | -0.063 [-0.102, -0.034] | -0.103 [-0.145, -0.058] |
| Floor (trained on RouterBench) | 0.649 [0.621, 0.678] | +0.149 [+0.121, +0.178] | +0.040 [+0.001, +0.070] | — |

## Dev-tuned operating point (threshold = dev 70th percentile, ~30% sent large)

| router | dev threshold | test: sent large | test quality [95% CI] | vs random mix at that share [95% CI] | $ / query |
|---|---|---|---|---|---|
| Jev | 0.030 | 28.4% | 0.674 [0.655, 0.693] | +0.027 [+0.015, +0.039] | 9.32e-04 |
| Kev-4B | 0.276 | 29.4% | 0.678 [0.660, 0.697] | +0.030 [+0.018, +0.042] | 1.16e-03 |
| Qwen3-8B | 0.050 | 22.7% | 0.624 [0.605, 0.643] | -0.011 [-0.019, -0.003] | 1.67e-03 |
| GPT-5.6 | 0.010 | 23.9% | 0.649 [0.630, 0.669] | +0.012 [+0.001, +0.024] | 2.13e-03 |
| GPT-OSS-20B | 0.110 | 30.0% | 0.668 [0.649, 0.687] | +0.018 [+0.007, +0.030] | 1.32e-03 |
| Floor (trained on RouterBench) | 0.347 | 28.3% | 0.691 [0.673, 0.710] | +0.045 [+0.033, +0.058] | 7.55e-04 |
