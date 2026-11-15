"""Tool results built the same way whether the data comes from Postgres or the demo snapshot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.agent.events import Citation
from app.agent.tools import ToolResult


@dataclass(frozen=True)
class Product:
    item_id: str
    ndc11: str
    description: str
    latest_price: Decimal
    effective_date: str


@dataclass(frozen=True)
class Benchmark:
    group_id: str
    group: str
    as_of_week: str
    p10: Decimal
    p25: Decimal
    p50: Decimal
    p75: Decimal
    p90: Decimal
    n_obs: int


@dataclass(frozen=True)
class Flag:
    item_id: str
    description: str
    group: str
    previous_price: Decimal | None
    new_price: Decimal
    effective_date: str
    score: float
    status: str


def word_pattern(word: str) -> str:
    """Numbers match whole ('50' never matches '150'); words match a word start ('TAB' matches 'TABLET').

    Plain POSIX syntax, so the same pattern works in Python and in Postgres.
    """
    start = rf"(^|[^A-Z0-9]){re.escape(word)}"
    return start + "([^A-Z0-9]|$)" if word[0].isdigit() else start


def no_match(drug: str) -> ToolResult:
    return ToolResult(True, f"No product group matches '{drug}'", {"found": False})


def benchmark_result(b: Benchmark, cheapest: list[Product], others: list[str]) -> ToolResult:
    data = {
        "found": True, "group": b.group, "group_id": b.group_id, "as_of_week": b.as_of_week,
        "unit_price_usd": {"p10": str(b.p10), "p25": str(b.p25), "median": str(b.p50),
                           "p75": str(b.p75), "p90": str(b.p90)},
        "products_in_benchmark": b.n_obs,
        "cheapest_products": [_product(p) for p in cheapest],
        "other_matching_groups": others,
    }
    summary = f"{b.group}, week of {b.as_of_week}: median ${b.p50} per unit across {b.n_obs} products"
    return ToolResult(True, summary, data, [_cite(p) for p in cheapest])


def equivalents_result(group: str, group_id: str, products: list[Product], total: int) -> ToolResult:
    data = {"found": True, "group": group, "group_id": group_id, "total_products": total,
            "products": [_product(p) for p in products]}
    summary = f"{total} equivalent products for {group}"
    if products:
        summary += f"; cheapest ${products[0].latest_price} per unit"
    return ToolResult(True, summary, data, [_cite(p) for p in products[:5]])


def anomalies_result(flags: list[Flag], drug: str | None) -> ToolResult:
    rows = [{"item_id": f.item_id, "description": f.description, "group": f.group,
             "previous_price": str(f.previous_price) if f.previous_price is not None else None,
             "new_price": str(f.new_price), "change_pct": _change(f), "effective_date": f.effective_date,
             "score": f.score, "status": f.status} for f in flags]
    scope = f" for {drug}" if drug else ""
    summary = f"{len(flags)} flagged price move{'s' if len(flags) != 1 else ''}{scope}"
    cites = list({f.item_id: Citation(f.item_id, f"{f.description} (NDC {f.item_id.removeprefix('ndc-')})")
                  for f in flags}.values())
    return ToolResult(True, summary, {"found": bool(flags), "anomalies": rows}, cites)


def _product(p: Product) -> dict[str, str]:
    return {"item_id": p.item_id, "ndc11": p.ndc11, "description": p.description,
            "latest_price": str(p.latest_price), "effective_date": p.effective_date}


def _cite(p: Product) -> Citation:
    return Citation(p.item_id, f"{p.description} (NDC {p.ndc11})")


def _change(f: Flag) -> str | None:
    if not f.previous_price:
        return None
    return f"{(f.new_price - f.previous_price) / f.previous_price * 100:+.1f}"
