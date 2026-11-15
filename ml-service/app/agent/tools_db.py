"""The agent's tools over PostgreSQL. Every query runs in a read-only transaction with a short timeout."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.agent.results import (
    Benchmark,
    Flag,
    Product,
    anomalies_result,
    benchmark_result,
    equivalents_result,
    no_match,
    word_pattern,
)
from app.agent.tools import MAX_ROWS, ToolResult, query_words

MATCH_GROUPS = """
SELECT g.id, g.name, count(i.id) AS n_items
  FROM catalog.item_group g JOIN catalog.item i ON i.group_id = g.id
 WHERE upper(g.name) ~ ALL(%(patterns)s)
 GROUP BY g.id, g.name
 ORDER BY n_items DESC, g.name
 LIMIT 4"""

LATEST_BENCHMARK = """
SELECT group_id, as_of_week::text, p10, p25, p50, p75, p90, n_obs
  FROM benchmark.v_latest_snapshot WHERE group_id = %(group)s"""

GROUP_PRODUCTS = """
SELECT i.id, i.ndc11, i.description, lp.unit_price, lp.effective_date::text,
       count(*) OVER () AS total
  FROM catalog.item i
  JOIN LATERAL (SELECT p.unit_price, p.effective_date FROM pricing.price_point p
                 WHERE p.item_id = i.id AND p.source = 'NADAC'
                 ORDER BY p.effective_date DESC LIMIT 1) lp ON true
 WHERE i.group_id = %(group)s
 ORDER BY lp.unit_price, i.id
 LIMIT %(limit)s"""

ANOMALIES = """
SELECT i.id, i.description, g.name, pp.unit_price, pp.effective_date::text, a.score::float, a.status,
       (SELECT p2.unit_price FROM pricing.price_point p2
         WHERE p2.item_id = pp.item_id AND p2.source = pp.source AND p2.effective_date < pp.effective_date
         ORDER BY p2.effective_date DESC LIMIT 1) AS previous
  FROM insights.price_anomaly a
  JOIN pricing.price_point pp ON pp.id = a.price_point_id
  JOIN catalog.item i ON i.id = pp.item_id
  JOIN catalog.item_group g ON g.id = a.group_id
 WHERE a.status <> 'DISMISSED' AND (%(any)s OR upper(g.name) ~ ALL(%(patterns)s))
 ORDER BY pp.effective_date DESC, a.score DESC
 LIMIT %(limit)s"""


class PostgresTools:
    def __init__(self, pool: ConnectionPool[Connection[Any]]) -> None:
        self._pool = pool

    @contextmanager
    def _read(self) -> Iterator[Connection[Any]]:
        with self._pool.connection() as conn:
            conn.read_only = True
            with conn.transaction():
                conn.execute("SET LOCAL statement_timeout = '3s'")
                yield conn

    def _groups(self, conn: Connection[Any], drug: str) -> list[dict[str, Any]]:
        patterns = [word_pattern(w) for w in query_words(drug)]
        return conn.cursor(row_factory=dict_row).execute(MATCH_GROUPS, {"patterns": patterns}).fetchall()

    def _products(self, conn: Connection[Any], group_id: str, limit: int) -> tuple[list[Product], int]:
        rows = conn.execute(GROUP_PRODUCTS, {"group": group_id, "limit": limit}).fetchall()
        products = [Product(r[0], r[1], r[2], r[3], r[4]) for r in rows]
        return products, (rows[0][5] if rows else 0)

    def get_benchmark(self, drug: str) -> ToolResult:
        with self._read() as conn:
            for group in self._groups(conn, drug):
                row = conn.execute(LATEST_BENCHMARK, {"group": group["id"]}).fetchone()
                if row is None:
                    continue
                cheapest, _ = self._products(conn, group["id"], 2)
                others = [g["name"] for g in self._groups(conn, drug) if g["id"] != group["id"]]
                return benchmark_result(Benchmark(row[0], group["name"], *row[1:]), cheapest, others)
        return no_match(drug)

    def find_equivalents(self, drug: str) -> ToolResult:
        with self._read() as conn:
            groups = self._groups(conn, drug)
            if not groups:
                return no_match(drug)
            products, total = self._products(conn, groups[0]["id"], MAX_ROWS)
            return equivalents_result(groups[0]["name"], groups[0]["id"], products, total)

    def list_anomalies(self, drug: str | None, limit: int) -> ToolResult:
        patterns = [word_pattern(w) for w in query_words(drug)] if drug else []
        with self._read() as conn:
            rows = conn.execute(ANOMALIES, {"any": not patterns, "patterns": patterns,
                                            "limit": limit}).fetchall()
        flags = [Flag(r[0], r[1], r[2], r[7], r[3], r[4], r[5], r[6]) for r in rows]
        return anomalies_result(flags, drug)
