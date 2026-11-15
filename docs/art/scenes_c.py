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


def platform() -> str:
    c = Canvas(1200, 640, "Benchline on Kubernetes, with MinIO and a Go lag monitor",
               "A kind cluster runs the chart: a migration job, five services with startup, readiness and liveness "
               "probes, and a helm test. Raw CMS files go to MinIO through the S3 API. A Go service reports how far "
               "each Kafka consumer is behind.", 21)
    c.text(60, 62, "the same chart on a laptop (kind) and in CI, on every push", 38, INK, 700)
    c.rect(40, 90, 760, 400, TEAL_PALE, TEAL_DARK)
    c.text(64, 132, "kind cluster  ·  helm install", 32, TEAL_DARK, 700)
    c.box(64, 156, 220, 110, "migrate job", "waits for postgres, then Flyway", "#ffffff", INK, 30, 22)
    pods = ["pricing-api", "benchmark-worker", "ml-service", "web", "lag-monitor"]
    for n, name in enumerate(pods):
        x, y = 310 + (n % 2) * 240, 156 + (n // 2) * 70
        c.rect(x, y, 220, 54, EMBER_PALE if name == "lag-monitor" else "#ffffff",
               EMBER_DARK if name == "lag-monitor" else TEAL_DARK)
        c.text(x + 110, y + 36, name, 27, INK, 700, "middle")
    c.arrow(286, 210, 304, 210, INK)
    c.text(64, 400, "every pod: startup, ready and live probes", 28, INK, 500)
    c.text(64, 440, "then helm test calls each one and reads the lag", 28, INK, 500)
    c.rect(840, 90, 320, 180, "#ffffff", INK)
    c.text(1000, 134, "MinIO (S3 API)", 32, INK, 700, "middle")
    c.paragraph(860, 174, "raw CMS files, untouched, each with its SHA-256", 280, 26, MUTED, 500)
    c.rect(840, 300, 320, 190, EMBER_PALE, EMBER_DARK)
    c.text(1000, 344, "lag-monitor (Go)", 32, EMBER_DARK, 700, "middle")
    c.paragraph(860, 384, "events each consumer has not read yet, per partition. /metrics", 280, 26, INK, 500)
    c.text(60, 560, "benchline_consumer_lag_total{group=\"benchmark-worker\"} 0", 30, TEAL_DARK, 700)
    c.text(60, 604, "zero means caught up. a number that keeps rising means a stuck worker.", 27, MUTED)
    return c.svg()
