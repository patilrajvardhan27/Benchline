import json
from pathlib import Path

import pandas as pd
import pytest

from benchline_pipelines.normalize.cache import JsonlCache
from benchline_pipelines.normalize.llm import LlmNormalizer, LlmSettings
from benchline_pipelines.normalize.openfda import FdaIndex, FdaProduct, fda_form
from benchline_pipelines.normalize.pipeline import normalize_item, run

OLANZAPINE = {"ingredient": "OLANZAPINE", "is_brand": True, "strength": "15 MG", "form": "TABLET"}


def index() -> FdaIndex:
    return FdaIndex(
        by_ndc={
            "00000000001": FdaProduct("Synthroid", ("LEVOTHYROXINE",), "TABLET", (), "NDA", ("50 MCG",)),
            "00000000002": FdaProduct("Levothyroxine", ("LEVOTHYROXINE",), "TABLET", (), "ANDA", ("50 MCG",)),
            "00000000003": FdaProduct("Metformin", ("METFORMIN",), "TABLET", ("ER",), "ANDA", ("500 MG",)),
        },
        vocabulary=frozenset({"LEVOTHYROXINE", "METFORMIN", "ASPIRIN"}),
    )


def llm(tmp_path: Path, answer: dict[str, object] | None = None) -> LlmNormalizer:
    from types import SimpleNamespace
    message = SimpleNamespace(content=json.dumps(answer or OLANZAPINE))
    reply = SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(total_tokens=100),
                            _hidden_params={"response_cost": 0.0001}, model="m")
    return LlmNormalizer(LlmSettings(model="m"), JsonlCache(tmp_path / "c.jsonl"), completion=lambda _m: reply)


def test_openfda_decides_when_it_knows_the_ndc_and_separates_brand_from_generic() -> None:
    brand = normalize_item("00000000001", "SYNTHROID 50 MCG TABLET", index(), None)
    generic = normalize_item("00000000002", "LEVOTHYROXINE SODIUM 50 MCG TAB", index(), None)
    assert brand.method == generic.method == "openfda"
    assert brand.group_name == "LEVOTHYROXINE 50 MCG TABLET (BRAND)"
    assert generic.group_name == "LEVOTHYROXINE 50 MCG TABLET"


def test_modifiers_from_either_source_are_kept() -> None:
    item = normalize_item("00000000003", "METFORMIN HCL 500 MG TABLET", index(), None)
    assert item.group_name == "METFORMIN ER 500 MG TABLET"


def test_rules_decide_when_openfda_has_no_record_but_the_name_is_known() -> None:
    item = normalize_item("99999999999", "ASPIRIN 81 MG TAB", index(), None)
    assert (item.method, item.group_name, item.needs_review) == ("rules", "ASPIRIN 81 MG TABLET", False)


def test_model_handles_the_rest_and_a_brand_is_flagged(tmp_path: Path) -> None:
    item = normalize_item("99999999998", "ZYPREXA 15 MG TABLET", index(), llm(tmp_path))
    assert (item.method, item.group_name, item.needs_review) == ("llm", "OLANZAPINE 15 MG TABLET (BRAND)", True)


def test_without_a_model_the_item_keeps_its_old_group_and_is_flagged() -> None:
    item = normalize_item("99999999998", "ZYPREXA 15 MG TABLET", index(), None)
    assert item.method == "unresolved" and item.group_name == "ZYPREXA 15 MG TABLET" and item.needs_review


def test_a_disagreement_between_description_and_openfda_is_flagged() -> None:
    item = normalize_item("00000000003", "METFORMIN 500 MG CAPSULE", index(), None)
    assert item.needs_review and "openFDA" in item.reason


def test_strength_falls_back_to_openfda_when_the_description_has_none() -> None:
    item = normalize_item("00000000002", "LEVOTHYROXINE TABLET", index(), None)
    assert "50 MCG" in item.group_name


def test_run_writes_group_map_review_file_and_an_honest_report(tmp_path: Path) -> None:
    silver = tmp_path / "nadac.parquet"
    pd.DataFrame({"ndc11": ["00000000001", "00000000002", "99999999999", "99999999998"],
                  "description": ["SYNTHROID 50 MCG TABLET", "LEVOTHYROXINE SODIUM 50 MCG TAB",
                                  "ASPIRIN 81 MG TAB", "ZYPREXA 15 MG TABLET"]}).to_parquet(silver)
    report = run(silver, index(), tmp_path, llm(tmp_path), max_llm=None)

    table = pd.read_parquet(tmp_path / "item_groups.parquet")
    assert set(table["method"]) == {"openfda", "rules", "llm"}
    assert report.ndcs == 4 and report.by_method == {"openfda": 2, "rules": 1, "llm": 1}
    assert report.llm["calls"] == 1 and report.llm["cost_usd"] > 0
    assert len(pd.read_csv(tmp_path / "needs_review.csv")) == report.needs_review == 1
    assert json.loads((tmp_path / "normalize_report.json").read_text())["ndcs"] == 4


