"""Row-level data quality rules for NADAC rows.

Each rule returns a boolean mask: True means the row passes. Rules run in a
fixed order and a row is charged to the first rule it fails, so the counts in
the run report add up to the number of rejected rows.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from benchline_pipelines.silver.ndc import normalize_ndc

VALID_UNITS = frozenset({"EA", "ML", "GM"})

Rule = Callable[[pd.DataFrame], pd.Series]


def _ndc_is_valid(df: pd.DataFrame) -> pd.Series:
    return df["ndc11"].notna()


def _description_present(df: pd.DataFrame) -> pd.Series:
    return df["description"].fillna("").str.strip().ne("")


def _price_is_positive(df: pd.DataFrame) -> pd.Series:
    return df["unit_price_num"].notna() & (df["unit_price_num"] > 0)


def _unit_is_known(df: pd.DataFrame) -> pd.Series:
    return df["pricing_unit"].isin(VALID_UNITS)


def _dates_parse(df: pd.DataFrame) -> pd.Series:
    return df["effective_dt"].notna() & df["as_of_dt"].notna()


def _effective_not_after_as_of(df: pd.DataFrame) -> pd.Series:
    return df["effective_dt"] <= df["as_of_dt"]


RULES: list[tuple[str, Rule]] = [
    ("ndc_not_11_digits", _ndc_is_valid),
    ("description_missing", _description_present),
    ("price_not_positive", _price_is_positive),
    ("pricing_unit_unknown", _unit_is_known),
    ("date_unparseable", _dates_parse),
    ("effective_after_as_of", _effective_not_after_as_of),
]


def add_working_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Parse raw strings into typed helper columns. Bad values become NA, not errors."""
    out = df.copy()
    out["ndc11"] = out["ndc"].map(normalize_ndc)
    out["unit_price_num"] = pd.to_numeric(out["unit_price"], errors="coerce")
    out["effective_dt"] = pd.to_datetime(out["effective_date"], format="%m/%d/%Y", errors="coerce")
    out["as_of_dt"] = pd.to_datetime(out["as_of_date"], format="%m/%d/%Y", errors="coerce")
    out["pricing_unit"] = out["pricing_unit"].str.strip().str.upper()
    return out


def apply_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Split into (accepted, rejected, rejected-per-rule). `df` needs the working columns."""
    remaining = pd.Series(True, index=df.index)
    reason = pd.Series("", index=df.index, dtype="object")
    counts: dict[str, int] = {}
    for name, rule in RULES:
        passes = rule(df)
        failed_here = remaining & ~passes
        counts[name] = int(failed_here.sum())
        reason[failed_here] = name
        remaining &= passes
    accepted = df[remaining]
    rejected = df[~remaining].assign(reject_reason=reason[~remaining])
    return accepted, rejected, counts
