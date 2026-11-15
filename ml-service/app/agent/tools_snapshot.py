"""The agent's tools over the static demo snapshot (web/public/demo). Same answers, no database.

Used to record the demo's replay and to try the agent with a real model without the full stack.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.agent.results import (
    Benchmark,
    Flag,
    Product,
    anomalies_result,
    benchmark_result,
    equivalents_result,
    no_match,
    word_pattern,
)
from app.agent.tools import MAX_ROWS, ToolResult, query_words


class SnapshotTools:
    def __init__(self, demo_dir: Path) -> None:
        self._dir = demo_dir
        self._items: list[dict[str, Any]] = json.loads((demo_dir / "items.json").read_text())
        self._anomalies: list[dict[str, Any]] = json.loads((demo_dir / "anomalies.json").read_text())

    def _groups(self, drug: str) -> list[tuple[str, str]]:
        patterns = [re.compile(word_pattern(w)) for w in query_words(drug)]
        counts: dict[tuple[str, str], int] = {}
        for item in self._items:
            name = item["groupName"].upper()
            if all(p.search(name) for p in patterns):
                key = (item["groupId"], item["groupName"])
                counts[key] = counts.get(key, 0) + 1
        return sorted(counts, key=lambda k: (-counts[k], k[1]))[:4]

    def _products(self, group_id: str) -> list[Product]:
        products = [Product(i["id"], i["ndc11"], i["description"], Decimal(i["latestPrice"]),
                            i["latestEffectiveDate"]) for i in self._items if i["groupId"] == group_id]
        return sorted(products, key=lambda p: (p.latest_price, p.item_id))

    def get_benchmark(self, drug: str) -> ToolResult:
        groups = self._groups(drug)
        for group_id, name in groups:
            path = self._dir / "benchmarks" / f"{group_id}.json"
            if not path.exists():
                continue
            s = json.loads(path.read_text())["history"]["snapshots"][-1]
            b = Benchmark(group_id, name, s["asOfWeek"], Decimal(s["p10"]), Decimal(s["p25"]),
                          Decimal(s["p50"]), Decimal(s["p75"]), Decimal(s["p90"]), int(s["nObs"]))
            others = [n for g, n in groups if g != group_id]
            return benchmark_result(b, self._products(group_id)[:2], others)
        return no_match(drug)

    def find_equivalents(self, drug: str) -> ToolResult:
        groups = self._groups(drug)
        if not groups:
            return no_match(drug)
        group_id, name = groups[0]
        products = self._products(group_id)
        return equivalents_result(name, group_id, products[:MAX_ROWS], len(products))

    def list_anomalies(self, drug: str | None, limit: int) -> ToolResult:
        wanted = {g for g, _ in self._groups(drug)} if drug else None
        descriptions = {i["id"]: i["description"] for i in self._items}
        rows = [a for a in self._anomalies if a["status"] != "DISMISSED"
                and (wanted is None or a["groupId"] in wanted)]
        rows.sort(key=lambda a: (a["effectiveDate"], a["score"]), reverse=True)
        flags = [Flag(a["itemId"], descriptions.get(a["itemId"], a["groupName"]), a["groupName"],
                      Decimal(a["previousUnitPrice"]) if a.get("previousUnitPrice") else None,
                      Decimal(a["unitPrice"]), a["effectiveDate"], float(a["score"]), a["status"])
                 for a in rows[:limit]]
        return anomalies_result(flags, drug)
