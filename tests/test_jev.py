import pytest

from dwg.jev import ChoiceAnswer, JevDecider, JevError, NoulAnswer


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_request = None

    def post(self, url, json, headers, timeout):
        self.last_request = {"url": url, "json": json, "headers": headers, "timeout": timeout}
        return self._response


def _decider(response: _FakeResponse) -> JevDecider:
    return JevDecider(api_key="test-key", session=_FakeSession(response))


def test_choice_routes_through_openrouter_with_bearer_auth():
    body = {
        "model": "jev-1.13.0",
        "answers": {"pick_tool": {"choice": "search", "confidence": 0.8, "probabilities": {"search": 0.9, "noop": 0.1}}},
        "usage": {"input_tokens": 42, "output_tokens": 0},
    }
    decider = _decider(_FakeResponse(200, body))

    answer = decider.choice(
        state="user wants to find X",
        name="pick_tool",
        instructions="which tool should run next?",
        criteria={"search": "look it up", "noop": "do nothing"},
    )

    assert isinstance(answer, ChoiceAnswer)
    assert answer.choice == "search"
    assert answer.confidence == pytest.approx(0.9)  # probabilities[choice], not vendor confidence
    assert answer.vendor_confidence == pytest.approx(0.8)
    assert answer.model == "jev-1.13.0"

    request = decider.session.last_request
    assert request["url"] == "https://openrouter.ai/api/alpha/decisions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"]["model"] == "~typesafe/jev-latest"


def test_noul_confidence_is_derived_not_from_vendor():
    body = {
        "model": "jev-1.13.0",
        "answers": {"should_retry": {"noul": 0.2}},
        "usage": {"input_tokens": 10, "output_tokens": 0},
    }
    decider = _decider(_FakeResponse(200, body))

    answer = decider.noul(state="last call failed", name="should_retry", instructions="retry?")

    assert isinstance(answer, NoulAnswer)
    assert answer.p_yes == pytest.approx(0.2)
    assert answer.confidence == pytest.approx(0.8)  # max(p, 1-p)


def test_non_200_raises_jev_error():
    decider = _decider(_FakeResponse(401, {"error": "invalid key"}))

    with pytest.raises(JevError, match="HTTP 401"):
        decider.choice(state="x", name="q", instructions="i", criteria={"a": "a"})


def test_missing_api_key_raises_before_any_request(monkeypatch):
    # tau2 calls load_dotenv() on import, so a real .env key can leak in from other tests.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(JevError, match="OPENROUTER_API_KEY"):
        JevDecider(api_key=None, session=_FakeSession(_FakeResponse(200, {})))
