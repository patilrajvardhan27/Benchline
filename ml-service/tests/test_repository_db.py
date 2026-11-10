"""Runs against a real PostgreSQL. Set TEST_DATABASE_DSN to a migrated throwaway database."""

import os
import uuid

import psycopg
import pytest

from app.anomaly.repository import PostgresAnomalyRepository

DSN = os.environ.get("TEST_DATABASE_DSN")
pytestmark = pytest.mark.skipif(DSN is None, reason="TEST_DATABASE_DSN not set")


@pytest.fixture
def conn():  # type: ignore[no-untyped-def]
    assert DSN is not None
    with psycopg.connect(DSN) as c:
        c.execute(
            """TRUNCATE insights.price_anomaly, pricing.outbox_event, pricing.price_point,
                        catalog.item, catalog.item_group CASCADE"""
        )
        c.execute("INSERT INTO catalog.item_group (id, name) VALUES ('grp-a', 'A')")
        c.execute(
            "INSERT INTO catalog.item (id, ndc11, description, group_id) "
            "VALUES ('ndc-00000000001', '00000000001', 'A', 'grp-a')"
        )
        c.commit()
        yield c


def add_price(conn, price: str, days_ago: int) -> uuid.UUID:  # type: ignore[no-untyped-def]
    row = conn.execute(
        """INSERT INTO pricing.price_point
               (item_id, source, unit_price, pricing_unit, effective_date, as_of_date)
           VALUES ('ndc-00000000001', 'NADAC', %s, 'EA',
                   current_date - %s, current_date - %s) RETURNING id""",
        (price, days_ago, days_ago),
    ).fetchone()
    conn.commit()
    assert row is not None
    result: uuid.UUID = row[0]
    return result


def test_group_changes_are_log_ratios_and_exclude_the_current_point(conn) -> None:  # type: ignore[no-untyped-def]
    add_price(conn, "1.00", 30)
    add_price(conn, "2.00", 20)
    current = add_price(conn, "1.00", 10)

    repo = PostgresAnomalyRepository(conn)
    assert repo.group_changes("grp-a", current, 365) == pytest.approx([0.6931471805599453])
    assert sorted(repo.pooled_changes(current, 365)) == pytest.approx([0.6931471805599453])


def test_insert_anomaly_is_idempotent(conn) -> None:  # type: ignore[no-untyped-def]
    point = add_price(conn, "1.00", 5)
    repo = PostgresAnomalyRepository(conn)
    assert repo.insert_anomaly(point, "grp-a", 4.2, "robust-z/log-change") is True
    assert repo.insert_anomaly(point, "grp-a", 4.2, "robust-z/log-change") is False
    count = conn.execute("SELECT count(*) FROM insights.price_anomaly").fetchone()[0]
    assert count == 1
