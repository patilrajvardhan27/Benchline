import json
from pathlib import Path

import pandas as pd

from benchline_pipelines.silver.build import build_silver, filter_subset, read_raw

FIXTURE = Path(__file__).parent / "fixtures" / "nadac_sample.csv"


def test_reads_real_header_layout() -> None:
    df = read_raw(FIXTURE)
    assert list(df.columns) == [
        "description", "ndc", "unit_price", "effective_date", "pricing_unit", "otc", "as_of_date",
    ]
    assert len(df) == 12


def test_each_rule_rejects_its_row(tmp_path: Path) -> None:
    report = build_silver([FIXTURE], tmp_path)

    assert report.rows_read == 12
    assert report.rejected_by_rule == {
        "ndc_not_11_digits": 1,        # "123"
        "description_missing": 1,      # blank description
        "price_not_positive": 2,       # 0 and "abc"
        "pricing_unit_unknown": 1,     # BOX
        "date_unparseable": 1,         # not-a-date
        "effective_after_as_of": 1,    # effective 11/10 after as-of 10/28
    }
    assert report.rows_rejected == 7


def test_counts_add_up(tmp_path: Path) -> None:
    report = build_silver([FIXTURE], tmp_path)
    assert report.rows_read == report.rows_rejected + report.rows_duplicate + report.rows_written
    assert sum(report.rejected_by_rule.values()) == report.rows_rejected


def test_duplicate_rate_keeps_first_publication(tmp_path: Path) -> None:
    build_silver([FIXTURE], tmp_path)
    silver = pd.read_parquet(tmp_path / "nadac.parquet")
    dup = silver[(silver["ndc11"] == "00000000002") & (silver["effective_date"] == "2026-10-22")]
    assert len(dup) == 1
    assert dup.iloc[0]["as_of_date"] == "2026-10-28"


def test_output_is_typed_and_money_stays_text(tmp_path: Path) -> None:
    build_silver([FIXTURE], tmp_path)
    silver = pd.read_parquet(tmp_path / "nadac.parquet")
    assert pd.api.types.is_string_dtype(silver["unit_price"])
    assert set(silver["source"]) == {"NADAC"}
    assert silver["otc"].dtype == bool
    assert silver["ndc11"].str.len().eq(11).all()
    assert silver["as_of_date"].is_monotonic_increasing


def test_run_report_and_rejects_are_written(tmp_path: Path) -> None:
    build_silver([FIXTURE], tmp_path)
    report = json.loads((tmp_path / "run_report.json").read_text())
    assert report["rows_rejected"] == 7
    rejected = pd.read_csv(tmp_path / "nadac_rejected.csv", dtype=str)
    assert len(rejected) == 7
    assert "reject_reason" in rejected.columns


def test_second_run_produces_identical_output(tmp_path: Path) -> None:
    build_silver([FIXTURE], tmp_path)
    first = pd.read_parquet(tmp_path / "nadac.parquet")
    build_silver([FIXTURE], tmp_path)
    pd.testing.assert_frame_equal(first, pd.read_parquet(tmp_path / "nadac.parquet"))


def test_subset_filter_is_case_insensitive_and_literal() -> None:
    df = read_raw(FIXTURE)
    assert len(filter_subset(df, ["drug b"])) == 1
    assert len(filter_subset(df, ["(.*)"])) == 0  # regex characters are not interpreted
    assert len(filter_subset(df, [])) == len(df)
