# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Write synthetic demo facilities and purchase lines to PostgreSQL.

Every row is tagged SYNTHETIC_DEMO and the database refuses anything else.
The seed is fixed, so the same command always produces the same data.

    uv run scripts/seed_synthetic.py --facilities 6 --seed 42
"""

from __future__ import annotations

import argparse
import os
from datetime import date
from decimal import Decimal

import psycopg

from synthetic_data import generate


def pick_items(conn: psycopg.Connection, limit: int) -> list[tuple[str, Decimal]]:
    """Items that have a benchmark and a current NADAC price, in a stable order."""
    rows = conn.execute(
        """
        SELECT i.id, lp.unit_price
          FROM catalog.item i
          JOIN benchmark.v_latest_snapshot s ON s.group_id = i.group_id
          JOIN LATERAL (SELECT unit_price FROM pricing.price_point
                         WHERE item_id = i.id AND source = 'NADAC'
                         ORDER BY effective_date DESC LIMIT 1) lp ON true
         ORDER BY i.id LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def seed(conn: psycopg.Connection, facilities: int, seed_value: int, lines_each: int) -> int:
    items = pick_items(conn, 4000)
    if not items:
        raise SystemExit("No priced items with a benchmark yet. Replay some prices first.")
    made_facilities, lines = generate(items, facilities, lines_each, seed_value, date.today())

    conn.execute("TRUNCATE member.purchase_line, member.facility RESTART IDENTITY CASCADE")
    for f in made_facilities:
        conn.execute(
            "INSERT INTO member.facility (id, name, bed_band, region) VALUES (%s, %s, %s, %s)",
            (f.id, f.name, f.bed_band, f.region),
        )
    for line in lines:
        conn.execute(
            """INSERT INTO member.purchase_line (facility_id, item_id, unit_price, qty, purchased_on)
               VALUES (%s, %s, %s, %s, %s)""",
            (line.facility_id, line.item_id, line.unit_price, line.qty, line.purchased_on),
        )
    conn.commit()
    return len(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--facilities", type=int, default=6)
    parser.add_argument("--lines", type=int, default=120, help="purchase lines per facility")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dsn", default=os.environ.get("DATABASE_URL", "postgresql://benchline@localhost:5432/benchline"))
    args = parser.parse_args()
    with psycopg.connect(args.dsn) as conn:
        total = seed(conn, args.facilities, args.seed, args.lines)
    print(f"Created {args.facilities} synthetic facilities with {total} purchase lines (seed {args.seed}).")


if __name__ == "__main__":
    main()
