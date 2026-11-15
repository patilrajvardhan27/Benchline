"""Bronze layer: save the raw files exactly as published, never modified."""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import tempfile
from pathlib import Path

import httpx

from benchline_pipelines.bronze.store import PREFIX, BronzeStore
from benchline_pipelines.sources import nadac

log = logging.getLogger(__name__)
CHUNK = 1024 * 1024


def fetch_nadac(years: list[int], store: BronzeStore, today: dt.date | None = None) -> list[str]:
    """Download each year's file to nadac/<download date>/ in the store. Returns the keys."""
    stamp = (today or dt.date.today()).isoformat()
    saved: list[str] = []
    with httpx.Client(follow_redirects=True) as client, tempfile.TemporaryDirectory() as tmp:
        for year in years:
            key = f"{PREFIX}/{stamp}/nadac_{year}.csv"
            if store.has(key):
                log.info("Already stored: %s", key)
                saved.append(key)
                continue
            url = nadac.download_url(client, year)
            log.info("Downloading %s", url)
            partial = Path(tmp) / f"nadac_{year}.csv"
            digest = hashlib.sha256()
            with client.stream("GET", url, timeout=300) as response:
                response.raise_for_status()
                with partial.open("wb") as out:
                    for chunk in response.iter_bytes(CHUNK):
                        out.write(chunk)
                        digest.update(chunk)
            # Stored only once complete, so a half-written file never looks like a finished one.
            store.put(key, partial, {"source-url": url, "sha256": digest.hexdigest()})
            saved.append(key)
    return saved
