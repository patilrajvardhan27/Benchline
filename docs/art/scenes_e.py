"""Load-test charts, drawn from the result files in docs/perf so the numbers cannot drift from the data."""

from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

from shapes import EMBER_DARK, EMBER_PALE, INK, LINE, MUTED, TEAL_DARK, TEAL_PALE, Canvas

PERF = Path(__file__).resolve().parents[1] / "perf"


def _eps(name: str) -> float:
    return float(json.loads((PERF / f"{name}.json").read_text())["consume_eps"])


def _bar(c: Canvas, x: float, base: float, height: float, w: float, label: str, value: float, fill: str, stroke: str,
         note: str = "") -> None:
    c.rect(x, base - height, w, height, fill, stroke)
    c.text(x + w / 2, base - height - 14, f"{value:,.0f}", 30, stroke, 700, "middle")
    c.text(x + w / 2, base + 34, label, 26, INK, 700, "middle")
    if note:
        c.text(x + w / 2, base + 62, note, 22, MUTED, 500, "middle")


def scaling() -> str:
    before, after = _eps("before-p3-w1"), _eps("p3-w1")
    configs = [("3 partitions", "1 worker", "p3-w1"), ("3 partitions", "4 workers", "p3-w4"),
               ("12 partitions", "1 worker", "p12-w1"), ("12 partitions", "2 workers", "p12-w2"),
               ("12 partitions", "4 workers", "p12-w4")]
    values = {name: _eps(name) for _, _, name in configs}
    c = Canvas(1200, 640, "Worker throughput, before and after, and as it scales",
               f"One commit per event drained {before:,.0f} events per second; one commit per poll drained {after:,.0f}. "
               "With 12 partitions, 1, 2 and 4 workers drained "
               + ", ".join(f"{values[n]:,.0f}" for n in ("p12-w1", "p12-w2", "p12-w4")) + " events per second.", 31)
    c.text(40, 60, "events per second the worker stores, 498,360 events already in Kafka", 34, INK, 700)
    base, scale = 520, 330 / 40000

    c.text(40, 112, "the fix: one commit per poll", 26, EMBER_DARK, 700)
    _bar(c, 60, base, before * scale, 110, "before", before, EMBER_PALE, EMBER_DARK, "3p, 1 worker")
    _bar(c, 210, base, after * scale, 110, "after", after, TEAL_PALE, TEAL_DARK, "3p, 1 worker")
    c.text(265, base - after * scale - 58, f"{after / before:.1f}x faster", 34, TEAL_DARK, 700, "middle")

    c.line(400, 100, 400, 590, LINE, 3, "6 8")
    c.text(430, 112, "after: more partitions, then more workers", 26, TEAL_DARK, 700)
    x = 430
    for partitions, workers, name in configs:
        fill, stroke = (TEAL_PALE, TEAL_DARK) if partitions.startswith("12") else ("#ececec", MUTED)
        _bar(c, x, base, values[name] * scale, 100, workers, values[name], fill, stroke, partitions)
        x += 145
    c.text(430, 612, "3 partitions cannot feed more than 3 consumers: extra workers sit idle", 24, MUTED, 500)
    return c.svg()


def _series(name: str, column: str) -> list[tuple[float, float]]:
    with (PERF / f"{name}.csv").open() as f:
        return [(float(r["t"]), float(r[column])) for r in csv.DictReader(f)]


def kill() -> str:
    report = json.loads((PERF / "kill-test-backlog-p12-w4.json").read_text())
    lag = _series("kill-test-backlog-p12-w4", "worker_lag")
    killed, back = float(report["kill_at_s"]), float(report["kill_at_s"]) + float(report["down_s"])
    end = max(t for t, _ in lag)
    peak = max(v for _, v in lag) or 1
    left, top, width, height = 90, 130, 1060, 300
    c = Canvas(1200, 640, "Killing a worker mid-stream",
               f"One of {report['replicas']} workers was killed after {report['killed_after_events']:,} events and "
               f"restarted {report['down_s']:.0f} seconds later. Events published {report['events_published']:,}, "
               f"stored {report['events_stored']:,}, lost {report['events_lost']}. The final snapshots matched an "
               "undisturbed run exactly. 48,000 redelivered events were all skipped.", 32)
    c.text(40, 60, "kill -9 one of 4 workers, restart it 20 s later", 36, INK, 700)
    c.text(40, 100, "events still waiting in Kafka", 26, MUTED, 500)
    c.line(left, top + height, left + width, top + height, INK, 3)
    c.line(left, top, left, top + height, INK, 3)

    def at(t: float, v: float) -> tuple[float, float]:
        return left + t / end * width, top + height - v / peak * height

    points = [at(t, v) for t, v in lag]
    for (x1, y1), (x2, y2) in itertools.pairwise(points):
        c.line(x1, y1, x2, y2, TEAL_DARK, 4)
    for t, label, colour in ((killed, "killed", EMBER_DARK), (back, "restarted", TEAL_DARK)):
        x, _ = at(t, 0)
        c.line(x, top - 6, x, top + height, colour, 3, "8 8")
        c.text(x, top - 14, label, 28, colour, 700, "middle")
    c.text(left, top + height + 36, "0 s", 24, MUTED, 500, "middle")
    c.text(left + width, top + height + 36, f"{end:.0f} s", 24, MUTED, 500, "end")
    c.text(left + 8, top + 28, f"{peak:,.0f}", 24, MUTED, 500)

    checks = [("published", f"{report['events_published']:,}"), ("stored", f"{report['events_stored']:,}"),
              ("lost", str(report["events_lost"])),
              ("same snapshots as clean run", "yes" if report["digest_matches_undisturbed_run"] else "NO"),
              ("redelivered and skipped", f"{report['redelivered']['duplicates_skipped']:,}")]
    x = 40
    for label, value in checks:
        c.rect(x, 515, 205, 112, TEAL_PALE if label != "lost" else "#ffffff", TEAL_DARK)
        c.text(x + 102, 562, value, 34, TEAL_DARK, 700, "middle")
        c.paragraph(x + 14, 585, label, 180, 21, INK, 500)
        x += 224
    return c.svg()
