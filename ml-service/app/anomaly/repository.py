"""All SQL for anomaly scoring. The service owns the insights schema."""

from __future__ import annotations

import uuid
from typing import Protocol, cast

import psycopg

CHANGES_SQL = """
SELECT change FROM (
    SELECT pp.id,
           ln(pp.unit_price / lag(pp.unit_price) OVER w)::float8 AS change
      FROM pricing.price_point pp
      JOIN catalog.item i ON i.id = pp.item_id
     WHERE {scope} AND pp.source = 'NADAC' AND pp.effective_date > current_date - %(days)s
    WINDOW w AS (PARTITION BY pp.item_id ORDER BY pp.effective_date)
) changes
 WHERE change IS NOT NULL AND id <> %(exclude)s
"""

GROUP_SCOPE = "i.group_id = %(group)s"
POOLED_SCOPE = "true"
POOLED_LIMIT = 20000


class AnomalyRepository(Protocol):
    def group_changes(self, group_id: str, exclude: uuid.UUID, days: int) -> list[float]: ...

    def pooled_changes(self, exclude: uuid.UUID, days: int) -> list[float]: ...

    def insert_anomaly(
        self, price_point_id: uuid.UUID, group_id: str, score: float, method: str
    ) -> bool: ...


class PostgresAnomalyRepository:
    def __init__(self, conn: psycopg.Connection[tuple[object, ...]]) -> None:
        self._conn = conn

    def group_changes(self, group_id: str, exclude: uuid.UUID, days: int) -> list[float]:
        sql = CHANGES_SQL.format(scope=GROUP_SCOPE)
        return self._floats(sql, {"group": group_id, "exclude": exclude, "days": days})

    def pooled_changes(self, exclude: uuid.UUID, days: int) -> list[float]:
        sql = CHANGES_SQL.format(scope=POOLED_SCOPE) + f" LIMIT {POOLED_LIMIT}"
        return self._floats(sql, {"exclude": exclude, "days": days})

    def insert_anomaly(
        self, price_point_id: uuid.UUID, group_id: str, score: float, method: str
    ) -> bool:
        """Returns False if this price point was already flagged by this method."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO insights.price_anomaly (id, price_point_id, group_id, score, method)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (price_point_id, method) DO NOTHING
                """,
                (uuid.uuid4(), price_point_id, group_id, round(score, 3), method),
            )
            inserted = cur.rowcount == 1
        self._conn.commit()
        return inserted

    def _floats(self, sql: str, params: dict[str, object]) -> list[float]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        self._conn.rollback()  # read only; releases the snapshot
        return [float(cast(float, row[0])) for row in rows]
