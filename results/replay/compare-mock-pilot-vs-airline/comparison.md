# mock-pilot vs airline — decider comparison

- mock-pilot: results/replay/mock-pilot
- airline: results/replay/airline
- Significance: independent-sample bootstrap on accuracy (NOT paired — different state universes)

| Decider | mock-pilot acc | airline acc | Diff | 95% CI | Sig? | mock-pilot p50 lat (ms) | airline p50 lat (ms) | mock-pilot ECE | airline ECE |
|---|---|---|---|---|---|---|---|---|---|
| Cascade (t=0.9) | 69.7% | 66.9% | +2.8pts | [-8.2, +13.5] | no | 249.0 | 2100.1 | 0.265 | 0.287 |
| Jev | 77.2% | 81.4% | -4.1pts | [-14.6, +5.6] | no | 373.8 | 176.3 | 0.087 | 0.029 |
| Kev-0.8B | 35.4% | 27.3% | +8.1pts | [-3.7, +20.1] | no | 130.7 | 217.6 | 0.350 | 0.088 |
| Kev-4B | 61.5% | 32.1% | +29.4pts | [+16.9, +41.2] | YES | 86.0 | 438.7 | 0.307 | 0.124 |
| Kev-9B | 63.1% | 40.1% | +23.0pts | [+10.4, +35.0] | YES | 92.8 | 547.5 | 0.321 | 0.179 |
| Qwen3-8B (local) | 92.9% | 39.6% | +53.3pts | [+46.1, +59.4] | YES | 422.8 | 655.9 | 0.067 | 0.599 |
| GPT-OSS-20B | 85.5% | 67.2% | +18.3pts | [+12.0, +26.4] | YES | 872.7 | 1160.8 | 0.108 | 0.285 |
