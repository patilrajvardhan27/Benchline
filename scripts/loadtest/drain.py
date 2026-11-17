"""Drains a Kafka backlog that is already loaded, with a chosen number of worker replicas.

    scripts/loadtest/drain.py --replicas 4 --threads 3 --events 475000 --label p12-w4

Starts from the first event every time: benchmarks are cleared and the consumer group is reset. The rate is
measured from the first event processed, so JVM start-up and group joining are reported separately.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from common import Db, Sampler, read_lag, wait_for

TOPIC = "pricing.price-point-recorded.v1"


def compose(project: str, *args: str) -> None:
    subprocess.run(["docker", "compose", "-p", project, *args], check=True, capture_output=True)


def reset_group(project: str, shift_back: int | None = None) -> None:
    """Back to the first event, or `shift_back` events per partition earlier than the committed offset."""
    where = ["--shift-by", f"-{shift_back}"] if shift_back else ["--to-earliest"]
    cmd = ["docker", "exec", f"{project}-kafka-1", "/opt/kafka/bin/kafka-consumer-groups.sh",
           "--bootstrap-server", "localhost:9092", "--group", "benchmark-worker", "--topic", TOPIC,
           "--reset-offsets", *where, "--execute"]
    for _ in range(30):  # the group must be empty; it is a few seconds after the workers leave
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError("could not reset the consumer group offsets")


def peak_rate(rows: list[dict[str, float]], window: int = 5) -> float:
    best = 0.0
    for a, b in zip(rows, rows[window:], strict=False):
        if b["t"] > a["t"]:
            best = max(best, (b["processed"] - a["processed"]) / (b["t"] - a["t"]))
    return round(best, 1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--replicas", type=int, required=True)
    p.add_argument("--threads", type=int, default=3, help="consumer threads per replica")
    p.add_argument("--events", type=int, required=True, help="events in the backlog")
    p.add_argument("--label", required=True)
    p.add_argument("--project", default="benchline-load")
    p.add_argument("--lag-url", default="http://127.0.0.1:9308")
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--out", type=Path, default=Path("docs/perf"))
    args = p.parse_args()

    db = Db()
    compose(args.project, "rm", "-sf", "benchmark-worker")
    db.conn.execute("TRUNCATE benchmark.processed_event, benchmark.benchmark_snapshot")
    reset_group(args.project)

    sampler = Sampler(args.lag_url).start()
    t0 = time.monotonic()
    env = {**os.environ, "KAFKA_PARTITIONS": os.environ.get("KAFKA_PARTITIONS", "3")}
    subprocess.run(["scripts/loadtest/stack.sh", "workers", str(args.replicas), str(args.threads)], check=True, env=env)
    wait_for(db.any_processed, args.timeout, "the first event to be processed", poll=0.1)
    t_first = time.monotonic() - t0
    wait_for(lambda: db.processed_at_least(args.events), args.timeout, "the backlog to drain", poll=0.5)
    t_done = time.monotonic() - t0
    time.sleep(2)
    sampler.stop()

    drain = t_done - t_first
    report = {
        "label": args.label, "events": args.events, "replicas": args.replicas, "threads_per_replica": args.threads,
        "partitions": int(os.environ.get("KAFKA_PARTITIONS", "3")),
        "startup_s": round(t_first, 1), "drain_s": round(drain, 1), "consume_eps": round(args.events / drain, 1),
        "peak_5s_eps": peak_rate(sampler.rows), "final_lag": read_lag(args.lag_url)["benchmark-worker"]["total"],
        "snapshots": db.scalar("SELECT count(*) FROM benchmark.benchmark_snapshot"),
        "snapshot_digest": db.snapshot_digest(),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.label}.json").write_text(json.dumps(report, indent=2) + "\n")
    sampler.write(args.out / f"{args.label}.csv")
    print(f"{args.label}: {report['consume_eps']:,.0f} events/s (peak {report['peak_5s_eps']:,.0f}), "
          f"start-up {report['startup_s']}s, digest {report['snapshot_digest'][:8]}")


if __name__ == "__main__":
    main()
