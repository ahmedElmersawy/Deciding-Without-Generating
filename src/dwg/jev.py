"""Thin HTTP client for Jev (typesafe.ai's System 1 decider), routed through OpenRouter.

Jev answers typed questions (choice / score / noul) over a `state` string or JSON
blob — it never generates free text. OpenRouter exposes it as a "decisions model"
on a dedicated endpoint (`POST /api/alpha/decisions`), separate from chat/completions —
confirmed against a live call, see DECISIONS.md (2026-09-22). No direct api.typesafe.ai
path is supported.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_BASE_URL = "https://openrouter.ai/api"
DEFAULT_MODEL = "~typesafe/jev-latest"
DECISIONS_PATH = "/alpha/decisions"


class JevError(RuntimeError):
    """Raised for any non-2xx response or malformed answer from Jev."""


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    probabilities: dict[str, float]
    vendor_confidence: float
    model: str
    usage: dict[str, int]

    @property
    def confidence(self) -> float:
        """p(chosen option) — the calibration-comparable confidence (DECISIONS.md 2026-09-21)."""
        return self.probabilities[self.choice]


@dataclass(frozen=True)
class ScoreAnswer:
    score: float
    legend: Any
    probabilities: dict[str, float]
    vendor_confidence: float
    model: str
    usage: dict[str, int]


@dataclass(frozen=True)
class NoulAnswer:
    p_yes: float
    model: str
    usage: dict[str, int]

    @property
    def confidence(self) -> float:
        """noul has no vendor confidence field; derive it ourselves (CHECKS.md #2)."""
        return max(self.p_yes, 1 - self.p_yes)


class JevDecider:
    """Calls Jev's `systemone` endpoint through OpenRouter.

    Credentials come from `OPENROUTER_API_KEY` (required) and optionally
    `OPENROUTER_API_BASE` (defaults to https://openrouter.ai/api), unless passed
    explicitly.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise JevError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        self.base_url = (base_url or os.environ.get("OPENROUTER_API_BASE") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model
        self.timeout = timeout
        self.session = session or requests.Session()
        self.last_response: dict[str, Any] | None = None  # raw response, cached for audit

    def ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Send one or more typed questions about `state`. Returns the raw parsed JSON body."""
        url = f"{self.base_url}{DECISIONS_PATH}"
        payload = {"state": state, "model": self.model, "questions": questions}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise JevError(f"Jev request failed: {exc}") from exc

        if resp.status_code != 200:
            raise JevError(f"Jev returned HTTP {resp.status_code}: {resp.text[:500]}")

        body = resp.json()
        self.last_response = body
        return body

    def choice(
        self,
        state: Any,
        name: str,
        instructions: str,
        criteria: dict[str, str],
    ) -> ChoiceAnswer:
        body = self.ask(state, {name: {"type": "choice", "instructions": instructions, "criteria": criteria}})
        answer = _extract_answer(body, name)
        return ChoiceAnswer(
            choice=answer["choice"],
            probabilities=answer["probabilities"],
            vendor_confidence=answer["confidence"],
            model=body["model"],
            usage=body["usage"],
        )

    def score(
        self,
        state: Any,
        name: str,
        instructions: str,
        criteria: list[str],
    ) -> ScoreAnswer:
        body = self.ask(state, {name: {"type": "score", "instructions": instructions, "criteria": criteria}})
        answer = _extract_answer(body, name)
        return ScoreAnswer(
            score=answer["score"],
            legend=answer["legend"],
            probabilities=answer["probabilities"],
            vendor_confidence=answer["confidence"],
            model=body["model"],
            usage=body["usage"],
        )

    def noul(self, state: Any, name: str, instructions: str) -> NoulAnswer:
        body = self.ask(state, {name: {"type": "noul", "instructions": instructions}})
        answer = _extract_answer(body, name)
        return NoulAnswer(p_yes=answer["noul"], model=body["model"], usage=body["usage"])


def _extract_answer(body: dict[str, Any], name: str) -> dict[str, Any]:
    try:
        return body["answers"][name]
    except KeyError as exc:
        raise JevError(f"Jev response missing answer '{name}': {body}") from exc
