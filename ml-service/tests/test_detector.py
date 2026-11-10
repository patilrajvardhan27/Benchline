import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.anomaly.detector import METHOD, AnomalyDetector
from app.anomaly.events import PricePointData, PricePointRecorded

CALM = [-0.02, -0.01, 0.0, 0.01, 0.02, 0.03, -0.03, 0.015, -0.015, 0.005]


class FakeRepo:
    def __init__(self, group: list[float], pooled: list[float] | None = None) -> None:
        self.group = group
        self.pooled = pooled or []
        self.inserted: list[tuple[uuid.UUID, str, float, str]] = []
        self.pooled_calls = 0

    def group_changes(self, group_id: str, exclude: uuid.UUID, days: int) -> list[float]:
        return self.group

    def pooled_changes(self, exclude: uuid.UUID, days: int) -> list[float]:
        self.pooled_calls += 1
        return self.pooled

    def insert_anomaly(
        self, price_point_id: uuid.UUID, group_id: str, score: float, method: str
    ) -> bool:
        if any(row[0] == price_point_id for row in self.inserted):
            return False
        self.inserted.append((price_point_id, group_id, score, method))
        return True


def event(
    price: str, previous: str | None, kind: str = "pricing.price-point-recorded.v1"
) -> PricePointRecorded:
    return PricePointRecorded(
        id=uuid.uuid4(),
        type=kind,
        data=PricePointData(
            pricePointId=uuid.uuid4(),
            itemId="ndc-1",
            itemGroupId="grp-a",
            source="NADAC",
            unitPrice=Decimal(price),
            previousUnitPrice=Decimal(previous) if previous else None,
            effectiveDate=date(2026, 10, 29),
        ),
    )


def test_a_normal_change_is_not_flagged() -> None:
    repo = FakeRepo(CALM)
    assert AnomalyDetector(repo).handle(event("1.01", "1.00")) is False
    assert repo.inserted == []


def test_a_tripling_is_flagged_once() -> None:
    repo = FakeRepo(CALM)
    e = event("3.00", "1.00")
    detector = AnomalyDetector(repo)
    assert detector.handle(e) is True
    assert detector.handle(e) is False  # redelivered event does not create a second row
    assert len(repo.inserted) == 1
    assert repo.inserted[0][3] == METHOD
    assert repo.inserted[0][2] > 3.5


def test_first_price_has_nothing_to_compare() -> None:
    repo = FakeRepo(CALM)
    assert AnomalyDetector(repo).handle(event("1.00", None)) is False
    assert repo.pooled_calls == 0


def test_thin_group_falls_back_to_pooled_history() -> None:
    repo = FakeRepo(group=[0.01, 0.02], pooled=CALM)
    assert AnomalyDetector(repo).handle(event("3.00", "1.00")) is True
    assert repo.pooled_calls == 1


def test_no_history_anywhere_means_no_flag() -> None:
    assert AnomalyDetector(FakeRepo([], [])).handle(event("3.00", "1.00")) is False


def test_wrong_event_type_is_an_error() -> None:
    with pytest.raises(ValueError, match="unexpected event type"):
        AnomalyDetector(FakeRepo(CALM)).handle(event("1", "1", kind="something.else.v1"))
