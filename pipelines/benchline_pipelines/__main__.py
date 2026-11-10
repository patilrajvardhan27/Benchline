"""Command line entry point: python -m benchline_pipelines <fetch|silver|replay>."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from benchline_pipelines.bronze.fetch import fetch_nadac
from benchline_pipelines.gold.auth import token_from_env
from benchline_pipelines.gold.replay import replay
from benchline_pipelines.normalize.cli import add_normalize_commands, run_normalize_command
from benchline_pipelines.silver.build import build_silver

DEFAULT_DATA = Path("data")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="benchline_pipelines")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="download raw NADAC files (bronze)")
    fetch.add_argument("--years", type=int, nargs="+", default=[2025, 2026])

    silver = sub.add_parser("silver", help="clean and validate (silver)")
    silver.add_argument(
        "--bronze-run", type=Path, help="bronze/nadac/<date> folder; default latest"
    )
    silver.add_argument(
        "--contains", nargs="*", default=[],
        help="keep only descriptions containing any of these words (keeps laptops happy)",
    )

    gold = sub.add_parser("replay", help="post silver rows to the API week by week")
    gold.add_argument("--weeks", type=int, help="only the latest N publication weeks")
    gold.add_argument("--since", help="only publication dates on or after YYYY-MM-DD")
    gold.add_argument("--group-map", type=Path, help="item_groups.parquet from the normalize command")
    gold.add_argument("--api-url", default=os.environ.get("BENCHLINE_API_URL", "http://localhost:8080"))
    add_normalize_commands(sub)
    return parser


def _latest_bronze_run(data_dir: Path) -> Path:
    runs = sorted((data_dir / "bronze" / "nadac").glob("*"))
    if not runs:
        raise SystemExit("No bronze data found. Run the fetch command first.")
    return runs[-1]


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parser().parse_args(argv)
    data: Path = args.data_dir

    if args.command == "fetch":
        fetch_nadac(args.years, data / "bronze")
    elif args.command == "silver":
        run = args.bronze_run or _latest_bronze_run(data)
        report = build_silver(sorted(run.glob("nadac_*.csv")), data / "silver", args.contains)
        print(f"read={report.rows_read} rejected={report.rows_rejected} "
              f"duplicates={report.rows_duplicate} written={report.rows_written}")
    elif args.command in ("normalize", "normalize-eval", "normalize-probe"):
        run_normalize_command(args, data)
    elif args.command == "replay":
        result = replay(data / "silver" / "nadac.parquet", args.api_url, token_from_env(),
                        args.weeks, args.since, group_map=args.group_map)
        print(f"weeks={result.weeks} sent={result.sent} accepted={result.accepted} "
              f"duplicates={result.duplicates}")


if __name__ == "__main__":
    main()
