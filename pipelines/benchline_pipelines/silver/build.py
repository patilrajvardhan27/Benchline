"""Silver layer: typed, validated, de-duplicated NADAC rows plus a run report."""

from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from benchline_pipelines.checks.rules import add_working_columns, apply_rules
from benchline_pipelines.sources.nadac import COLUMN_MAP

log = logging.getLogger(__name__)

SILVER_COLUMNS = [
    "ndc11", "description", "otc", "source", "unit_price", "pricing_unit",
    "effective_date", "as_of_date",
]


@dataclass
class RunReport:
    """Written next to the output so every run can be audited later."""

    started_at: str
    inputs: list[str]
    rows_read: int = 0
    rows_rejected: int = 0
    rows_duplicate: int = 0
    rows_written: int = 0
    rejected_by_rule: dict[str, int] = field(default_factory=dict)
    subset_terms: list[str] = field(default_factory=list)
    rows_outside_subset: int = 0


def read_raw(path: Path) -> pd.DataFrame:
    """Read a bronze CSV as strings and map its headers to our column names."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = set(COLUMN_MAP) - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing expected columns: {sorted(missing)}")
    return df[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)


def filter_subset(df: pd.DataFrame, terms: list[str]) -> pd.DataFrame:
    """Keep rows whose description contains any term (case-insensitive)."""
    if not terms:
        return df
    pattern = "|".join(pd.Series(terms).str.replace(r"([.^$*+?{}\[\]\\|()])", r"\\\1", regex=True))
    return df[df["description"].str.contains(pattern, case=False, na=False, regex=True)]


def build_silver(
    inputs: list[Path], out_dir: Path, subset_terms: list[str] | None = None
) -> RunReport:
    terms = subset_terms or []
    report = RunReport(
        started_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        inputs=[p.name for p in inputs],
        subset_terms=terms,
    )
    frames = [read_raw(p) for p in inputs]
    raw = pd.concat(frames, ignore_index=True)
    report.rows_read = len(raw)

    in_subset = filter_subset(raw, terms)
    report.rows_outside_subset = len(raw) - len(in_subset)

    working = add_working_columns(in_subset)
    accepted, rejected, counts = apply_rules(working)
    report.rows_rejected = len(rejected)
    report.rejected_by_rule = counts

    # CMS re-publishes every rate each week with the same effective date. The first
    # publication is when the change arrived, so keep it and drop the repeats.
    accepted = accepted.sort_values("as_of_dt")
    deduped = accepted.drop_duplicates(subset=["ndc11", "effective_dt"], keep="first")
    report.rows_duplicate = len(accepted) - len(deduped)

    silver = pd.DataFrame(
        {
            "ndc11": deduped["ndc11"],
            "description": deduped["description"].str.strip(),
            "otc": deduped["otc"].str.upper().eq("Y"),
            "source": "NADAC",
            "unit_price": deduped["unit_price"].str.strip(),  # kept as text: money is never a float
            "pricing_unit": deduped["pricing_unit"],
            "effective_date": deduped["effective_dt"].dt.date.astype(str),
            "as_of_date": deduped["as_of_dt"].dt.date.astype(str),
        }
    )[SILVER_COLUMNS].sort_values(["as_of_date", "ndc11", "effective_date"])
    report.rows_written = len(silver)

    out_dir.mkdir(parents=True, exist_ok=True)
    silver.to_parquet(out_dir / "nadac.parquet", index=False)
    if len(rejected):
        rejected.drop(columns=[c for c in rejected.columns if c.endswith(("_num", "_dt"))]).to_csv(
            out_dir / "nadac_rejected.csv", index=False
        )
    (out_dir / "run_report.json").write_text(json.dumps(asdict(report), indent=2) + "\n")
    log.info("Silver: %s", report)
    return report
