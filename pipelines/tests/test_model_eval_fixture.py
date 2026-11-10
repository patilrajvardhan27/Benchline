"""The model evaluation, reproduced from the saved answers. Runs with no key, no network and no cost.

The fixture holds every answer from one run of claude-haiku-5-5 on 200 hard cases (NDCs that openFDA knows and
the rules did not recognise), with openFDA's ingredient for each. The verdicts are recomputed here from the raw
ingredient strings, so the numbers in the docs can be checked by anyone with a clone of the repository.
"""

import csv
from pathlib import Path

import pytest

from benchline_pipelines.normalize.evaluate import ingredient_core, ingredient_set
from benchline_pipelines.normalize.rules import clean

FIXTURE = Path(__file__).parent / "fixtures" / "model_eval_claude_haiku_5_5.csv"


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    with FIXTURE.open() as f:
        return list(csv.DictReader(f))


def test_the_run_is_complete(rows: list[dict[str, str]]) -> None:
    outcomes = [r["outcome"] for r in rows]
    assert len(rows) == 188 and outcomes.count("answered") == 162 and outcomes.count("declined") == 26
    assert all(r["openfda_ingredient"] for r in rows)        # every case has an answer key
    assert len({r["description"] for r in rows}) == 188     # scored once per description


def test_headline_numbers_recomputed_from_the_raw_answers(rows: list[dict[str, str]]) -> None:
    answered = [r for r in rows if r["outcome"] == "answered"]
    truth = {r["description"]: ingredient_set(r["openfda_ingredient"]) for r in answered}
    exact = sum(ingredient_set(r["model_ingredient"]) == truth[r["description"]] for r in answered)
    same = sum(ingredient_core(ingredient_set(r["model_ingredient"])) == ingredient_core(truth[r["description"]])
               for r in answered)
    assert (exact, same) == (134, 154)                      # 82.7% exact, 95.1% same drug
    assert all((r["exact"] == "True") == (ingredient_set(r["model_ingredient"]) == truth[r["description"]])
               for r in answered)                           # the stored verdicts agree with the recomputation


def test_brand_name_answers_are_the_hard_part_and_are_all_flagged(rows: list[dict[str, str]]) -> None:
    from_knowledge = [r for r in rows if r["outcome"] == "answered" and r["grounded"] == "False"]
    assert len(from_knowledge) == 108
    same = sum(ingredient_core(ingredient_set(r["model_ingredient"]))
               == ingredient_core(ingredient_set(r["openfda_ingredient"])) for r in from_knowledge)
    assert same == 104                                      # 96.3%


def test_declines_were_descriptions_with_no_drug_name_in_them(rows: list[dict[str, str]]) -> None:
    declined = [r for r in rows if r["outcome"] == "declined"]
    assert all(not r["model_ingredient"] for r in declined)
    named_in_text = 0
    for r in declined:
        words = set(clean(r["description"]).split())
        drugs = {w for name in ingredient_set(r["openfda_ingredient"]) for w in name.split() if len(w) > 3}
        named_in_text += bool(words & drugs)
    assert named_in_text <= 2                               # declining was the right answer almost every time


def test_wrong_answers_are_a_short_list_anyone_can_read(rows: list[dict[str, str]]) -> None:
    wrong = [r for r in rows if r["outcome"] == "answered" and r["same_drug"] == "False"]
    assert len(wrong) == 8
    assert {r["description"] for r in wrong} >= {"GAS RELIEF 125 MG SOFTGEL", "NP THYROID 90 MG TABLET"}
