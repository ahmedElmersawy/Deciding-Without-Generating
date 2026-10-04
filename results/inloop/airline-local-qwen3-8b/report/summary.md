# In-loop run — airline-local-qwen3-8b

- reward = tau2's episode reward, mean with a 95% bootstrap CI clustered by task; pass^k = chance that k trials of the same task all succeed (tau-bench).
- $ = agent side (decision + execution); the user simulator's $ is listed apart. G and the user are priced by litellm's price map, deciders by OpenRouter's reported cost.
- decision share = decider's part of the agent's $ / latency (0 for arm C by construction). Fallback = turns where the decider failed and G decided instead.

| arm | G | decider | episodes | errors | reward [95% CI] | pass^1 | pass^2 | pass^3 | pass^4 | pass^5 | $/success | decision share $ | decision share latency | s/turn | turns/ep | fallback |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B: G decides (constrained) + G | hosted_vllm/Qwen/Qwen3-8B | llm:hosted_vllm/Qwen/Qwen3-8B | 250 | 0 (+0 infra) | 0.308 [0.196, 0.428] | 0.308 | 0.258 | 0.230 | 0.212 | 0.200 | 0.0000 | n/a | 32.7% | 2.09 | 7.0 | 0.0% |
| C: G alone (single call) | hosted_vllm/Qwen/Qwen3-8B | — | 250 | 0 (+0 infra) | 0.196 [0.116, 0.284] | 0.196 | 0.114 | 0.080 | 0.064 | 0.060 | 0.0000 | n/a | 0.0% | 1.43 | 11.5 | 0.0% |
| E: Kev decides + G | hosted_vllm/Qwen/Qwen3-8B | kev-4b | 250 | 0 (+0 infra) | 0.048 [0.012, 0.092] | 0.048 | 0.020 | 0.006 | 0.000 | 0.000 | 0.0000 | n/a | 70.4% | 6.89 | 10.2 | 2.5% |
