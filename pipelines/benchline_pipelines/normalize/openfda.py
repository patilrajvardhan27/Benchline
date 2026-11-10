"""openFDA NDC directory: an authoritative, free lookup from NDC to ingredient and form (CC0)."""

from __future__ import annotations

import json
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from benchline_pipelines.normalize.rules import base_ingredient, clean, expand_salts
from benchline_pipelines.normalize.vocabulary import FDA_FORM_BASE, FDA_MODIFIERS
from benchline_pipelines.silver.ndc import normalize_ndc

log = logging.getLogger(__name__)
URL = "https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip"
# Marketing categories whose ingredient names make a trustworthy vocabulary.
VOCAB_CATEGORIES = {"ANDA", "NDA", "NDA AUTHORIZED GENERIC", "BLA", "OTC MONOGRAPH DRUG", "UNAPPROVED DRUG OTHER"}


@dataclass(frozen=True)
class FdaProduct:
    brand: str
    ingredients: tuple[str, ...]      # base ingredient names, salts stripped
    form: str
    modifiers: tuple[str, ...]
    marketing: str
    strengths: tuple[str, ...] = ()

    @property
    def is_brand(self) -> bool:
        return self.marketing in {"NDA", "BLA"}

    @property
    def ingredient(self) -> str:
        return " / ".join(sorted(set(self.ingredients)))


@dataclass(frozen=True)
class FdaIndex:
    by_ndc: dict[str, FdaProduct]
    vocabulary: frozenset[str]        # base ingredient names openFDA knows


def fda_form(dosage_form: str) -> tuple[str, tuple[str, ...]]:
    """"TABLET, FILM COATED, EXTENDED RELEASE" becomes ("TABLET", ("ER",))."""
    pieces = [p.strip() for p in dosage_form.upper().split(",") if p.strip()]
    if not pieces:
        return "", ()
    form = FDA_FORM_BASE.get(pieces[0].split()[0], "")
    mods = {FDA_MODIFIERS[p] for p in pieces[1:] if p in FDA_MODIFIERS}
    return form, tuple(sorted(mods))


def _base(name: str) -> str:
    return base_ingredient(expand_salts(clean(name)))


def ensure_download(directory: Path, refresh: bool = False) -> Path:
    """Fetch the bulk file once. It is public data (CC0) and about 28 MB."""
    target = directory / "drug-ndc.json.zip"
    if target.exists() and not refresh:
        return target
    directory.mkdir(parents=True, exist_ok=True)
    log.info("Downloading %s", URL)
    with httpx.stream("GET", URL, timeout=300, follow_redirects=True) as response:
        response.raise_for_status()
        with target.open("wb") as out:
            for chunk in response.iter_bytes(1 << 20):
                out.write(chunk)
    return target


def load_index(zip_path: Path) -> FdaIndex:
    with zipfile.ZipFile(zip_path) as archive:
        results = json.loads(archive.read(archive.namelist()[0]))["results"]
    by_ndc: dict[str, FdaProduct] = {}
    vocabulary: set[str] = set()
    for item in results:
        names = tuple(_base(i["name"]) for i in item.get("active_ingredients", []) if i.get("name"))
        if not names:
            continue
        form, mods = fda_form(item.get("dosage_form", ""))
        strengths = tuple(
            re.sub(r"\s*/\s*1$", "", i["strength"].upper()).replace(" /", "/").strip()
            for i in item.get("active_ingredients", []) if i.get("strength"))
        product = FdaProduct(item.get("brand_name", ""), names, form, mods, item.get("marketing_category", ""),
                             strengths)
        if product.marketing in VOCAB_CATEGORIES and len(names) <= 3:
            vocabulary.update(names)
        for package in item.get("packaging", []):
            ndc = normalize_ndc(package.get("package_ndc"))
            if ndc:
                by_ndc[ndc] = product
    return FdaIndex(by_ndc, frozenset(vocabulary))
