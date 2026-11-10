"""Normalize every NDC and write the group map the API and the demo builder can use."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from benchline_pipelines.normalize.evaluate import ingredient_set
from benchline_pipelines.normalize.llm import LlmNormalizer
from benchline_pipelines.normalize.openfda import FdaIndex
from benchline_pipelines.normalize.rules import clean, parse_description


@dataclass(frozen=True)
class Normalized:
    ndc11: str
    description: str
    ingredient: str
    strength: str
    form: str
    modifiers: tuple[str, ...]
    is_brand: bool
    method: str            # openfda, rules, llm or unresolved
    reason: str            # why a person should check it; empty when nothing to check

    @property
    def group_name(self) -> str:
        """Same product, same name. Without an ingredient we keep the old behaviour: the cleaned description."""
        if not self.ingredient:
            return clean(self.description)
        parts = [self.ingredient, *self.modifiers, self.strength, self.form]
        return " ".join(p for p in parts if p) + (" (BRAND)" if self.is_brand else "")

    @property
    def needs_review(self) -> bool:
        return bool(self.reason)


def normalize_item(ndc: str, description: str, index: FdaIndex, llm: LlmNormalizer | None) -> Normalized:
    rule = parse_description(description)
    product = index.by_ndc.get(ndc)
    names = ingredient_set(rule.candidate)

    if product:
        reason = ""
        if rule.form and product.form and rule.form != product.form:
            reason = f"description says {rule.form}, openFDA says {product.form}"
        strength = rule.strength or " / ".join(product.strengths)
        if not strength:
            reason = reason or "no strength in the description or in openFDA"
        return Normalized(ndc, description, product.ingredient, strength, rule.form or product.form,
                          tuple(sorted(set(rule.modifiers) | set(product.modifiers))), product.is_brand,
                          "openfda", reason)
    if names and all(n in index.vocabulary for n in names):
        return Normalized(ndc, description, " / ".join(sorted(names)), rule.strength, rule.form,
                          rule.modifiers, False, "rules", "" if rule.strength else "no strength in the description")
    if llm is not None:
        result = llm.normalize(description)
        if result is not None:
            return Normalized(ndc, description, result.ingredient, rule.strength or result.strength,
                              rule.form or result.form, rule.modifiers, result.is_brand, "llm", result.reason)
        return Normalized(ndc, description, "", "", "", (), False, "unresolved", "the model could not identify it")
    return Normalized(ndc, description, "", "", "", (), False, "unresolved",
                      "no openFDA record, rules did not recognise it, and no model is configured")


@dataclass
class NormalizeReport:
    ndcs: int = 0
    by_method: dict[str, int] = field(default_factory=dict)
    needs_review: int = 0
    groups_before: int = 0     # distinct cleaned descriptions: what grouping used until now
    groups_after: int = 0
    llm: dict[str, float] = field(default_factory=dict)
    biggest_merges: list[dict[str, object]] = field(default_factory=list)


def run(silver: Path, index: FdaIndex, out_dir: Path, llm: LlmNormalizer | None = None,
        max_llm: int | None = None) -> NormalizeReport:
    frame = pd.read_parquet(silver, columns=["ndc11", "description"]).drop_duplicates("ndc11", keep="last")
    results: list[Normalized] = []
    llm_used = 0
    for ndc, description in zip(frame["ndc11"], frame["description"], strict=True):
        guard = llm
        if llm is not None and max_llm is not None and llm_used >= max_llm:
            guard = None
        before = llm.stats.handled if llm else 0
        item = normalize_item(ndc, description, index, guard)
        if llm is not None and llm.stats.handled > before:
            llm_used += 1
        results.append(item)

    table = pd.DataFrame([{
        "ndc11": r.ndc11, "description": r.description, "group_name": r.group_name,
        "ingredient": r.ingredient, "strength": r.strength, "form": r.form,
        "modifiers": " ".join(r.modifiers), "is_brand": r.is_brand, "method": r.method,
        "needs_review": r.needs_review, "reason": r.reason} for r in results])
    out_dir.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out_dir / "item_groups.parquet", index=False)
    table[table["needs_review"]].to_csv(out_dir / "needs_review.csv", index=False)

    sources: dict[str, set[str]] = defaultdict(set)
    for r in results:
        sources[r.group_name].add(clean(r.description))
    report = NormalizeReport(
        ndcs=len(results), by_method={str(k): int(v) for k, v in table["method"].value_counts().items()},
        needs_review=int(table["needs_review"].sum()),
        groups_before=len({clean(r.description) for r in results}), groups_after=len(sources),
        llm=asdict(llm.stats) if llm else {},
        biggest_merges=[{"group": g, "descriptions": len(d), "examples": sorted(d)[:4]}
                        for g, d in sorted(sources.items(), key=lambda kv: -len(kv[1]))[:8] if len(d) > 1])
    (out_dir / "normalize_report.json").write_text(json.dumps(asdict(report), indent=2, default=str) + "\n")
    return report
