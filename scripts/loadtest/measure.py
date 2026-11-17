"""Replays silver data through the running stack and reports events per second at each stage.

    uv run --project pipelines --with "psycopg[binary]" python scripts/loadtest/measure.py \\
        --silver data/loadtest/silver/nadac.parquet --since 2025-06-01 --label 12p-4w

Stages: ingest (API accepts the rows), publish (outbox rows reach Kafka), consume (every event is
stored as a benchmark). With --then, a command runs once publishing is done, which is how consumer
throughput is measured with the workers held back until the backlog is complete.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from benchline_pipelines.gold.auth import token_from_env
from benchline_pipelines.gold.replay import replay
from common import Db, Sampler, read_lag, wait_for


def rate(count: int, seconds: float) -> float:
    return round(count / seconds, 1) if seconds > 0 else 0.0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--silver", type=Path, required=True)
    p.add_argument("--weeks", type=int)
    p.add_argument("--since")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--api-url", default="http://127.0.0.1:8080")
    p.add_argument("--lag-url", default="http://127.0.0.1:9308")
    p.add_argument("--label", default="run")
    p.add_argument("--load-only", action="store_true", help="stop once every event is in Kafka (see drain.py)")
    p.add_argument("--then", help="shell command to run once the outbox has drained (e.g. start the workers)")
    p.add_argument("--timeout", type=float, default=7200)
    p.add_argument("--out", type=Path, default=Path("docs/perf"))
    args = p.parse_args()

    db = Db()
    before = db.exact_counts()
    sampler = Sampler(args.lag_url).start()
    t0 = time.monotonic()

    result = replay(args.silver, args.api_url, token_from_env, args.weeks, args.since, concurrency=args.concurrency)
    t_ingest = time.monotonic() - t0
    published = result.accepted
    wait_for(lambda: db.counts()["outbox_unpublished"] == 0, args.timeout, "the outbox to drain")
    t_publish = time.monotonic() - t0

    if args.load_only:
        sampler.stop()
        report = {"label": args.label, "events": published, "rows_sent": result.sent,
                  "ingest_s": round(t_ingest, 1), "ingest_eps": rate(published, t_ingest),
                  "publish_done_s": round(t_publish, 1), "publish_lag_after_ingest_s": round(t_publish - t_ingest, 1),
                  "publish_eps": rate(published, t_publish)}
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / f"{args.label}.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return

    t_consume_start = t_publish
    if args.then:
        subprocess.run(args.then, shell=True, check=True)
        t_consume_start = time.monotonic() - t0
    target = before["processed"] + published
    wait_for(lambda: db.processed_at_least(target), args.timeout, "every event to be processed", poll=1.0)
    t_done = time.monotonic() - t0
    time.sleep(2)
    sampler.stop()

    report = {
        "label": args.label, "events": published, "rows_sent": result.sent, "duplicates_rejected": result.duplicates,
        "ingest_s": round(t_ingest, 1), "ingest_eps": rate(published, t_ingest),
        "publish_done_s": round(t_publish, 1), "publish_eps": rate(published, t_publish),
        "consume_s": round(t_done - t_consume_start, 1), "consume_eps": rate(published, t_done - t_consume_start),
        "end_to_end_s": round(t_done, 1), "end_to_end_eps": rate(published, t_done),
        "peak_worker_lag": int(max((r["worker_lag"] for r in sampler.rows), default=0)),
        "final_lag": read_lag(args.lag_url),
        "snapshots": db.scalar("SELECT count(*) FROM benchmark.benchmark_snapshot"),
        "snapshot_digest": db.snapshot_digest(),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.label}.json").write_text(json.dumps(report, indent=2) + "\n")
    sampler.write(args.out / f"{args.label}.csv")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
