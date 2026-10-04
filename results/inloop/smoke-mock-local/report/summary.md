# In-loop run — smoke-mock-local

- reward = tau2's episode reward, mean with a 95% bootstrap CI clustered by task; pass^k = chance that k trials of the same task all succeed (tau-bench).
- $ = agent side (decision + execution); the user simulator's $ is listed apart. G and the user are priced by litellm's price map, deciders by OpenRouter's reported cost.
- decision share = decider's part of the agent's $ / latency (0 for arm C by construction). Fallback = turns where the decider failed and G decided instead.

| arm | G | decider | episodes | errors | reward [95% CI] | pass^1 | $/success | decision share $ | decision share latency | s/turn | turns/ep | fallback |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B: G decides (constrained) + G | hosted_vllm/Qwen/Qwen3-8B | llm:hosted_vllm/Qwen/Qwen3-8B | 10 | 0 (+0 infra) | 0.800 [0.500, 1.000] | 0.800 | 0.0000 | n/a | 58.8% | 0.96 | 2.0 | 0.0% |
| C: G alone (single call) | hosted_vllm/Qwen/Qwen3-8B | — | 10 | 0 (+0 infra) | 0.800 [0.500, 1.000] | 0.800 | 0.0000 | n/a | 0.0% | 0.40 | 2.5 | 0.0% |
| E: Kev decides + G | hosted_vllm/Qwen/Qwen3-8B | kev-4b | 10 | 0 (+0 infra) | 0.600 [0.300, 0.900] | 0.600 | 0.0000 | n/a | 58.9% | 1.49 | 7.4 | 0.0% |
