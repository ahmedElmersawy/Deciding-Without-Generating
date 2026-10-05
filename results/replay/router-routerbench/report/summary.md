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
