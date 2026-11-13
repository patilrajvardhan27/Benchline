"""Load Benchline's gold tables into DuckDB (local, free) or Snowflake.

    uv run python load_gold.py                      # DuckDB file benchline.duckdb
    uv run python load_gold.py --target snowflake   # needs the SNOWFLAKE_* variables, see README
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_demo_snapshot import group_id, money
from synthetic_data import generate

SCHEMA = "raw"


def gold_tables(silver: Path, group_map: Path | None) -> dict[str, pd.DataFrame]:
    prices = pd.read_parquet(silver).astype({"ndc11": str, "description": str, "unit_price": str})
    prices["item_id"] = "ndc-" + prices["ndc11"]
    prices["group_name"] = prices["description"].str.strip().str.replace(r"\s+", " ", regex=True).str.upper()
    if group_map is not None:  # normalized groups from `benchline_pipelines normalize`
        names = pd.read_parquet(group_map, columns=["ndc11", "group_name"])
        prices = prices.drop(columns="group_name").merge(names, on="ndc11", how="left")
    prices["group_id"] = prices["group_name"].map(group_id)

    latest = prices.sort_values(["effective_date", "as_of_date"]).drop_duplicates("item_id", keep="last")
    items = latest[["item_id", "ndc11", "description", "group_id", "group_name"]]

    priced = [(r.item_id, Decimal(r.unit_price)) for r in latest.itertuples()]
    _, lines = generate(priced, facilities=6, lines_each=120, seed=42, today=date.fromisoformat(latest["as_of_date"].max()))
    purchases = pd.DataFrame([{
        "purchase_line_id": n, "facility_id": ln.facility_id, "item_id": ln.item_id,
        "unit_price": money(ln.unit_price), "qty": ln.qty, "purchased_on": ln.purchased_on,
    } for n, ln in enumerate(lines, 1)])

    points = prices[["item_id", "source", "unit_price", "pricing_unit", "effective_date", "as_of_date"]].copy()
    for col in ("effective_date", "as_of_date"):
        points[col] = pd.to_datetime(points[col]).dt.date
    return {"items": items, "price_points": points, "purchase_lines": purchases}


def load_duckdb(tables: dict[str, pd.DataFrame], path: str) -> None:
    import duckdb

    with duckdb.connect(path) as con:
        con.execute(f"create schema if not exists {SCHEMA}")
        for name, frame in tables.items():
            con.register("frame", frame)
            con.execute(f"create or replace table {SCHEMA}.{name} as select * from frame")
            con.unregister("frame")


def load_snowflake(tables: dict[str, pd.DataFrame]) -> None:
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas

    env = os.environ
    with snowflake.connector.connect(
        account=env["SNOWFLAKE_ACCOUNT"], user=env["SNOWFLAKE_USER"], password=env["SNOWFLAKE_PASSWORD"],
        role=env.get("SNOWFLAKE_ROLE"), warehouse=env["SNOWFLAKE_WAREHOUSE"], database=env["SNOWFLAKE_DATABASE"],
    ) as con:
        con.cursor().execute(f"create schema if not exists {SCHEMA}")
        for name, frame in tables.items():
            write_pandas(con, frame, name.upper(), schema=SCHEMA.upper(), auto_create_table=True, overwrite=True,
                         quote_identifiers=False, use_logical_type=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=["duckdb", "snowflake"], default="duckdb")
    parser.add_argument("--silver", type=Path, default=ROOT / "data/silver/nadac.parquet")
    parser.add_argument("--group-map", type=Path, help="item_groups.parquet; groups by description when omitted")
    parser.add_argument("--duckdb-path", default=os.environ.get("DUCKDB_PATH", "benchline.duckdb"))
    args = parser.parse_args()

    tables = gold_tables(args.silver, args.group_map)
    if args.target == "duckdb":
        load_duckdb(tables, args.duckdb_path)
    else:
        load_snowflake(tables)
    print(", ".join(f"{name} {len(frame):,}" for name, frame in tables.items()), f"-> {args.target}")


if __name__ == "__main__":
    main()
