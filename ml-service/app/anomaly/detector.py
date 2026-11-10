"""Turns one price event into zero or one anomaly row."""

from __future__ import annotations

import logging

from app.anomaly.events import PricePointRecorded
from app.anomaly.repository import AnomalyRepository
from app.anomaly.scoring import is_anomaly, log_change, score_change

log = logging.getLogger(__name__)

METHOD = "robust-z/log-change"
EXPECTED_TYPE = "pricing.price-point-recorded.v1"


class AnomalyDetector:
    def __init__(
        self,
        repo: AnomalyRepository,
        threshold: float = 3.5,
        min_group_history: int = 8,
        history_weeks: int = 52,
    ) -> None:
        self._repo = repo
        self._threshold = threshold
        self._min_group_history = min_group_history
        self._days = history_weeks * 7

    def handle(self, event: PricePointRecorded) -> bool:
        """Return True if an anomaly row was created."""
        if event.type != EXPECTED_TYPE:
            raise ValueError(f"unexpected event type {event.type!r}")
        data = event.data
        if data.previous_unit_price is None:
            return False  # first price for this item, nothing to compare with

        change = log_change(float(data.unit_price), float(data.previous_unit_price))
        history = self._repo.group_changes(data.item_group_id, data.price_point_id, self._days)
        if len(history) < self._min_group_history:
            # A thin group says little about what is normal; use all groups instead.
            history = self._repo.pooled_changes(data.price_point_id, self._days)
        if not history:
            return False

        score = score_change(change, history)
        if not is_anomaly(score, self._threshold):
            return False
        created = self._repo.insert_anomaly(
            data.price_point_id, data.item_group_id, score.z, METHOD
        )
        if created:
            log.info("anomaly group=%s z=%.2f n=%d", data.item_group_id, score.z, score.sample_size)
        return created
