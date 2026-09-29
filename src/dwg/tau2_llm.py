"""Patches on tau2's own LLM calls (agent, filler and user simulator all go through
`tau2.utils.llm_utils.generate`), shared by the state collector and the in-loop runner."""

from __future__ import annotations


def rate_limit_tau2_llm_calls(max_calls_per_minute: float) -> None:
    """Throttle every LLM call tau2 makes (agent + user simulator both go through
    tau2.utils.llm_utils.generate -> the `completion` name bound there) to at most
    `max_calls_per_minute`, spaced evenly.

    Needed because tau2's own retry (DEFAULT_MAX_RETRIES=3) assumes transient errors,
    not a hard per-minute account quota: found live 2026-09-23 collecting airline states
    with a fresh OpenRouter account — every one of 15 episodes was rate-limited to death
    (litellm.RateLimitError, "new accounts are limited to 20 requests per minute") because
    3 retries can't outlast a 60s window that 4 concurrent workers were all hammering at
    once. Must patch the NAME `tau2.utils.llm_utils.completion`, not `litellm.completion`:
    that module did `from litellm import completion`, which copies the reference at import
    time, so reassigning litellm.completion afterward would not affect it.
    """
    import threading
    import time as time_module

    import tau2.utils.llm_utils as llm_utils

    original = llm_utils.completion
    min_interval = 60.0 / max_calls_per_minute
    lock = threading.Lock()
    last_call = [0.0]

    def throttled(*args, **kwargs):
        with lock:
            wait = min_interval - (time_module.monotonic() - last_call[0])
            if wait > 0:
                time_module.sleep(wait)
            last_call[0] = time_module.monotonic()
        return original(*args, **kwargs)

    llm_utils.completion = throttled


def cap_max_tokens(max_tokens: int) -> None:
    """Cap every tau2 LLM call's max_tokens (default: uncapped -> the model's own ceiling,
    e.g. 65536 for gpt-5.6).

    Found live 2026-09-23 collecting airline states: OpenRouter pre-authorizes credits
    against the WORST CASE max_tokens on every call, before any tokens are generated or
    billed -- "you requested up to 65536 tokens, but can only afford 32405" (HTTP 402). A
    single conversational turn or tool call realistically needs a few hundred tokens, not
    65536; leaving it uncapped means the account's remaining balance gates far below what
    it can actually afford in real usage. Same monkeypatch target as
    rate_limit_tau2_llm_calls, for the same reason (the bound name, not the module).
    """
    import tau2.utils.llm_utils as llm_utils

    original = llm_utils.completion

    def capped(*args, **kwargs):
        kwargs.setdefault("max_tokens", max_tokens)
        return original(*args, **kwargs)

    llm_utils.completion = capped
