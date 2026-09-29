"""OpenRouter spending guard shared by every paid runner (replay, in-loop).

Added 2026-09-25 after a replay ran the account dry mid-run (DECISIONS.md): estimate first,
refuse to start if the estimate doesn't fit --max-usd or the live balance, stop on the first 402.
"""

from __future__ import annotations

import os
from typing import Optional

# Headroom kept on the OpenRouter balance: it pre-authorizes every in-flight request against
# its worst case before billing, so a run sized to exactly the balance fails near the end.
BALANCE_MARGIN = 1.25
BALANCE_FLOOR_USD = 0.25


def openrouter_balance() -> Optional[float]:
    """Remaining OpenRouter credit in $, or None if it can't be read."""
    import requests

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    try:
        data = requests.get("https://openrouter.ai/api/v1/credits",
                            headers={"Authorization": f"Bearer {key}"}, timeout=15).json()["data"]
        return float(data["total_credits"]) - float(data["total_usage"])
    except Exception:
        return None


def check_budget(est_total: float, max_usd: Optional[float]) -> None:
    """Raise SystemExit unless `est_total` fits both --max-usd and the live balance (with headroom)."""
    if max_usd is not None and est_total > max_usd:
        raise SystemExit(f"!! estimated ${est_total:.2f} exceeds --max-usd {max_usd:.2f}; not starting")
    balance = openrouter_balance()
    if balance is None:
        raise SystemExit("!! could not read the OpenRouter balance; not starting paid calls")
    need = est_total * BALANCE_MARGIN + BALANCE_FLOOR_USD
    print(f"==> OpenRouter balance ${balance:.2f}; need ~${need:.2f} (estimate x{BALANCE_MARGIN} + ${BALANCE_FLOOR_USD})")
    if need > balance:
        raise SystemExit(f"!! balance ${balance:.2f} < ~${need:.2f} needed; add credits or lower the scope")
