"""Accuracy labels for arm-0 replay (PLAN.md U1).

Two accuracies per call:
- **strict**: the decider's choice matches the reference action from the successful trajectory.
- **lenient**: strict, OR the choice is a read-only lookup (tau2's own `ToolType.READ`) and
  either (a) that lookup is in the task's gold actions, or (b) the reference action is a
  state-changing tool (`ToolType.WRITE`), i.e. looking something up to verify before acting.
  On the mock pilot the largest "error" for both Jev and the LLM was `get_users` before
  `create_task`. (b) is needed because gold actions often list only the final writes (every
  mock task does), so (a) alone never accepts that case.

Both are lower bounds on "acceptable": other actions may also be fine.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


def _tasks_file(domain: str) -> Path:
    data_dir = os.environ.get("TAU2_DATA_DIR")
    if not data_dir:
        raise RuntimeError("TAU2_DATA_DIR is not set (source scripts/env.sh)")
    return Path(data_dir) / "tau2" / "domains" / domain / "tasks.json"


@lru_cache(maxsize=None)
def gold_action_names(domain: str) -> dict[str, frozenset[str]]:
    """task_id -> names of the tools in that task's gold `evaluation_criteria.actions`."""
    tasks = json.loads(_tasks_file(domain).read_text())
    out = {}
    for task in tasks:
        actions = (task.get("evaluation_criteria") or {}).get("actions") or []
        out[str(task["id"])] = frozenset(a["name"] for a in actions)
    return out


@lru_cache(maxsize=None)
def tools_of_type(domain: str, tool_type: str) -> frozenset[str]:
    """Tools tau2 itself classifies as `ToolType.<tool_type>` (READ, WRITE, ...) for this domain."""
    from tau2.environment.toolkit import ToolType
    from tau2.runner import build_environment

    toolkit = build_environment(domain).tools
    return frozenset(name for name in toolkit.get_tools() if toolkit.tool_type(name) == ToolType[tool_type])


def lenient_correct(choice: str, reference: str, domain: str, task_id: str) -> bool:
    if choice == reference:
        return True
    if choice not in tools_of_type(domain, "READ"):
        return False
    in_gold = choice in gold_action_names(domain).get(str(task_id), frozenset())
    return in_gold or reference in tools_of_type(domain, "WRITE")
