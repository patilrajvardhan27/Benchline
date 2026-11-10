# /// script
# requires-python = ">=3.12"
# dependencies = ["pandas>=2.2", "pyarrow>=17", "numpy>=2"]
# ///
"""Build the static demo snapshot straight from the cleaned NADAC data, with no running stack.

It follows the same rules as the live system: group by normalized description, benchmark each
Monday-start week from each product's latest rate within 52 weeks (linear percentiles), and score
price changes with the ML service's own scoring functions. Member data is synthetic.

This is an offline build. It does not go through the API, Kafka or the worker. For a snapshot
exported from a running stack, use export_demo_snapshot.py.

    uv run scripts/build_demo_snapshot.py --silver data/silver/nadac.parquet --out web/public/demo
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml-service"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.anomaly.scoring import MAD_CONSTANT, MIN_SCALE, is_anomaly, log_change, score_change  # noqa: E402
from synthetic_data import generate  # noqa: E402

METHOD = "percentile_cont/latest-per-item/52w"
ANOMALY_METHOD = "robust-z/log-change"
WINDOW_DAYS = 52 * 7
MIN_GROUP_HISTORY = 8
Z_THRESHOLD = 3.5


def money(value: float | Decimal) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))


def group_id(description: str) -> str:
    name = re.sub(r"\s+", " ", description.strip()).upper()
    return "grp-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def point_id(item_id: str, effective: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"price|{item_id}|{effective}"))


def write(out: Path, name: str, data: Any) -> None:
    path = out / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")


def monday(day: str) -> date:
    d = date.fromisoformat(day)
    return d - timedelta(days=d.weekday())


def weekly_snapshots(rows: pd.DataFrame, gid: str, name: str) -> list[dict[str, Any]]:
    """One snapshot per week that had a price event, as the worker would compute them."""
    snapshots = []
    for week in sorted({monday(d) for d in rows["as_of_date"]}):
        end, start = week + timedelta(days=6), week + timedelta(days=6) - timedelta(days=WINDOW_DAYS)
        valid = rows[(rows["effective_date"] <= end.isoformat()) & (rows["effective_date"] > start.isoformat())]
        if valid.empty:
            continue
        latest = valid.sort_values("effective_date").drop_duplicates("ndc11", keep="last")
        prices = latest["price"].to_numpy(dtype=float)
        p10, p25, p50, p75, p90 = np.percentile(prices, [10, 25, 50, 75, 90])
        snapshots.append({
            "groupId": gid, "groupName": name, "asOfWeek": week.isoformat(), "p10": money(p10),
            "p25": money(p25), "p50": money(p50), "p75": money(p75), "p90": money(p90),
            "nObs": len(latest), "method": METHOD,
        })
    return snapshots


def find_anomalies(sub: pd.DataFrame, listed: set[str], since: str) -> list[dict[str, Any]]:
    """Replay recent changes in order and flag the ones the ML service would flag."""
    sub = sub.sort_values(["item_id", "effective_date"]).copy()
    sub["prev"] = sub.groupby("item_id")["price"].shift(1)
    changes = sub.dropna(subset=["prev"]).copy()
    changes["x"] = np.log(changes["price"] / changes["prev"])
    changes["as_of_t"] = pd.to_datetime(changes["as_of_date"]).astype("int64") // 86_400_000_000_000
    changes["eff_t"] = pd.to_datetime(changes["effective_date"]).astype("int64") // 86_400_000_000_000
    found = []
    pooled = changes.sort_values("as_of_t").tail(20000)
    for pos, row in enumerate(changes[changes["as_of_date"] >= since].itertuples()):
        if row.item_id not in listed:
            continue
        pool = changes[changes["group_id"] == row.group_id]
        for source, floor in ((pool, MIN_GROUP_HISTORY), (pooled, 1)):
            hist = source[(source["as_of_t"] <= row.as_of_t) & (source["eff_t"] > row.as_of_t - WINDOW_DAYS)
                          & (source.index != row.Index)]["x"].to_numpy()
            if len(hist) >= floor:
                break
        if len(hist) == 0:
            continue
        med = np.median(hist)
        z = MAD_CONSTANT * (row.x - med) / max(float(np.median(np.abs(hist - med))), MIN_SCALE)
        if abs(z) < Z_THRESHOLD:
            continue
        score = score_change(log_change(row.price, row.prev), [float(v) for v in hist])
        if not is_anomaly(score, Z_THRESHOLD):
            continue
        found.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"anomaly|{row.item_id}|{row.effective_date}")),
            "pricePointId": point_id(row.item_id, row.effective_date), "groupId": row.group_id,
            "groupName": row.name, "itemId": row.item_id, "unitPrice": money(row.price),
            "previousUnitPrice": money(row.prev), "effectiveDate": row.effective_date,
            "score": round(score.z, 3), "method": ANOMALY_METHOD, "status": "OPEN",
            "detectedAt": f"{row.as_of_date}T00:00:00Z",
        })
    return sorted(found, key=lambda a: (-abs(a["score"]), a["id"]))


def build(silver: Path, out: Path, max_groups: int, per_group: int, min_ndcs: int) -> dict[str, int]:
    df = pd.read_parquet(silver).astype({"ndc11": str, "description": str, "unit_price": str})
    df["name"] = df["description"].map(lambda d: re.sub(r"\s+", " ", d.strip()).upper())
    df["group_id"] = df["name"].map(group_id)
    df["item_id"] = "ndc-" + df["ndc11"]
    df["price"] = df["unit_price"].astype(float)

    counts = df.groupby("group_id")["ndc11"].nunique()
    chosen = sorted((g for g in counts.index if counts[g] >= min_ndcs), key=lambda g: (-counts[g], g))[:max_groups]
    sub = df[df["group_id"].isin(chosen)]
    if out.exists():
        shutil.rmtree(out)

    benchmarks = {g: weekly_snapshots(sub[sub["group_id"] == g], g, str(sub[sub["group_id"] == g]["name"].iloc[0]))
                  for g in chosen}
    latest = sub.sort_values(["effective_date", "as_of_date"]).drop_duplicates("item_id", keep="last")
    listed_rows = latest.sort_values(["group_id", "ndc11"]).groupby("group_id").head(per_group)
    listed = set(listed_rows["item_id"])

    items = sorted(({"id": r.item_id, "ndc11": r.ndc11, "description": r.name, "groupId": r.group_id,
                     "groupName": r.name, "otc": bool(r.otc), "latestPrice": money(r.price),
                     "latestEffectiveDate": r.effective_date} for r in listed_rows.itertuples()),
                   key=lambda i: (i["description"], i["id"]))
    write(out, "items.json", items)
    by_group: dict[str, list[Any]] = {}
    for r in listed_rows.itertuples():
        by_group.setdefault(r.group_id, []).append(r)
    for r in listed_rows.itertuples():
        history = sub[sub["item_id"] == r.item_id].sort_values("effective_date")
        prices = [{"id": point_id(r.item_id, h.effective_date), "itemId": r.item_id, "source": "NADAC",
                   "unitPrice": money(h.price), "pricingUnit": h.pricing_unit,
                   "effectiveDate": h.effective_date, "asOfDate": h.as_of_date} for h in history.itertuples()]
        cheaper = sorted((o for o in by_group[r.group_id] if o.price < r.price), key=lambda o: (o.price, o.ndc11))[:20]
        write(out, f"items/{r.item_id}.json", {"prices": prices, "equivalents": [
            {"itemId": o.item_id, "ndc11": o.ndc11, "latestPrice": money(o.price),
             "savingsPerUnit": money(Decimal(str(r.price)) - Decimal(str(o.price)))} for o in cheaper]})
    for g, snaps in benchmarks.items():
        if snaps:
            write(out, f"benchmarks/{g}.json", {"latest": snaps[-1], "history": {"groupId": g, "snapshots": snaps}})

    newest = sub["as_of_date"].max()
    p25 = {g: Decimal(s[-1]["p25"]) for g, s in benchmarks.items() if s}
    p50 = {g: s[-1]["p50"] for g, s in benchmarks.items() if s}
    facilities, lines = generate([(r.item_id, Decimal(str(r.price))) for r in listed_rows.itertuples()],
                                 6, 120, 42, date.fromisoformat(newest))
    meta = {r.item_id: r for r in listed_rows.itertuples()}
    write(out, "members.json", [{"id": f.id, "name": f.name, "bedBand": f.bed_band, "region": f.region,
                                 "synthetic": True} for f in facilities])
    for f in facilities:
        opp = []
        for number, line in enumerate((ln for ln in lines if ln.facility_id == f.id), start=1):
            item = meta[line.item_id]
            if item.group_id in p25 and line.unit_price > p25[item.group_id]:
                opp.append({"purchaseLineId": int(f.id[-2:]) * 1000 + number, "itemId": item.item_id,
                            "groupId": item.group_id, "description": item.name, "paidUnitPrice": money(line.unit_price),
                            "benchmarkP25": money(p25[item.group_id]), "benchmarkP50": p50[item.group_id],
                            "qty": line.qty, "source": "SYNTHETIC_DEMO",
                            "savingsAmount": money((line.unit_price - p25[item.group_id]) * line.qty)})
        opp.sort(key=lambda o: (-Decimal(o["savingsAmount"]), o["purchaseLineId"]))
        write(out, f"opportunities/{f.id}.json", {
            "facility": {"id": f.id, "name": f.name, "bedBand": f.bed_band, "region": f.region, "synthetic": True},
            "totalSavings": money(sum((Decimal(o["savingsAmount"]) for o in opp), Decimal(0))), "lines": opp})

    since = str(date.fromisoformat(newest) - timedelta(weeks=26))
    anomalies = find_anomalies(sub, listed, since)[:200]
    write(out, "anomalies.json", anomalies)
    write(out, "overview.json", {"itemCount": len(items), "groupCount": len(chosen),
                                 "pricePointCount": int(sub["item_id"].isin(listed).sum()),
                                 "latestAsOfDate": newest, "openAnomalies": len(anomalies)})
    write(out, "config.json", {"anomalyAlertsEnabled": True})
    write(out, "manifest.json", {
        "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"), "groups": len(chosen), "items": len(items),
        "source": "CMS NADAC (real). Member data synthetic.",
        "build": "Offline build with pandas from cleaned NADAC data. Not produced by the Kafka path."})
    return {"groups": len(chosen), "items": len(items), "anomalies": len(anomalies)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--silver", type=Path, default=ROOT / "data/silver/nadac.parquet")
    parser.add_argument("--out", type=Path, default=ROOT / "web/public/demo")
    parser.add_argument("--max-groups", type=int, default=24)
    parser.add_argument("--per-group", type=int, default=40, help="products listed per group")
    parser.add_argument("--min-ndcs", type=int, default=8)
    args = parser.parse_args()
    result = build(args.silver, args.out, args.max_groups, args.per_group, args.min_ndcs)
    print(f"Wrote {result['items']} items in {result['groups']} groups, {result['anomalies']} anomalies, to {args.out}")


if __name__ == "__main__":
    main()
