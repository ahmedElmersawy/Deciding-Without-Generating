# Cache guard: paired differences (same test queries, bootstrap over classes)

Accuracy difference in points (a − b); * = 95% CI excludes 0.

## gsmplus

| a − b | queries | accuracy diff [95% CI] | wrong-reuse diff [95% CI] |
|---|---|---|---|
| Jev − Threshold | 2000 | +27.2* [+25.5, +29.1] | +0.8* [+0.3, +1.4] |
| Jev − vCache | 2000 | +27.2* [+25.4, +29.0] | +0.4 [-0.2, +1.0] |
| Jev − Floor | 2000 | +11.7* [+10.1, +13.3] | -1.7* [-2.5, -0.9] |
| Jev − Kev-4B | 2000 | +5.2* [+4.0, +6.6] | -4.2* [-5.2, -3.2] |
| GPT-5.6 − Jev | 2000 | +2.6* [+1.9, +3.4] | -0.3 [-0.6, +0.0] |
| GPT-OSS-20B − Jev | 2000 | +1.6* [+0.9, +2.4] | +0.1 [-0.2, +0.5] |
| Threshold→Jev − Jev | 2000 | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |

## lmarena

| a − b | queries | accuracy diff [95% CI] | wrong-reuse diff [95% CI] |
|---|---|---|---|
| Threshold − Jev | 2000 | +0.6 [-0.4, +1.6] | +1.7* [+1.2, +2.3] |
| Threshold→Jev − Threshold | 2000 | +0.5* [+0.2, +0.9] | -0.4* [-0.6, -0.1] |
| Floor − Threshold | 2000 | -1.1* [-1.9, -0.4] | -0.4* [-0.9, -0.1] |
| Kev-4B − Jev | 2000 | +0.6 [-0.3, +1.4] | +0.7* [+0.3, +1.1] |

## searchqueries

| a − b | queries | accuracy diff [95% CI] | wrong-reuse diff [95% CI] |
|---|---|---|---|
| Jev − Threshold | 2000 | +4.4* [+2.3, +6.4] | -10.6* [-12.1, -9.1] |
| GPT-5.6 − Jev | 2000 | -0.4 [-1.5, +0.8] | -2.3* [-3.1, -1.6] |
| Jev − Floor | 2000 | +8.5* [+6.5, +10.5] | -8.8* [-10.2, -7.3] |

