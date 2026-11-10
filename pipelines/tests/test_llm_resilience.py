"""How the LLM client behaves when things go wrong: refusals, outages, odd models, temperature."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from benchline_pipelines.normalize.cache import JsonlCache
from benchline_pipelines.normalize.llm import LlmNormalizer, LlmSettings
from tests.llm_helpers import ZYPREXA, fake_response, normalizer


def failing(_messages):  # type: ignore[no-untyped-def]
    raise RuntimeError("Budget has been exceeded! Current cost: 0.0002, Max budget: 0.0001")


def test_the_provider_error_text_is_kept_for_a_person_to_read(tmp_path: Path) -> None:
    n = normalizer(tmp_path, failing)
    n.normalize("ZYPREXA 15 MG TABLET")
    assert n.stats.errors == ["RuntimeError: Budget has been exceeded! Current cost: 0.0002, Max budget: 0.0001"]


def test_long_error_messages_are_truncated_and_duplicates_collapse(tmp_path: Path) -> None:
    def long_error(_m):  # type: ignore[no-untyped-def]
        raise RuntimeError("x" * 1000)
    n = normalizer(tmp_path, long_error, max_consecutive_failures=99)
    for i in range(3):
        n.normalize(f"BRAND{i} 5 MG TABLET")
    assert len(n.stats.errors) == 1 and len(n.stats.errors[0]) < 330


def test_after_repeated_failures_the_model_is_left_alone_for_the_rest_of_the_run(tmp_path: Path) -> None:
    calls: list[int] = []

    def counting_failure(_m):  # type: ignore[no-untyped-def]
        calls.append(1)
        raise RuntimeError("refused")

    n = normalizer(tmp_path, counting_failure, max_consecutive_failures=3)
    for i in range(10):
        assert n.normalize(f"BRAND{i} 5 MG TABLET") is None
    assert len(calls) == 3
    assert (n.stats.failures, n.stats.skipped_circuit) == (3, 7)


def test_a_success_resets_the_failure_streak(tmp_path: Path) -> None:
    answers: Iterator[dict[str, object] | str] = iter(["bad", "bad", ZYPREXA, "bad", "bad", ZYPREXA])
    n = normalizer(tmp_path, lambda _m: fake_response(next(answers)), max_consecutive_failures=3)
    results = [n.normalize(f"BRAND{i} 15 MG TABLET") for i in range(6)]
    assert [r is not None for r in results] == [False, False, True, False, False, True]
    assert n.stats.skipped_circuit == 0


def test_cache_without_a_path_never_touches_the_disk() -> None:
    cache = JsonlCache(None)
    cache.put("k", {"a": 1})
    assert cache.get("k") == {"a": 1}


class FakeRouterRateLimit(ValueError):
    """Stands in for LiteLLM's RouterRateLimitError, which is a ValueError subclass."""


def test_a_provider_error_that_is_a_valueerror_is_still_a_failed_call_not_a_bad_answer(
        tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    def cooldown(_m):  # type: ignore[no-untyped-def]
        raise FakeRouterRateLimit("No deployments available for selected model")
    n = normalizer(tmp_path, cooldown, max_consecutive_failures=2)
    with caplog.at_level("WARNING"):
        n.normalize("BRAND1 5 MG TABLET")
        n.normalize("BRAND2 5 MG TABLET")
    assert "model call failed" in caplog.text and "unusable model answer" not in caplog.text
    assert n.stats.errors[0].startswith("FakeRouterRateLimit: No deployments available")
    assert n.normalize("BRAND3 5 MG TABLET") is None and n.stats.skipped_circuit == 1


def test_unusable_answers_do_not_trip_the_circuit_breaker(tmp_path: Path) -> None:
    n = normalizer(tmp_path, lambda _m: fake_response("not json"), max_consecutive_failures=2)
    for i in range(5):
        n.normalize(f"BRAND{i} 5 MG TABLET")
    assert n.stats.failures == 5 and n.stats.skipped_circuit == 0


def test_cooldown_is_disabled_only_when_there_is_no_fallback(tmp_path: Path) -> None:
    from benchline_pipelines.normalize.llm import ALIAS
    solo = LlmNormalizer(LlmSettings(model="gpt-4o-mini"), JsonlCache(None))
    paired = LlmNormalizer(LlmSettings(model="gpt-4o-mini", fallback_model="gpt-4o"), JsonlCache(None))
    assert solo._build_router().disable_cooldowns is True and paired._build_router().disable_cooldowns is False
    assert ALIAS == "normalizer"


def test_a_missing_response_is_a_failed_call_with_a_clear_message(tmp_path: Path) -> None:
    """LiteLLM once returned None for a refused call; that must read as a failure, not an AttributeError."""
    n = normalizer(tmp_path, lambda _m: None, max_consecutive_failures=2)
    assert n.normalize("BRAND1 5 MG TABLET") is None
    assert n.stats.errors == ["RuntimeError: the model client returned no response"]
    n.normalize("BRAND2 5 MG TABLET")
    assert n.normalize("BRAND3 5 MG TABLET") is None and n.stats.skipped_circuit == 1


def test_the_client_does_not_set_litellm_drop_params(tmp_path: Path) -> None:
    import litellm
    litellm.drop_params = False
    LlmNormalizer(LlmSettings(model="gpt-4o-mini"), JsonlCache(None))._build_router()
    assert litellm.drop_params is False


def mocked(model: str, tmp_path: Path, **kwargs) -> LlmNormalizer:  # type: ignore[no-untyped-def]
    reply = json.dumps({"ingredient": "OLANZAPINE", "is_brand": True, "strength": "15 MG", "form": "TABLET"})
    settings = LlmSettings(model=model, extra={"mock_response": reply}, **kwargs)
    return LlmNormalizer(settings, JsonlCache(None))


@pytest.mark.parametrize("model", ["anthropic/claude-haiku-5-5", "anthropic/claude-sonnet-5-5"])
def test_newest_claude_models_work_even_though_they_reject_temperature_zero(tmp_path: Path, model: str) -> None:
    n = mocked(model, tmp_path)
    first = n.normalize("ZYPREXA 15 MG TABLET")
    second = n.normalize("DROXIA 400 MG CAPSULE")
    assert first is not None and second is not None and n.stats.failures == 0
    assert n._send_temperature is False        # dropped after the first rejection, not retried every call


def test_models_that_accept_temperature_zero_keep_sending_it(tmp_path: Path) -> None:
    n = mocked("openai/gpt-4o-mini", tmp_path)
    assert n.normalize("ZYPREXA 15 MG TABLET") is not None and n._send_temperature is True


def test_temperature_can_be_switched_off_by_setting(tmp_path: Path) -> None:
    assert mocked("openai/gpt-4o-mini", tmp_path, temperature=None)._send_temperature is False


def test_temperature_setting_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BENCHLINE_LLM_MODEL", "openai/gpt-4o-mini")
    monkeypatch.delenv("BENCHLINE_LLM_TEMPERATURE", raising=False)
    assert LlmSettings.from_env().temperature == 0.0        # type: ignore[union-attr]
    monkeypatch.setenv("BENCHLINE_LLM_TEMPERATURE", "none")
    assert LlmSettings.from_env().temperature is None       # type: ignore[union-attr]
    monkeypatch.setenv("BENCHLINE_LLM_TEMPERATURE", "0.3")
    assert LlmSettings.from_env().temperature == 0.3        # type: ignore[union-attr]
