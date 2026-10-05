# Cache guard: paired differences (same test queries, bootstrap over classes)

Accuracy difference in points (a − b); * = 95% CI excludes 0.

## gsmplus

| a − b | queries | accuracy diff [95% CI] | wrong-reuse diff [95% CI] |
|---|---|---|---|
| Jev − Threshold | 2000 | +27.2* [+25.4, +29.0] | +0.9* [+0.4, +1.5] |
| Jev − vCache | 2000 | +27.1* [+25.3, +29.0] | +0.5 [-0.1, +1.1] |
| Jev − Floor | 2000 | +11.6* [+10.0, +13.2] | -1.6* [-2.4, -0.8] |
| Jev − Kev-4B | 2000 | +7.4* [+6.1, +8.8] | -5.4* [-6.5, -4.4] |
| GPT-5.6 − Jev | 2000 | +3.6* [+2.7, +4.5] | -0.3 [-0.6, +0.0] |
| GPT-OSS-20B − Jev | 2000 | +3.0* [+2.1, +4.0] | -0.1 [-0.4, +0.3] |
| Threshold→Jev − Jev | 2000 | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |

## lmarena

| a − b | queries | accuracy diff [95% CI] | wrong-reuse diff [95% CI] |
|---|---|---|---|
| Threshold − Jev | 2000 | +21.7* [+19.4, +24.0] | +2.6* [+1.9, +3.4] |
| Threshold→Jev − Threshold | 2000 | -0.3 [-0.8, +0.1] | -0.2* [-0.4, -0.0] |
| Floor − Threshold | 2000 | -2.1* [-3.1, -1.0] | -1.1* [-1.6, -0.5] |
| Kev-4B − Jev | 2000 | +15.6* [+13.5, +17.7] | +1.6* [+1.0, +2.3] |

## searchqueries

| a − b | queries | accuracy diff [95% CI] | wrong-reuse diff [95% CI] |
|---|---|---|---|
| Jev − Threshold | 2000 | +0.9 [-1.3, +3.1] | -11.9* [-13.4, -10.4] |
| GPT-5.6 − Jev | 2000 | -0.3 [-1.4, +0.8] | -0.9* [-1.5, -0.2] |
| Jev − Floor | 2000 | +3.5* [+1.3, +5.6] | -6.2* [-7.7, -4.7] |

