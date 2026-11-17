"""Kills a benchmark worker with SIGKILL while it is consuming, then checks nothing is lost or counted twice.

    scripts/loadtest/stack.sh up 12 && uv run --project pipelines --with "psycopg[binary]" \\
        python scripts/loadtest/kill_test.py --mode backlog --silver data/loadtest/silver/nadac.parquet \\
        --since 2025-09-01 --expect-digest <digest of an undisturbed run> --redeliver 4000

backlog  Load every event into Kafka first, then drain it with the workers and kill one part-way. The final
         snapshots are deterministic, so they must equal an undisturbed run exactly.
live     Kill a worker while events are still being ingested. Snapshot values then depend on when each row
         arrived, so only "no event lost, none stored twice" can be checked.

SIGKILL gives the process no chance to commit offsets or finish a transaction, which is what a crashed pod
does. --redeliver K then rewinds every partition by K events and restarts the workers, forcing Kafka to
deliver events that were already stored: all of them must be skipped and nothing may change.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from benchline_pipelines.gold.auth import token_from_env
from benchline_pipelines.gold.replay import replay
from common import Db, Sampler, read_lag, wait_for
from drain import compose, reset_group


def sh(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def worker_containers(project: str) -> list[str]:
    return sh("docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}",
              "--filter", "label=com.docker.compose.service=benchmark-worker").split()


def duplicates_skipped(containers: list[str]) -> int:
    total = 0
    for c in containers:
        logs = subprocess.run(["docker", "logs", c], capture_output=True, text=True)
        total += (logs.stdout + logs.stderr).count("Skipping duplicate event")
    return total


def longest_stall(rows: list[dict[str, float]], after: float) -> float:
    """Longest stretch after `after` seconds in which no worker stored a new event."""
    best, start, last = 0.0, None, None
    for r in (r for r in rows if r["t"] >= after):
        if last is not None and r["processed"] == last:
            start = r["t"] if start is None else start
            best = max(best, r["t"] - start)
        else:
            start = None
        last = r["processed"]
    return best


def start_workers(args: argparse.Namespace) -> None:
    env = {**os.environ, "WORKER_LOG_LEVEL": "DEBUG", "KAFKA_PARTITIONS": os.environ.get("KAFKA_PARTITIONS", "3")}
    subprocess.run(["scripts/loadtest/stack.sh", "workers", str(args.replicas), str(args.threads)], check=True, env=env)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["backlog", "live"], default="backlog")
    p.add_argument("--silver", type=Path, required=True)
    p.add_argument("--since")
    p.add_argument("--weeks", type=int)
    p.add_argument("--events", type=int, help="backlog mode: events already in Kafka (default: the outbox size)")
    p.add_argument("--replicas", type=int, default=4)
    p.add_argument("--threads", type=int, default=3)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--api-url", default="http://127.0.0.1:8080")
    p.add_argument("--lag-url", default="http://127.0.0.1:9308")
    p.add_argument("--project", default="benchline-load")
    p.add_argument("--kill-at-processed", type=int, default=150000)
    p.add_argument("--down-seconds", type=float, default=20)
    p.add_argument("--redeliver", type=int, default=0, help="events per partition to rewind and redeliver")
    p.add_argument("--expect-digest", help="snapshot digest of an undisturbed run of the same data")
    p.add_argument("--label", default="kill-test")
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--out", type=Path, default=Path("docs/perf"))
    args = p.parse_args()

    db = Db()
    outcome: dict[str, Any] = {}
    if args.mode == "backlog":
        compose(args.project, "rm", "-sf", "benchmark-worker")
        db.conn.execute("TRUNCATE benchmark.processed_event, benchmark.benchmark_snapshot")
        reset_group(args.project)
        expected = args.events or db.exact_counts()["outbox"]
        start_workers(args)
    before = db.exact_counts()
    sampler = Sampler(args.lag_url).start()
    t0 = time.monotonic()

    loader = None
    if args.mode == "live":
        def load() -> None:
            try:
                outcome["result"] = replay(args.silver, args.api_url, token_from_env, args.weeks, args.since,
                                           concurrency=args.concurrency)
            except Exception as error:  # reported once the kill has been handled
                outcome["error"] = error
        loader = threading.Thread(target=load)
        loader.start()

    containers = worker_containers(args.project)
    victim = containers[0]
    wait_for(lambda: db.counts()["processed"] - before["processed"] >= args.kill_at_processed, args.timeout,
             "enough events to kill a worker mid-stream", poll=0.1)
    lag_before = read_lag(args.lag_url)["benchmark-worker"]
    processed_at_kill = db.counts()["processed"] - before["processed"]
    t_kill = time.monotonic() - t0
    sh("docker", "kill", victim)
    time.sleep(args.down_seconds)
    sh("docker", "start", victim)
    t_restart = time.monotonic() - t0

    if loader:
        loader.join()
        if "error" in outcome:
            raise outcome["error"]
        expected = outcome["result"].accepted
    target = before["processed"] + expected
    wait_for(lambda: db.counts()["outbox_unpublished"] == 0 and db.processed_at_least(target),
             args.timeout, "every event to be processed", poll=1.0)
    t_done = time.monotonic() - t0
    time.sleep(3)
    sampler.stop()

    counts = db.exact_counts()
    lost = db.scalar("""SELECT count(*) FROM pricing.outbox_event o
                          LEFT JOIN benchmark.processed_event p ON p.event_id = o.id WHERE p.event_id IS NULL""")
    digest = db.snapshot_digest()
    after_kill = [r for r in sampler.rows if r["t"] >= t_kill]
    report: dict[str, Any] = {
        "label": args.label, "mode": args.mode, "events": expected, "replicas": args.replicas,
        "killed_after_events": processed_at_kill, "kill_at_s": round(t_kill, 1), "down_s": args.down_seconds,
        "worker_lag_at_kill": lag_before["total"],
        "peak_worker_lag_after_kill": int(max((r["worker_lag"] for r in after_kill), default=0)),
        "peak_partition_lag_after_kill": int(max((r["worker_lag_max_partition"] for r in after_kill), default=0)),
        "longest_stall_s": round(longest_stall(sampler.rows, t_kill), 1),
        "seconds_from_restart_to_done": round(t_done - t_restart, 1),
        "events_published": counts["outbox"], "events_stored": counts["processed"] - before["processed"],
        "events_lost": lost, "duplicates_skipped_after_kill": duplicates_skipped(worker_containers(args.project)),
        "final_worker_lag": read_lag(args.lag_url)["benchmark-worker"]["total"], "snapshot_digest": digest,
        "digest_matches_undisturbed_run": None if not args.expect_digest else digest == args.expect_digest,
    }

    if args.redeliver:
        skipped_before = report["duplicates_skipped_after_kill"]
        compose(args.project, "stop", "benchmark-worker")
        reset_group(args.project, shift_back=args.redeliver)
        compose(args.project, "start", "benchmark-worker")
        wait_for(lambda: read_lag(args.lag_url)["benchmark-worker"]["total"] == 0, args.timeout,
                 "the redelivered events to be consumed", poll=1.0)
        time.sleep(3)
        report["redelivered"] = {
            "duplicates_skipped": duplicates_skipped(worker_containers(args.project)) - skipped_before,
            "events_stored_after": db.exact_counts()["processed"] - before["processed"],
            "snapshot_digest_unchanged": db.snapshot_digest() == digest,
        }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.label}.json").write_text(json.dumps(report, indent=2) + "\n")
    sampler.write(args.out / f"{args.label}.csv")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
