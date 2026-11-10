"""Gold layer: replay silver rows into the API one publication week at a time.

Rows go in date order so each event's previous price is correct. Re-running
is safe: the API stores a row once per (NDC, source, effective date).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Hashable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

log = logging.getLogger(__name__)

BATCH_SIZE = 1000  # the API limit
RETRY_STATUS = {429, 502, 503, 504}
MAX_ATTEMPTS = 5


@dataclass
class ReplayResult:
    weeks: int = 0
    sent: int = 0
    accepted: int = 0
    duplicates: int = 0


def _batches(rows: list[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    for start in range(0, len(rows), BATCH_SIZE):
        yield rows[start : start + BATCH_SIZE]


def select_weeks(df: pd.DataFrame, weeks: int | None, since: str | None) -> pd.DataFrame:
    """Pick the latest `weeks` publication dates, or everything since a date.

    A truncated run would leave the benchmark with only the items that changed
    inside the window, so it starts from a baseline: each NDC's current rate at
    the window start, dated the day before the window opens.
    """
    dates = sorted(df["as_of_date"].unique())
    if since:
        dates = [d for d in dates if d >= since]
    if weeks:
        dates = dates[-weeks:]
    if not dates:
        return df.head(0)
    window = df[df["as_of_date"].isin(dates)]
    earlier = df[df["as_of_date"] < dates[0]]
    if earlier.empty:
        return window
    baseline_date = str((pd.Timestamp(dates[0]) - pd.Timedelta(days=1)).date())
    baseline = (
        earlier.sort_values(["effective_date", "as_of_date"])
        .drop_duplicates("ndc11", keep="last")
        .assign(as_of_date=baseline_date)
    )
    combined: pd.DataFrame = pd.concat([baseline, window], ignore_index=True)
    return combined


def _post(client: httpx.Client, url: str, batch: list[dict[str, Any]]) -> dict[str, int]:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.post(url, json={"pricePoints": batch})
        if response.status_code == 202:
            body = response.json()
            return {"accepted": int(body["accepted"]), "duplicates": int(body["duplicates"])}
        if response.status_code in RETRY_STATUS and attempt < MAX_ATTEMPTS:
            delay = 2**attempt * 0.5
            log.warning("API returned %s, retrying in %.1fs", response.status_code, delay)
            time.sleep(delay)
            continue
        # Surface the problem+json detail but never the request body.
        raise RuntimeError(f"API rejected a batch ({response.status_code}): {response.text[:300]}")
    raise RuntimeError("unreachable")


def replay(
    silver_file: Path,
    base_url: str,
    token: str,
    weeks: int | None = None,
    since: str | None = None,
    client: httpx.Client | None = None,
    group_map: Path | None = None,
) -> ReplayResult:
    df = select_weeks(pd.read_parquet(silver_file), weeks, since)
    if group_map is not None:
        names = pd.read_parquet(group_map, columns=["ndc11", "group_name"]).drop_duplicates("ndc11")
        df = df.merge(names, on="ndc11", how="left")
    result = ReplayResult()
    owns_client = client is None
    http = client or httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=60)
    url = f"{base_url.rstrip('/')}/api/v1/price-points:batch"
    try:
        for as_of, week_rows in df.groupby("as_of_date", sort=True):
            rows = week_rows.sort_values("effective_date").to_dict("records")
            payload = [_to_payload(r) for r in rows]
            for batch in _batches(payload):
                receipt = _post(http, url, batch)
                result.sent += len(batch)
                result.accepted += receipt["accepted"]
                result.duplicates += receipt["duplicates"]
            result.weeks += 1
            log.info("Replayed %s: %d rows", as_of, len(payload))
    finally:
        if owns_client:
            http.close()
    return result


def _to_payload(row: Mapping[Hashable, Any]) -> dict[str, Any]:
    group = row.get("group_name")
    extra = {"groupName": group} if isinstance(group, str) and group else {}
    return {**extra, 
        "ndc11": row["ndc11"],
        "description": row["description"],
        "otc": bool(row["otc"]),
        "source": row["source"],
        "unitPrice": row["unit_price"],
        "pricingUnit": row["pricing_unit"],
        "effectiveDate": row["effective_date"],
        "asOfDate": row["as_of_date"],
    }
