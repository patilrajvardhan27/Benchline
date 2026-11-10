"""Bronze layer: save the raw files exactly as published, never modified."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import httpx

from benchline_pipelines.sources import nadac

log = logging.getLogger(__name__)
CHUNK = 1024 * 1024


def fetch_nadac(years: list[int], bronze_dir: Path, today: dt.date | None = None) -> list[Path]:
    """Download each year's file into bronze/nadac/<download date>/. Returns the paths."""
    stamp = (today or dt.date.today()).isoformat()
    target_dir = bronze_dir / "nadac" / stamp
    target_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    with httpx.Client(follow_redirects=True) as client:
        for year in years:
            target = target_dir / f"nadac_{year}.csv"
            if target.exists():
                log.info("Already downloaded: %s", target)
                saved.append(target)
                continue
            url = nadac.download_url(client, year)
            log.info("Downloading %s", url)
            partial = target.with_suffix(".part")
            with client.stream("GET", url, timeout=300) as response:
                response.raise_for_status()
                with partial.open("wb") as out:
                    for chunk in response.iter_bytes(CHUNK):
                        out.write(chunk)
            partial.rename(target)  # a half-written file never looks complete
            saved.append(target)
    return saved
