import json
from pathlib import Path

import pytest

from benchline_pipelines.normalize.cache import JsonlCache
from benchline_pipelines.normalize.checks import LlmParse, interpret
from benchline_pipelines.normalize.llm import LlmNormalizer, LlmSettings
from tests.llm_helpers import ZYPREXA, fake_response, normalizer


def test_brand_answer_is_accepted_but_flagged_for_review(tmp_path: Path) -> None:
    result = normalizer(tmp_path, lambda m: fake_response(ZYPREXA)).normalize("ZYPREXA 15 MG TABLET")
    assert result is not None
    assert (result.ingredient, result.is_brand, result.strength, result.form) == ("OLANZAPINE", True, "15 MG", "TABLET")
    assert not result.grounded and result.needs_review


def test_ingredient_found_in_the_text_is_grounded_and_needs_no_review(tmp_path: Path) -> None:
    reply = {"ingredient": "MISOPROSTOL", "is_brand": False, "strength": "100 MCG", "form": "TABLET"}
    result = normalizer(tmp_path, lambda m: fake_response(reply)).normalize("MISOPROSTOL 100 MCG TABLET")
    assert result is not None and result.grounded and not result.needs_review


def test_a_strength_the_description_does_not_contain_is_discarded(tmp_path: Path) -> None:
    reply = {**ZYPREXA, "strength": "99 MG"}
    result = normalizer(tmp_path, lambda m: fake_response(reply)).normalize("ZYPREXA 15 MG TABLET")
    assert result is not None and result.strength == "" and "strength" in result.reason


@pytest.mark.parametrize("answer", [
    "not json at all", {"is_brand": True}, "[]"])
def test_unreadable_answers_are_failures_and_do_not_raise(tmp_path: Path, answer) -> None:  # type: ignore[no-untyped-def]
    n = normalizer(tmp_path, lambda m: fake_response(answer))
    assert n.normalize("SM ALLERGY RELIEF 50 MCG SPRAY") is None
    assert (n.stats.failures, n.stats.declined) == (1, 0)


@pytest.mark.parametrize("answer", [{"ingredient": "UNKNOWN", "is_brand": True}, {"ingredient": "", "is_brand": False}])
def test_unknown_is_a_decline_not_an_error(tmp_path: Path, answer) -> None:  # type: ignore[no-untyped-def]
    n = normalizer(tmp_path, lambda m: fake_response(answer))
    assert n.normalize("SM ALLERGY RELIEF 50 MCG SPRAY") is None
    assert (n.stats.failures, n.stats.declined, n.stats.calls) == (0, 1, 1)


def test_a_decline_is_remembered_so_it_is_not_paid_for_twice(tmp_path: Path) -> None:
    first = normalizer(tmp_path, lambda m: fake_response({"ingredient": "UNKNOWN", "is_brand": True}))
    first.normalize("SM ALLERGY RELIEF 50 MCG SPRAY")
    again = LlmNormalizer(first.settings, JsonlCache(tmp_path / "c.jsonl"), completion=lambda m: pytest.fail("called"))
    assert again.normalize("SM ALLERGY RELIEF 50 MCG SPRAY") is None
    assert again.stats.declined == 1 and again.stats.calls == 0


def test_declines_do_not_trip_the_circuit_breaker(tmp_path: Path) -> None:
    n = normalizer(tmp_path, lambda m: fake_response({"ingredient": "UNKNOWN", "is_brand": True}),
                   max_consecutive_failures=2)
    for i in range(6):
        n.normalize(f"BRAND{i} 5 MG TABLET")
    assert n.stats.declined == 6 and n.stats.skipped_circuit == 0


def test_offline_mode_uses_the_cache_and_never_calls_the_model(tmp_path: Path) -> None:
    online = normalizer(tmp_path, lambda m: fake_response(ZYPREXA))
    online.normalize("ZYPREXA 15 MG TABLET")
    offline = LlmNormalizer(LlmSettings(model="fake", offline=True), JsonlCache(tmp_path / "c.jsonl"),
                            completion=lambda m: pytest.fail("called"))
    assert offline.normalize("ZYPREXA 15 MG TABLET") is not None
    assert offline.normalize("SOMETHING NEW 5 MG TABLET") is None
    assert (offline.stats.cached, offline.stats.skipped_offline, offline.stats.calls) == (1, 1, 0)


