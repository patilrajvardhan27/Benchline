"""Deterministic reading of a NADAC product description."""

from __future__ import annotations

import re
from dataclasses import dataclass

from benchline_pipelines.normalize.vocabulary import (
    FORMS,
    IGNORED,
    MODIFIERS,
    SALT_ABBREVIATIONS,
    SALT_WORDS,
)

STRENGTH = re.compile(
    r"(?<![\w.])(?P<num>\d[\d.,]*(?:-\d[\d.,]*)*)\s*"
    r"(?P<unit>MCG|MG|UG|GM|G|ML|MEQ|IU|UNITS?|UNT|MMOL|%)"
    r"(?:\s*/\s*(?P<per>\d*\.?\d*)\s*(?P<perunit>ML|GM|G|HR|H|DAY|L|ACTUAT|ACT)\b)?"
)
UNIT_ALIASES = {"GM": "G", "UG": "MCG", "UNITS": "UNIT", "UNT": "UNIT"}


@dataclass(frozen=True)
class RuleParse:
    candidate: str            # the drug words before the strength, with forms and modifiers removed
    strength: str             # canonical, for example "20 MG" or "250 MG/5 ML"; empty if none found
    form: str                 # canonical form, empty if none found
    modifiers: tuple[str, ...]


def _canonical_number(text: str) -> str:
    parts = []
    for piece in text.split("-"):
        piece = piece.replace(",", "").rstrip(".")
        parts.append("0" + piece if piece.startswith(".") else piece)
    return "-".join(parts)


def canonical_strength(match: re.Match[str]) -> str:
    unit = UNIT_ALIASES.get(match["unit"], match["unit"])
    number = _canonical_number(match["num"])
    if unit == "%":
        return f"{number}%"
    out = f"{number} {unit}"
    if match["perunit"]:
        per = UNIT_ALIASES.get(match["perunit"], match["perunit"])
        per = {"H": "HR", "ACT": "ACTUAT"}.get(per, per)
        count = match["per"] or ""
        out += f"/{count} {per}" if count else f"/{per}"
    return out


def expand_salts(text: str) -> str:
    return " ".join(SALT_ABBREVIATIONS.get(word, word) for word in text.split())


def base_ingredient(name: str) -> str:
    """Drop trailing salt words ("ATORVASTATIN CALCIUM TRIHYDRATE" becomes "ATORVASTATIN").

    Names that begin with a salt word, such as "POTASSIUM CHLORIDE", are left whole: the salt
    is the drug there.
    """
    words = name.split()
    while len(words) > 1 and words[-1] in SALT_WORDS and words[0] not in SALT_WORDS:
        words.pop()
    return " ".join(words)


def clean(text: str) -> str:
    text = re.sub(r"[()]", " ", text.upper())
    text = re.sub(r"[^A-Z0-9%/.,\- ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_description(description: str) -> RuleParse:
    text = clean(description)
    match = STRENGTH.search(text)
    strength = canonical_strength(match) if match else ""
    before = text[: match.start()] if match else text
    after = text[match.end():] if match else ""

    form, mods, kept = "", set(), []
    for word in before.split():
        if word in MODIFIERS:
            mods.add(MODIFIERS[word])
        elif word in FORMS:
            form = form or FORMS[word]
        elif word not in IGNORED:
            kept.append(word)
    for word in after.split():
        if word in MODIFIERS:
            mods.add(MODIFIERS[word])
        elif word in FORMS and not form:
            form = FORMS[word]
    candidate = expand_salts(" ".join(kept)).strip(" -/,")
    return RuleParse(candidate, strength, form, tuple(sorted(mods)))
