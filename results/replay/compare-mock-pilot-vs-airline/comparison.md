# Mock vs Airline — decider comparison

- Mock: results/replay/mock-pilot
- Airline: results/replay/airline
- Significance: independent-sample bootstrap on accuracy (NOT paired — different state universes)

| Decider | Mock acc | Airline acc | Diff | 95% CI | Sig? | Mock p50 lat (ms) | Airline p50 lat (ms) | Mock ECE | Airline ECE |
|---|---|---|---|---|---|---|---|---|---|
| Kev-4B | 61.5% | 28.9% | +32.7pts | [+20.0, +44.8] | YES | 86.0 | 436.8 | 0.307 | 0.199 |
| Kev-9B | 63.1% | 41.1% | +22.0pts | [+9.2, +34.1] | YES | 92.8 | 547.3 | 0.321 | 0.197 |
