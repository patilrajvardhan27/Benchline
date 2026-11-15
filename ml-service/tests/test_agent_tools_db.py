"""The agent's SQL against a real PostgreSQL. Set TEST_DATABASE_DSN to a migrated throwaway database."""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from app.agent.tools_db import PostgresTools

DSN = os.environ.get("TEST_DATABASE_DSN")
pytestmark = pytest.mark.skipif(DSN is None, reason="TEST_DATABASE_DSN not set")

ITEMS = [("00000000001", "0.03000"), ("00000000002", "0.02000"), ("00000000003", "0.05000")]


@pytest.fixture(scope="module")
def tools() -> Iterator[PostgresTools]:
    assert DSN is not None
    with psycopg.connect(DSN) as c:
        c.execute("""TRUNCATE insights.price_anomaly, benchmark.benchmark_snapshot, pricing.outbox_event,
                              pricing.price_point, catalog.item, catalog.item_group CASCADE""")
        c.execute("INSERT INTO catalog.item_group VALUES ('grp-sert-50', 'SERTRALINE HCL 50 MG TABLET'),"
                  " ('grp-sert-150', 'SERTRALINE HCL 150 MG TABLET')")
        for ndc, price in ITEMS:
            c.execute("INSERT INTO catalog.item (id, ndc11, description, group_id) VALUES (%s, %s, %s, 'grp-sert-50')",
                      (f"ndc-{ndc}", ndc, "SERTRALINE HCL 50 MG TABLET"))
            for date, p in (("2026-09-01", "0.04000"), ("2026-10-01", price)):
                c.execute("INSERT INTO pricing.price_point (id, item_id, source, unit_price, pricing_unit, "
                          "effective_date, as_of_date) VALUES (%s, %s, 'NADAC', %s, 'EA', %s, %s)",
                          (uuid.uuid4(), f"ndc-{ndc}", p, date, date))
        c.execute("INSERT INTO catalog.item (id, ndc11, description, group_id) VALUES "
                  "('ndc-00000000009', '00000000009', 'SERTRALINE HCL 150 MG TABLET', 'grp-sert-150')")
        c.execute("INSERT INTO benchmark.benchmark_snapshot VALUES "
                  "('grp-sert-50', '2026-09-28', 0.021, 0.025, 0.03, 0.04, 0.048, 3, 'test', now()),"
                  "('grp-sert-50', '2026-09-21', 1, 1, 1, 1, 1, 3, 'test', now())")
        c.execute("INSERT INTO insights.price_anomaly (id, price_point_id, group_id, score, method) "
                  "SELECT gen_random_uuid(), id, 'grp-sert-50', 4.2, 'robust-z' FROM pricing.price_point "
                  "WHERE item_id = 'ndc-00000000003' AND effective_date = '2026-10-01'")
        c.commit()
    pool = ConnectionPool(DSN, min_size=0, max_size=2, open=True)
    yield PostgresTools(pool)
    pool.close()


def test_benchmark_uses_the_latest_week_and_whole_number_matching(tools: PostgresTools) -> None:
    result = tools.get_benchmark("sertraline 50mg")
    assert result.data["group"] == "SERTRALINE HCL 50 MG TABLET"   # not the 150 MG group
    assert result.data["as_of_week"] == "2026-09-28"
    assert result.data["unit_price_usd"]["median"] == "0.03000"
    assert [c.item_id for c in result.citations] == ["ndc-00000000002", "ndc-00000000001"]


def test_equivalents_use_each_products_latest_price(tools: PostgresTools) -> None:
    result = tools.find_equivalents("sertraline 50")
    assert [p["latest_price"] for p in result.data["products"]] == ["0.02000", "0.03000", "0.05000"]
    assert result.data["total_products"] == 3


def test_anomalies_include_the_previous_price(tools: PostgresTools) -> None:
    rows = tools.list_anomalies("sertraline", 5).data["anomalies"]
    assert [(r["item_id"], r["previous_price"], r["new_price"], r["change_pct"]) for r in rows] == [
        ("ndc-00000000003", "0.04000", "0.05000", "+25.0")]
    assert tools.list_anomalies("metformin", 5).data["anomalies"] == []


def test_queries_run_read_only(tools: PostgresTools) -> None:
    with tools._read() as conn, pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conn.execute("DELETE FROM catalog.item")
