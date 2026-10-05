# Router: router-routerbench (small = Mixtral-8x7B, large = GPT-4; 1998 test prompts)

- quality = mean recorded score of the routed model (small alone 0.589, large alone 0.792); $ = decider $ + routed model's recorded $ per query; 'vs random' = quality minus a random mix sending the same share to the large model; APGR = mean share of the quality gap recovered over all large-call rates (random mix = 0.5).

| router | n | quality [95% CI] | sent to large | $ / query | vs random mix | APGR | failures |
|---|---|---|---|---|---|---|---|
| Always small (Mixtral) | 1998 | 0.589 [0.589, 0.589] | 0.0% | 1.23e-04 | +0.000 | — | 0 |
| Always large (GPT-4) | 1998 | 0.792 [0.792, 0.792] | 100.0% | 3.82e-03 | +0.000 | — | 0 |
| Jev | 200 | 0.611 [0.549, 0.674] | 0.0% | 1.41e-04 | +0.000 | 0.647 | 0 |
| GPT-5.6 | 200 | 0.611 [0.549, 0.674] | 0.5% | 1.27e-03 | -0.001 | 0.511 | 0 |
| GPT-OSS-20B | 199 | 0.614 [0.553, 0.676] | 4.0% | 2.78e-04 | -0.002 | 0.444 | 1 |
