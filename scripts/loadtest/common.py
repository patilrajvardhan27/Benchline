"""Shared by the load tests: database and lag readings, and a sampler that records a timeline."""

from __future__ import annotations

import csv
import json
import os
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

import psycopg

WORKER_GROUP = "benchmark-worker"
ML_GROUP = "ml-anomaly"
UNPUBLISHED = "SELECT count(*) FROM pricing.outbox_event WHERE published_at IS NULL"
COLUMNS = ["t", "outbox_unpublished", "processed", "worker_lag", "worker_lag_max_partition", "ml_lag"]


def dsn() -> str:
    explicit = os.environ.get("LOADTEST_DSN")
    if explicit:
        return explicit
    password = os.environ["POSTGRES_PASSWORD"]
    return f"postgresql://benchline:{password}@127.0.0.1:{os.environ.get('POSTGRES_PORT', '5432')}/benchline"


class Db:
    def __init__(self) -> None:
        self.conn = psycopg.connect(dsn(), autocommit=True)

    def scalar(self, sql: str) -> Any:
        row = self.conn.execute(sql).fetchone()
        return row[0] if row else None

    def counts(self) -> dict[str, int]:
        """Cheap, for polling: table sizes come from the statistics view, which lags by a moment.

        Counting millions of rows every second would itself slow the system being measured.
        """
        approx = dict(self.conn.execute(
            "SELECT relname, n_live_tup FROM pg_stat_user_tables WHERE relname IN ('outbox_event', 'processed_event')"
        ).fetchall())
        return {"outbox": approx.get("outbox_event", 0), "processed": approx.get("processed_event", 0),
                "outbox_unpublished": self.scalar(UNPUBLISHED)}

    def exact_counts(self) -> dict[str, int]:
        return {
            "outbox": self.scalar("SELECT count(*) FROM pricing.outbox_event"),
            "outbox_unpublished": self.scalar(UNPUBLISHED),
            "processed": self.scalar("SELECT count(*) FROM benchmark.processed_event"),
        }

    def processed_at_least(self, target: int) -> bool:
        """Polls the cheap count, and only counts exactly once it says the target may be reached."""
        return self.counts()["processed"] >= target * 0.995 and self.exact_counts()["processed"] >= target

    def any_processed(self) -> bool:
        return bool(self.scalar("SELECT EXISTS (SELECT 1 FROM benchmark.processed_event)"))

    def snapshot_digest(self) -> str:
        return self.scalar("""
            SELECT coalesce(md5(string_agg(concat_ws('|', group_id, as_of_week, p10, p25, p50, p75, p90, n_obs),
                                           ',' ORDER BY group_id, as_of_week)), '')
              FROM benchmark.benchmark_snapshot""")


def read_lag(url: str) -> dict[str, dict[str, int]]:
    """Per group: total lag and the worst single partition, from the Go lag monitor."""
    with urllib.request.urlopen(f"{url.rstrip('/')}/lag", timeout=5) as response:
        body = json.load(response)
    return {g["group"]: {"total": g["total"], "max_partition": max((p["lag"] for p in g["partitions"]), default=0)}
            for g in body["groups"]}


class Sampler:
    """Records one row a second in the background until stopped."""

    def __init__(self, lag_url: str) -> None:
        self.rows: list[dict[str, float]] = []
        self._lag_url = lag_url
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._t0 = time.monotonic()

    def start(self) -> Sampler:
        self._t0 = time.monotonic()
        self._thread.start()
        return self

    def _run(self) -> None:
        db = Db()
        while not self._stop.wait(1.0):
            try:
                counts, lag = db.counts(), read_lag(self._lag_url)
            except Exception:  # a reading can fail while a service restarts; the next one will do
                continue
            worker = lag.get(WORKER_GROUP, {"total": 0, "max_partition": 0})
            self.rows.append({
                "t": round(time.monotonic() - self._t0, 1), "outbox_unpublished": counts["outbox_unpublished"],
                "processed": counts["processed"], "worker_lag": worker["total"],
                "worker_lag_max_partition": worker["max_partition"], "ml_lag": lag.get(ML_GROUP, {"total": 0})["total"],
            })

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def write(self, path: Path) -> None:
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(self.rows)


def wait_for(condition, timeout: float, what: str, poll: float = 0.5) -> float:  # type: ignore[no-untyped-def]
    """Seconds waited until condition() is true; raises on timeout."""
    start = time.monotonic()
    while not condition():
        if time.monotonic() - start > timeout:
            raise TimeoutError(f"timed out after {timeout:.0f}s waiting for {what}")
        time.sleep(poll)
    return time.monotonic() - start
