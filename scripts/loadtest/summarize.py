"""Prints consume rates for every run in docs/perf, from the recorded timelines, with one definition:
events divided by the time from the first processed event to the last (worker start-up excluded).

    python3 scripts/loadtest/summarize.py [docs/perf]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def drain_seconds(rows: list[dict[str, str]], events: int) -> tuple[float, float] | None:
    first = next((float(r["t"]) for r in rows if float(r["processed"]) > 0), None)
    last = next((float(r["t"]) for r in rows if float(r["processed"]) >= events), None)
    return (first, last) if first is not None and last is not None and last > first else None


def main() -> None:
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/perf")
    print("| run | events | first event at | drained at | events/s |\n|---|---|---|---|---|")
    for report in sorted(folder.glob("*.json")):
        data = json.loads(report.read_text())
        timeline = report.with_suffix(".csv")
        if "events" not in data or not timeline.exists() or "consume_eps" not in data:
            continue
        with timeline.open() as f:
            span = drain_seconds(list(csv.DictReader(f)), data["events"])
        if span:
            first, last = span
            rate = data["events"] / (last - first)
            print(f"| {data['label']} | {data['events']:,} | {first:.0f}s | {last:.0f}s | {rate:,.0f} |")


if __name__ == "__main__":
    main()
