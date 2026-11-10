"""Checks on what the model says, before any of it is used."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

from benchline_pipelines.normalize.rules import (
    STRENGTH,
    base_ingredient,
    canonical_strength,
    clean,
    expand_salts,
)
from benchline_pipelines.normalize.vocabulary import FORMS


class LlmParse(BaseModel):
    ingredient: str
    is_brand: bool
    strength: str | None = None
    form: str | None = None


def interpret(description: str, parsed: LlmParse) -> tuple[str, str, str, bool, str] | None:
    """Validate the model's answer against the description. None means unusable."""
    words = clean(description).split()
    name = base_ingredient(expand_salts(clean(parsed.ingredient)))
    if not name or name == "UNKNOWN" or len(name) > 80:
        return None
    grounded = any(part in words for part in re.split(r"[ /-]+", name) if len(part) > 3)

    strength = ""
    if parsed.strength:
        found = STRENGTH.search(clean(parsed.strength))
        wanted = re.findall(r"\d*\.?\d+", found["num"].replace(",", "")) if found else []
        have = re.findall(r"\d*\.?\d+", clean(description).replace(",", ""))
        if found and wanted and all(n in have for n in wanted):
            strength = canonical_strength(found)
    form = FORMS.get(clean(parsed.form or ""), "")
    problems = []
    if not grounded:
        problems.append("ingredient came from model knowledge, not from the description")
    if parsed.strength and not strength:
        problems.append("model gave a strength the description does not contain")
    return name, strength, form, grounded, "; ".join(problems)


def parse_json(content: str) -> Any:
    """Models sometimes wrap JSON in a code fence."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)
