"""Deterministic synthetic facilities and purchase lines. Pure: no database, no clock.

Used by seed_synthetic.py (writes to PostgreSQL) and build_demo_snapshot.py (writes JSON),
so both produce the same data for the same seed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

NAMES = ["Riverside General", "Northgate Medical", "St. Anselm Regional", "Lakeview Community",
         "Ridgeback University", "Harbor Point", "Cedar Valley", "Summit County"]
REGIONS = ["Northeast", "South", "Midwest", "West"]
BED_BANDS = ["under 100", "100-199", "200-399", "400-699", "700 and over"]
MIN_PRICE = Decimal("0.00001")


@dataclass(frozen=True)
class SyntheticFacility:
    id: str
    name: str
    bed_band: str
    region: str


@dataclass(frozen=True)
class SyntheticLine:
    facility_id: str
    item_id: str
    unit_price: Decimal
    qty: int
    purchased_on: date


def generate(
    items: list[tuple[str, Decimal]],
    facilities: int,
    lines_each: int,
    seed: int,
    today: date,
) -> tuple[list[SyntheticFacility], list[SyntheticLine]]:
    """`items` is (item id, current market price). `today` anchors the purchase dates."""
    if not items:
        raise ValueError("items must not be empty")
    rng = random.Random(seed)
    made_facilities: list[SyntheticFacility] = []
    made_lines: list[SyntheticLine] = []
    for n in range(facilities):
        facility = SyntheticFacility(
            id=f"fac-{n + 1:02d}",
            name=NAMES[n % len(NAMES)],
            bed_band=rng.choice(BED_BANDS),
            region=rng.choice(REGIONS),
        )
        made_facilities.append(facility)
        # Each facility has its own habit: some buy close to the market, some well above.
        premium = rng.uniform(1.05, 1.6)
        for item_id, market in rng.sample(items, min(lines_each, len(items))):
            factor = max(rng.gauss(premium, 0.35), 0.7)
            price = (market * Decimal(str(round(factor, 4)))).quantize(MIN_PRICE)
            made_lines.append(SyntheticLine(
                facility_id=facility.id,
                item_id=item_id,
                unit_price=max(price, MIN_PRICE),
                qty=rng.randint(100, 20000),
                purchased_on=today - timedelta(days=rng.randint(1, 90)),
            ))
    return made_facilities, made_lines
