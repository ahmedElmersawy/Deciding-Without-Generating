"""Which failed calls are the decider's fault, shared by replay (what to retry) and analysis
(what to count), so the two can never disagree.

Infra errors say nothing about the decider: billing (402), rate limits (429), provider 5xx,
network/timeouts. A resumed replay retries them. Anything else is a decider failure (no tool
call, malformed output, an input the model can't take such as Kev's "branch too long") and is
final: retrying would let a stochastic decider re-roll its own failures until one succeeds,
hiding them and inflating its accuracy (DECISIONS.md 2026-09-26).
"""

from __future__ import annotations

import re

INFRA_ERROR_MARKERS = (
    "in_flight_budget", "insufficient credits", "rate limit", "ratelimit", "APIConnectionError",
    "ServiceUnavailable", "InternalServerError", "Timeout", "ConnectionError", "timed out",
)
# Status codes only where they are reported as one — `HTTP 520`, `"code":402`, `status 429` —
# never any number in the message: Kev's "branch too long: 4020 tokens" is not a 402.
INFRA_STATUS = re.compile(r"(?:http|\"code\"|status(?:_code)?)\W{0,3}(?:402|429|5\d\d)(?!\d)")


def is_infra_error(error: str) -> bool:
    low = error.lower()
    return any(m.lower() in low for m in INFRA_ERROR_MARKERS) or bool(INFRA_STATUS.search(low))


def is_out_of_credits(error: str) -> bool:
    """A 402 / exhausted OpenRouter budget: the replay stops paid calls on the first one."""
    low = error.lower()
    return ("in_flight_budget" in low or "insufficient credits" in low
            or bool(re.search(r"(?:http|\"code\"|status(?:_code)?)\W{0,3}402(?!\d)", low)))
