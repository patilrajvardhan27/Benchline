# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "pyjwt>=2.9"]
# ///
"""Export a static snapshot of a running Benchline API for the free static demo.

The snapshot holds real NADAC prices and benchmarks plus the synthetic facilities
(still labelled synthetic). It is read-only JSON, so the site needs no backend.

    DEV_JWT_SECRET=... uv run scripts/export_demo_snapshot.py --out web/public/demo
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import jwt

MIN_NDCS_PER_GROUP = 6


def token() -> str:
    secret = os.environ.get("DEV_JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise SystemExit("Set DEV_JWT_SECRET (32+ characters) to read protected endpoints")
    now = int(time.time())
    claims = {"sub": "snapshot-export", "scope": "members:read insights:read", "iat": now, "exp": now + 900}
    return jwt.encode(claims, secret, algorithm="HS256")


def write(out: Path, name: str, data: Any) -> None:
    path = out / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")


def get_all(client: httpx.Client, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 0
    while True:
        r = client.get(path, params={**(params or {}), "page": page, "size": 100})
        r.raise_for_status()
        body = r.json()
        rows.extend(body["content"] if "content" in body else body["lines"])
        if page + 1 >= body["page"]["totalPages"]:
            return rows
        page += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8080")
    parser.add_argument("--out", type=Path, default=Path("web/public/demo"))
    parser.add_argument("--max-groups", type=int, default=30)
    args = parser.parse_args()

    if args.out.exists():
        shutil.rmtree(args.out)
    with httpx.Client(base_url=args.api, headers={"Authorization": f"Bearer {token()}"}, timeout=60) as client:
        everything = get_all(client, "/api/v1/items")
        by_group: dict[str, list[dict[str, Any]]] = {}
        for item in everything:
            by_group.setdefault(item["groupId"], []).append(item)
        ranked = sorted(by_group, key=lambda g: (-len(by_group[g]), g))
        chosen = [g for g in ranked if len(by_group[g]) >= MIN_NDCS_PER_GROUP][: args.max_groups]
        items = sorted((i for g in chosen for i in by_group[g]), key=lambda i: (i["description"], i["id"]))

        write(args.out, "items.json", items)
        for item in items:
            prices = client.get(f"/api/v1/items/{item['id']}/prices", params={"source": "NADAC"}).json()
            equivalents = client.get(f"/api/v1/items/{item['id']}/equivalents").json()
            write(args.out, f"items/{item['id']}.json", {"prices": prices, "equivalents": equivalents})
        for group in chosen:
            latest = client.get(f"/api/v1/benchmarks/groups/{group}")
            if latest.status_code != 200:
                continue
            history = client.get(f"/api/v1/benchmarks/groups/{group}/history").json()
            write(args.out, f"benchmarks/{group}.json", {"latest": latest.json(), "history": history})

        members = client.get("/api/v1/members").json()
        write(args.out, "members.json", members)
        for member in members:
            lines = get_all(client, f"/api/v1/members/{member['id']}/opportunities")
            first = client.get(f"/api/v1/members/{member['id']}/opportunities", params={"size": 1}).json()
            write(args.out, f"opportunities/{member['id']}.json",
                  {"facility": first["facility"], "totalSavings": first["totalSavings"], "lines": lines})

        anomalies: list[dict[str, Any]] = []
        for status in ("OPEN", "CONFIRMED", "DISMISSED"):
            anomalies += get_all(client, "/api/v1/anomalies", {"status": status})
        write(args.out, "anomalies.json", anomalies)
        write(args.out, "overview.json", client.get("/api/v1/overview").json())
        write(args.out, "config.json", {"anomalyAlertsEnabled": True})

    write(args.out, "manifest.json", {
        "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "groups": len(chosen), "items": len(items), "source": "CMS NADAC; member data synthetic",
    })
    print(f"Wrote {len(items)} items in {len(chosen)} groups to {args.out}")


if __name__ == "__main__":
    main()
