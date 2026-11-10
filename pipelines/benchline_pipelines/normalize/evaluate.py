"""How good is each layer? Scores the rules against openFDA's answers for the same NDCs."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from benchline_pipelines.normalize.openfda import FdaIndex, FdaProduct
from benchline_pipelines.normalize.rules import base_ingredient, parse_description
from benchline_pipelines.normalize.vocabulary import SALT_WORDS

if TYPE_CHECKING:
    from benchline_pipelines.normalize.llm import LlmNormalizer

NUMBER = re.compile(r"\d*\.?\d+")


def ingredient_set(text: str) -> frozenset[str]:
    """"AMLODIPINE-BENAZEPRIL" and "A / B" become sets of base ingredient names."""
    parts = [p.strip() for p in re.split(r"[/,]| - |-", text) if p.strip()]
    return frozenset(base_ingredient(p) for p in parts) if parts else frozenset()


def ingredient_core(names: frozenset[str] | set[str]) -> frozenset[str]:
    """The drug word of each ingredient, skipping salt words: "SODIUM FLUORIDE" gives FLUORIDE.

    A lenient comparison: it accepts a model that names the drug without an ester or salt that openFDA appends
    ("FLUOCINOLONE" for "FLUOCINOLONE ACETONIDE"), and one that lists a mixture's parts once, not per salt.
    """
    core = set()
    for name in names:
        words = name.split()
        core.add(next((w for w in words if w not in SALT_WORDS), words[0] if words else ""))
    return frozenset(core)


def numbers(text: str) -> list[float]:
    return [float(n) for n in NUMBER.findall(text.replace(",", ""))]


def strength_matches(mine: str, fda_strengths: str) -> bool | None:
    """True or False when comparable, None for percent strengths (openFDA uses mg/g there)."""
    if not mine or mine.endswith("%"):
        return None
    mine_numbers = numbers(mine.split(" ")[0])
    theirs = numbers(fda_strengths)
    return bool(mine_numbers) and all(n in theirs for n in mine_numbers)


@dataclass
class RulesScore:
    ndcs: int = 0
    resolved: int = 0                 # rules recognised the drug name in openFDA's vocabulary
    ingredient_correct: int = 0
    brand_ndcs: int = 0
    brand_abstained: int = 0          # brands the rules correctly did not claim to know
    form_compared: int = 0
    form_correct: int = 0
    strength_compared: int = 0
    strength_correct: int = 0
    wrong_examples: list[tuple[str, str, str]] = field(default_factory=list)


def score_rules(rows: pd.DataFrame, index: FdaIndex, keep_examples: int = 15) -> RulesScore:
    """`rows` has ndc11 and description. Only NDCs openFDA knows can be scored."""
    score = RulesScore()
    for ndc, description in zip(rows["ndc11"], rows["description"], strict=True):
        product: FdaProduct | None = index.by_ndc.get(ndc)
        if product is None:
            continue
        score.ndcs += 1
        parsed = parse_description(description)
        names = ingredient_set(parsed.candidate)
        known = bool(names) and all(n in index.vocabulary for n in names)
        if product.is_brand:
            score.brand_ndcs += 1
            score.brand_abstained += 0 if known else 1
        if known:
            score.resolved += 1
            if names == set(product.ingredients):
                score.ingredient_correct += 1
            elif len(score.wrong_examples) < keep_examples:
                score.wrong_examples.append((description, parsed.candidate, product.ingredient))
        if parsed.form and product.form:
            score.form_compared += 1
            score.form_correct += parsed.form == product.form
    return score


@dataclass
class LlmScore:
    sampled: int = 0
    answered: int = 0
    ingredient_correct: int = 0          # exact match with openFDA's ingredient
    lenient_correct: int = 0             # same drug, ignoring salt and ester names
    grounded: int = 0
    knowledge_answered: int = 0          # answers whose ingredient is not in the description: brand names
    knowledge_lenient_correct: int = 0
    flagged_for_review: int = 0
    wrong_examples: list[tuple[str, str, str]] = field(default_factory=list)
    records: list[dict[str, object]] = field(default_factory=list)   # one row per case, for export and audit


def hard_cases(rows: pd.DataFrame, index: FdaIndex, size: int, seed: int = 7) -> pd.DataFrame:
    """NDCs openFDA knows, where the rules do not recognise the name. Mostly brands: the model's real job."""
    keep = []
    for ndc, description in zip(rows["ndc11"], rows["description"], strict=True):
        if ndc in index.by_ndc:
            names = ingredient_set(parse_description(description).candidate)
            if not (names and all(n in index.vocabulary for n in names)):
                keep.append((ndc, description))
    frame = pd.DataFrame(keep, columns=["ndc11", "description"])
    return frame.sample(min(size, len(frame)), random_state=seed) if len(frame) else frame


def cached_cases(rows: pd.DataFrame, index: FdaIndex, llm: LlmNormalizer) -> pd.DataFrame:
    """Every description the model has already been asked about, once each, that openFDA can check.

    Offline scoring uses this instead of drawing a sample, so it measures exactly the answers on file even if
    the rules (and so the set of hard cases) have changed since they were collected.
    """
    known = rows[rows["ndc11"].isin(index.by_ndc.keys())]
    asked = known[[llm.is_cached(d) for d in known["description"]]]
    return asked.drop_duplicates("description")


def score_llm(rows: pd.DataFrame, index: FdaIndex, llm: LlmNormalizer,
              progress: Callable[[int, int], None] | None = None) -> LlmScore:
    """Ask the model about hard cases and compare with openFDA's ingredient."""
    score = LlmScore(sampled=len(rows))
    for position, (ndc, description) in enumerate(zip(rows["ndc11"], rows["description"], strict=True), 1):
        if progress is not None:
            progress(position, len(rows))
        result = llm.normalize(description)
        truth = index.by_ndc[ndc]
        if result is None:
            score.records.append({"ndc11": ndc, "description": description, "openfda_ingredient": truth.ingredient,
                                  "outcome": "declined"})
            continue
        score.answered += 1
        score.grounded += result.grounded
        score.flagged_for_review += result.needs_review
        predicted = ingredient_set(result.ingredient)
        lenient = ingredient_core(predicted) == ingredient_core(set(truth.ingredients))
        score.ingredient_correct += predicted == set(truth.ingredients)
        score.lenient_correct += lenient
        if not result.grounded:
            score.knowledge_answered += 1
            score.knowledge_lenient_correct += lenient
        if not lenient and len(score.wrong_examples) < 15:
            score.wrong_examples.append((description, result.ingredient, truth.ingredient))
        score.records.append({
            "ndc11": ndc, "description": description, "openfda_ingredient": truth.ingredient, "outcome": "answered",
            "model_ingredient": result.ingredient, "is_brand": result.is_brand, "grounded": result.grounded,
            "strength": result.strength, "form": result.form, "exact": predicted == set(truth.ingredients),
            "same_drug": lenient})
    return score
