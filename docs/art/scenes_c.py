"""Warehouse card: gold tables into DuckDB or Snowflake, rebuilt in dbt."""

from __future__ import annotations

from shapes import EMBER_DARK, EMBER_PALE, INK, MUTED, TEAL_DARK, TEAL_PALE, Canvas


def warehouse() -> str:
    c = Canvas(1200, 600, "The gold tables in a warehouse, modelled with dbt",
               "load_gold.py loads items, price points and purchase lines into DuckDB or Snowflake. dbt builds "
               "staging views and two marts: the weekly benchmark and the savings opportunity. 28 checks pass and "
               "all 681 weekly snapshots match the Python build.", 20)
    c.text(60, 66, "same SQL on DuckDB (laptop) and Snowflake (cloud)", 40, INK, 700)
    w, h, gap, y = 250, 170, 40, 110
    steps = [("silver data", "nadac.parquet from the pipeline", "#ffffff", INK),
             ("load_gold.py", "raw.items, price_points, purchase_lines", TEAL_PALE, TEAL_DARK),
             ("staging", "views: typed, renamed, tested", TEAL_PALE, TEAL_DARK),
             ("marts", "weekly benchmark, savings opportunity", EMBER_PALE, EMBER_DARK)]
    for n, (title, body, fill, stroke) in enumerate(steps):
        x = 40 + n * (w + gap)
        c.box(x, y, w, h, title, body, fill, stroke, 36, 26)
        if n < 3:
            c.arrow(x + w + 3, y + h / 2, x + w + gap - 5, y + h / 2, INK)
    c.text(60, 350, "what dbt checks on every build", 36, TEAL_DARK, 700)
    checks = ["4 unit tests with hand-computed percentiles", "19 data tests: keys, links, order, one row per week",
              "exact decimal percentiles, halves round up"]
    for n, line in enumerate(checks):
        c.check(60, 378 + n * 40, 26)
        c.text(102, 400 + n * 40, line, 30, INK)
    c.rect(720, 340, 420, 200, "#ffffff", EMBER_DARK)
    c.text(740, 384, "cross-checked", 34, EMBER_DARK, 700)
    c.paragraph(740, 424, "681 of 681 weekly snapshots match the Python build behind the demo, value for value.",
                380, 29, INK)
    c.text(60, 560, "free locally with DuckDB. on a Snowflake trial: an X-Small warehouse that suspends after 60s.",
           27, MUTED)
    return c.svg()
