import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "analyze_decisions", Path(__file__).parent.parent / "scripts" / "analyze_decisions.py")
analyze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze)


def _row(state, rep, error=None, choice="a"):
    return {"decider": "d", "state_id": state, "repeat": rep, "error": error, "choice": choice}


def test_resolve_attempts_counts_each_call_once_and_separates_billing_errors():
    billing = "litellm.APIError: OpenrouterException - {\"code\":402,\"reason\":\"in_flight_budget_exhausted\"}"
    rows = [
        _row("s1", 0, error=billing), _row("s1", 0),                  # retried after 402 -> success
        _row("s2", 0, error="NoDecisionError('no decide_next_action call')"),  # decider failure
        _row("s3", 0, error=billing),                                  # still missing
    ]
    resolved, stats = analyze.resolve_attempts(rows)
    assert len(resolved) == 3
    assert [r["error"] is None for r in resolved].count(True) == 1
    assert stats["d"]["attempts"] == 4 and stats["d"]["infra_errors"] == 2
    assert stats["d"]["decider_failures"] == 1 and stats["d"]["unresolved_infra"] == 1


def test_resolve_attempts_keeps_a_decider_failure_even_if_an_old_retry_succeeded():
    # Older files hold re-rolls of decider failures; the first real attempt is the outcome.
    rows = [_row("s1", 0, error="TypeError(\"'NoneType' object is not subscriptable\")"), _row("s1", 0)]
    resolved, stats = analyze.resolve_attempts(rows)
    assert len(resolved) == 1 and resolved[0]["error"] is not None
    assert stats["d"]["decider_failures"] == 1 and stats["d"]["infra_errors"] == 0


def test_infra_error_classification():
    from dwg.errors import is_infra_error, is_out_of_credits

    billing = 'litellm.APIError: OpenrouterException - {"error":{"message":"...","code":402}}'
    assert is_infra_error(billing) and is_out_of_credits(billing)
    key_limit = ('litellm.APIError: APIError: OpenrouterException - {"error":{"message":"Key limit exceeded '
                 '(total limit). Manage it using https://openrouter.ai/workspaces/default/keys/x","code":403}}')
    assert is_infra_error(key_limit) and is_out_of_credits(key_limit)
    assert not is_infra_error('{"error":{"message":"flagged by moderation","code":403}}')
    assert is_infra_error("JevError('Jev returned HTTP 520: error code: 520')")
    assert is_infra_error("litellm.RateLimitError: status 429")
    # token counts and JSON positions are not status codes
    too_long = "JevError('Jev returned HTTP 422: {\"detail\":\"branch too long: 4020 tokens\"}')"
    assert not is_infra_error(too_long) and not is_out_of_credits(too_long)
    assert not is_infra_error("JSONDecodeError('Extra data: line 1 column 402 (char 402)')")


def test_pooled_energy_sums_every_run_block():
    from dwg.runfiles import pooled_energy

    dmeta = {
        "energy_block": {"joules": 200.0, "seconds": 10.0, "calls": 2}, "gpu_idle_watts": 5.0,
        "previous_runs": [{"energy_block": {"joules": 100.0, "seconds": 4.0, "calls": 2}, "gpu_idle_watts": 10.0}],
    }
    p = pooled_energy(dmeta)
    assert p["calls"] == 4 and p["runs"] == 2 and p["gross_j"] == 75.0
    assert p["net_j"] == ((200 - 50) + (100 - 40)) / 4
    assert pooled_energy({}) is None


def test_load_calls_counts_non_escalated_cascade_calls_as_free(tmp_path):
    import json

    from dwg.runfiles import load_calls

    rows = [
        {"decider": "cascade-kev-4b-t0.9", "escalated": False, "cost_usd": None, "error": None},
        {"decider": "cascade-kev-4b-t0.9", "escalated": True, "cost_usd": 3e-4, "error": None},
        {"decider": "kev-4b", "escalated": False, "cost_usd": None, "error": None},
    ]
    (tmp_path / "calls-x.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    loaded = load_calls(tmp_path)
    assert [r["cost_usd"] for r in loaded] == [0.0, 3e-4, None]
