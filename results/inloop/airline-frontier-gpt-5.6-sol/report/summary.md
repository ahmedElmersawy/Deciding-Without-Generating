# In-loop run — airline-frontier-gpt-5.6-sol

- reward = tau2's episode reward, mean with a 95% bootstrap CI clustered by task; pass^k = chance that k trials of the same task all succeed (tau-bench).
- $ = agent side (decision + execution); the user simulator's $ is listed apart. G and the user are priced by litellm's price map, deciders by OpenRouter's reported cost.
- decision share = decider's part of the agent's $ / latency (0 for arm C by construction). Fallback = turns where the decider failed and G decided instead.

| arm | G | decider | episodes | errors | reward [95% CI] | pass^1 | pass^2 | pass^3 | pass^4 | pass^5 | $/success | decision share $ | decision share latency | s/turn | turns/ep | fallback |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A: Jev decides + G | openrouter/openai/gpt-5.6-sol | jev | 250 | 0 (+0 infra) | 0.744 [0.636, 0.844] | 0.744 | 0.682 | 0.646 | 0.620 | 0.600 | 0.0477 | 5.3% | 7.0% | 2.76 | 10.5 | 0.0% |
| B: G decides (constrained) + G | openrouter/openai/gpt-5.6-sol | llm:openrouter/openai/gpt-5.6-sol | 250 | 0 (+0 infra) | 0.796 [0.696, 0.888] | 0.796 | 0.750 | 0.718 | 0.688 | 0.660 | 0.1760 | 74.5% | 51.1% | 5.36 | 10.2 | 0.7% |
| C: G alone (single call) | openrouter/openai/gpt-5.6-sol | — | 250 | 0 (+0 infra) | 0.792 [0.696, 0.884] | 0.792 | 0.738 | 0.700 | 0.668 | 0.640 | 0.0333 | 0.0% | 0.0% | 2.63 | 10.3 | 0.0% |
| D: small LLM decides + G | openrouter/openai/gpt-5.6-sol | llm:openrouter/openai/gpt-oss-20b | 250 | 0 (+0 infra) | 0.692 [0.572, 0.804] | 0.692 | 0.638 | 0.604 | 0.572 | 0.540 | 0.0432 | 4.9% | 52.7% | 5.35 | 9.1 | 8.7% |
| E: Kev decides + G | openrouter/openai/gpt-5.6-sol | kev-4b | 244 | 6 (+0 infra) | 0.045 [0.012, 0.089] | 0.044 | 0.016 | 0.008 | 0.004 | n/a | 0.4759 | 0.0% | 15.4% | 3.24 | 8.5 | 6.3% |

## Paired arm differences (first arm minus second)

Same (task, trial) and user seed in both arms; per-task mean difference, 95% bootstrap CI over tasks. Starred = CI excludes 0.

| comparison | tasks (pairs) | reward diff [95% CI] | agent $/episode diff [95% CI] | wall s/episode diff [95% CI] |
|---|---|---|---|---|
| A-B | 50 (250) | -0.052* [-0.108, -0.004] | -0.1046* [-0.1258, -0.0851] | -24.2* [-29.2, -19.3] |
| A-C | 50 (250) | -0.048 [-0.108, +0.008] | +0.0091* [+0.0058, +0.0125] | +4.1* [+1.8, +6.4] |
| B-C | 50 (250) | +0.004 [-0.028, +0.040] | +0.1137* [+0.0928, +0.1364] | +28.3* [+23.6, +33.3] |
| D-A | 50 (250) | -0.052 [-0.124, +0.020] | -0.0056* [-0.0098, -0.0018] | +18.4* [+11.7, +25.3] |
| E-A | 50 (244) | -0.701* [-0.801, -0.595] | -0.0141* [-0.0222, -0.0065] | -9.9* [-16.2, -3.5] |