def test_a_failing_provider_does_not_stop_the_run(tmp_path: Path) -> None:
    def boom(_m):  # type: ignore[no-untyped-def]
        raise TimeoutError("provider down")
    n = normalizer(tmp_path, boom)
    assert n.normalize("ZYPREXA 15 MG TABLET") is None and n.stats.failures == 1


def test_json_in_a_code_fence_is_accepted(tmp_path: Path) -> None:
    fenced = "```json\n" + json.dumps(ZYPREXA) + "\n```"
    assert normalizer(tmp_path, lambda m: fake_response(fenced)).normalize("ZYPREXA 15 MG TABLET") is not None


def test_second_lookup_comes_from_the_cache_and_costs_nothing(tmp_path: Path) -> None:
    calls: list[int] = []

    def counting(_messages):  # type: ignore[no-untyped-def]
        calls.append(1)
        return fake_response(ZYPREXA)

    n = normalizer(tmp_path, counting)
    first = n.normalize("ZYPREXA 15 MG TABLET")
    again = LlmNormalizer(n.settings, JsonlCache(tmp_path / "c.jsonl"), completion=lambda m: pytest.fail("called"))
    second = again.normalize("ZYPREXA 15 MG TABLET")
    assert first and second and second.cached and second.cost_usd == 0.0 and len(calls) == 1


def test_spending_cap_stops_further_calls(tmp_path: Path) -> None:
    n = normalizer(tmp_path, lambda m: fake_response(ZYPREXA, cost=0.6), max_usd=1.0)
    results = [n.normalize(f"BRAND{i} 15 MG TABLET") for i in range(4)]
    assert [r is not None for r in results] == [True, True, False, False]
    assert n.stats.skipped_budget == 2 and n.stats.calls == 2


def test_the_prompt_asks_for_unknown_rather_than_a_guess(tmp_path: Path) -> None:
    seen: list[list[dict[str, str]]] = []

    def recording(messages):  # type: ignore[no-untyped-def]
        seen.append(messages)
        return fake_response(ZYPREXA)

    normalizer(tmp_path, recording).normalize("ZYPREXA 15 MG TABLET")
    system, user = seen[0]
    assert system["role"] == "system" and "UNKNOWN" in system["content"]
    assert user == {"role": "user", "content": "ZYPREXA 15 MG TABLET"}


def test_interpret_strips_salt_words_from_the_models_ingredient() -> None:
    parsed = LlmParse(ingredient="Atorvastatin Calcium", is_brand=True, strength="20 mg", form="tablet")
    name, strength, form, grounded, _ = interpret("LIPITOR 20 MG TABLET", parsed)  # type: ignore[misc]
    assert (name, strength, form, grounded) == ("ATORVASTATIN", "20 MG", "TABLET", False)


# --- the real LiteLLM Router, offline through LiteLLM's own mock_response ---------------------

def test_real_litellm_router_path_works_offline(tmp_path: Path) -> None:
    settings = LlmSettings(model="gpt-4o-mini", extra={"mock_response": json.dumps(ZYPREXA)})
    result = LlmNormalizer(settings, JsonlCache(tmp_path / "c.jsonl")).normalize("ZYPREXA 15 MG TABLET")
    assert result is not None and result.ingredient == "OLANZAPINE" and result.tokens > 0


def test_router_falls_back_when_the_primary_model_fails(tmp_path: Path) -> None:
    settings = LlmSettings(model="gpt-4o-mini", fallback_model="gpt-4o", retries=0,
                           extra={"mock_testing_fallbacks": True, "mock_response": json.dumps(ZYPREXA)})
    n = LlmNormalizer(settings, JsonlCache(tmp_path / "c.jsonl"))
    result = n.normalize("ZYPREXA 15 MG TABLET")
    assert result is not None and n.stats.failures == 0