def test_max_llm_caps_how_many_descriptions_reach_the_model(tmp_path: Path) -> None:
    silver = tmp_path / "nadac.parquet"
    pd.DataFrame({"ndc11": [f"9999999999{n}" for n in range(5)],
                  "description": [f"BRAND{n} 15 MG TABLET" for n in range(5)]}).to_parquet(silver)
    model = llm(tmp_path)
    report = run(silver, index(), tmp_path, model, max_llm=2)
    assert model.stats.calls == 2 and report.by_method == {"llm": 2, "unresolved": 3}


@pytest.mark.parametrize(("raw", "expected"), [
    ("TABLET, FILM COATED, EXTENDED RELEASE", ("TABLET", ("ER",))),
    ("TABLET, ORALLY DISINTEGRATING", ("TABLET", ("ODT",))),
    ("CAPSULE, DELAYED RELEASE", ("CAPSULE", ("DR",))),
    ("INJECTION, SOLUTION", ("INJECTION", ())),
    ("", ("", ())),
])
def test_openfda_dosage_forms_map_to_ours(raw: str, expected: tuple[str, tuple[str, ...]]) -> None:
    assert fda_form(raw) == expected


def test_max_llm_counts_refused_calls_too(tmp_path: Path) -> None:
    """A gateway that refuses everything must not be asked about every remaining item."""
    silver = tmp_path / "nadac.parquet"
    pd.DataFrame({"ndc11": [f"9999999999{n}" for n in range(8)],
                  "description": [f"BRAND{n} 15 MG TABLET" for n in range(8)]}).to_parquet(silver)
    attempts: list[int] = []

    def refuse(_m):  # type: ignore[no-untyped-def]
        attempts.append(1)
        raise RuntimeError("refused")

    model = LlmNormalizer(LlmSettings(model="m", max_consecutive_failures=99),
                          JsonlCache(tmp_path / "c.jsonl"), completion=refuse)
    report = run(silver, index(), tmp_path, model, max_llm=3)
    assert len(attempts) == 3 and report.by_method == {"unresolved": 8}


def test_score_llm_reports_progress_and_scores_against_openfda(tmp_path: Path) -> None:
    from benchline_pipelines.normalize.evaluate import score_llm
    rows = pd.DataFrame({"ndc11": ["00000000001", "00000000002"],
                         "description": ["SYNTHROID 50 MCG TABLET", "LEVOTHYROXINE 50 MCG TAB"]})
    answer = {"ingredient": "LEVOTHYROXINE", "is_brand": True, "strength": "50 MCG", "form": "TABLET"}
    seen: list[tuple[int, int]] = []
    score = score_llm(rows, index(), llm(tmp_path, answer), lambda done, total: seen.append((done, total)))
    assert seen == [(1, 2), (2, 2)]
    assert (score.sampled, score.answered, score.ingredient_correct) == (2, 2, 2)


def test_lenient_match_ignores_salt_names_but_not_different_drugs() -> None:
    from benchline_pipelines.normalize.evaluate import ingredient_core
    assert ingredient_core({"FLUOCINOLONE"}) == ingredient_core({"FLUOCINOLONE ACETONIDE"})
    assert ingredient_core({"FLUORIDE"}) == ingredient_core({"SODIUM FLUORIDE"})
    assert ingredient_core({"AMPHETAMINE", "DEXTROAMPHETAMINE"}) == ingredient_core(
        {"AMPHETAMINE", "AMPHETAMINE ASPARTATE", "DEXTROAMPHETAMINE", "DEXTROAMPHETAMINE SACCHARATE"})
    assert ingredient_core({"SIMETHICONE"}) != ingredient_core({"DIMETHICONE"})
    assert ingredient_core({"SODIUM CHLORIDE"}) != ingredient_core({"SODIUM BICARBONATE"})


def test_brand_answers_are_scored_separately_from_answers_named_in_the_text(tmp_path: Path) -> None:
    from benchline_pipelines.normalize.evaluate import score_llm
    rows = pd.DataFrame({"ndc11": ["00000000001", "00000000002"],
                         "description": ["SYNTHROID 50 MCG TABLET", "LEVOTHYROXINE 50 MCG TAB"]})
    answer = {"ingredient": "LEVOTHYROXINE", "is_brand": True, "strength": "50 MCG", "form": "TABLET"}
    score = score_llm(rows, index(), llm(tmp_path, answer))
    assert (score.answered, score.grounded, score.knowledge_answered) == (2, 1, 1)
    assert (score.ingredient_correct, score.lenient_correct, score.knowledge_lenient_correct) == (2, 2, 1)


def test_cached_cases_are_exactly_the_descriptions_already_answered(tmp_path: Path) -> None:
    from benchline_pipelines.normalize.evaluate import cached_cases
    model = llm(tmp_path)
    model.normalize("SYNTHROID 50 MCG TABLET")
    rows = pd.DataFrame({"ndc11": ["00000000001", "00000000002", "00000000003", "99999999999"],
                         "description": ["SYNTHROID 50 MCG TABLET", "SYNTHROID 50 MCG TABLET",
                                         "METFORMIN 500 MG TABLET", "SYNTHROID 50 MCG TABLET"]})
    cases = cached_cases(rows, index(), model)
    assert list(cases["description"]) == ["SYNTHROID 50 MCG TABLET"]   # once, only if answered and checkable
