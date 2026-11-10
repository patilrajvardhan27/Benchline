import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_demo_snapshot import build, group_id, money  # noqa: E402
from synthetic_data import generate  # noqa: E402


def silver(tmp_path: Path) -> Path:
    rows = [
        {"ndc11": f"0000000000{n}", "description": "TEST  drug 10 MG tab", "otc": False, "source": "NADAC",
         "unit_price": f"0.{n}0000", "pricing_unit": "EA", "effective_date": "2026-10-01",
         "as_of_date": "2026-10-07"}
        for n in range(1, 9)
    ]
    path = tmp_path / "nadac.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def read(out: Path, name: str):
    return json.loads((out / name).read_text())


def test_group_id_matches_the_java_rule() -> None:
    assert group_id("  atorvastatin   calcium 20 mg tab ") == "grp-atorvastatin-calcium-20-mg-tab"
    assert group_id("12HR NASAL (OTC)") == "grp-12hr-nasal-otc"


def test_money_rounds_half_up_to_five_places() -> None:
    assert money(0.030215) == "0.03022"
    assert money(Decimal("1.5")) == "1.50000"


def test_benchmark_matches_hand_computed_percentiles(tmp_path: Path) -> None:
    out = tmp_path / "demo"
    build(silver(tmp_path), out, max_groups=1, per_group=40, min_ndcs=8)
    latest = read(out, "benchmarks/grp-test-drug-10-mg-tab.json")["latest"]
    # eight products priced 0.1 to 0.8, linear interpolation
    assert (latest["p10"], latest["p25"], latest["p50"], latest["p75"], latest["p90"]) == (
        "0.17000", "0.27500", "0.45000", "0.62500", "0.73000")
    assert latest["nObs"] == 8
    assert latest["asOfWeek"] == "2026-10-05"  # the Monday of 2026-10-07


def test_listed_items_equivalents_and_overview(tmp_path: Path) -> None:
    out = tmp_path / "demo"
    build(silver(tmp_path), out, max_groups=1, per_group=40, min_ndcs=8)
    assert len(read(out, "items.json")) == 8
    top = read(out, "items/ndc-00000000008.json")
    assert len(top["equivalents"]) == 7 and top["equivalents"][0]["latestPrice"] == "0.10000"
    assert read(out, "overview.json")["itemCount"] == 8


def test_member_data_is_always_labelled_synthetic(tmp_path: Path) -> None:
    out = tmp_path / "demo"
    build(silver(tmp_path), out, max_groups=1, per_group=40, min_ndcs=8)
    members = read(out, "members.json")
    assert members and all(m["synthetic"] is True for m in members)
    lines = [ln for m in members for ln in read(out, f"opportunities/{m['id']}.json")["lines"]]
    assert lines and {ln["source"] for ln in lines} == {"SYNTHETIC_DEMO"}


def test_build_is_deterministic_and_says_it_is_offline(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    path = silver(tmp_path)
    build(path, first, 1, 40, 8)
    build(path, second, 1, 40, 8)
    for file in first.rglob("*.json"):
        if file.name != "manifest.json":
            assert file.read_text() == (second / file.relative_to(first)).read_text()
    assert "Not produced by the Kafka path" in read(first, "manifest.json")["build"]


def test_synthetic_generation_is_reproducible_for_a_seed() -> None:
    items = [(f"ndc-{n:011d}", Decimal("0.10")) for n in range(30)]
    a = generate(items, 3, 10, 42, date(2026, 10, 28))
    assert a == generate(items, 3, 10, 42, date(2026, 10, 28))
    assert a != generate(items, 3, 10, 7, date(2026, 10, 28))
    assert all(line.unit_price > 0 and line.qty >= 100 for line in a[1])
