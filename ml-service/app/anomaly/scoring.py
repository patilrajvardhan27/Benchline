"""Robust anomaly scoring for weekly price changes. Pure functions, no I/O.

A price change is measured as the natural log of new/old, so a drop from 2.00 to
1.00 and a rise from 1.00 to 2.00 are equal in size and opposite in sign. The
score is the modified z-score (Iglewicz and Hoaglin): 0.6745 * (x - median) / MAD.
Median and MAD barely move when a few extreme changes are in the history, unlike
mean and standard deviation.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

MAD_CONSTANT = 0.6745
IQR_MULTIPLIER = 1.5
# Smallest scale we divide by. A group whose past changes are all nearly identical
# has a MAD near zero, and any new change would look infinitely unusual.
MIN_SCALE = 0.005
MIN_IQR_SAMPLE = 4


@dataclass(frozen=True)
class Score:
    z: float
    median: float
    mad: float
    iqr_outlier: bool
    sample_size: int


def log_change(price: float, previous: float) -> float:
    if price <= 0 or previous <= 0:
        raise ValueError("prices must be positive")
    return math.log(price / previous)


def mad(values: list[float]) -> float:
    centre = statistics.median(values)
    return statistics.median([abs(v - centre) for v in values])


def iqr_outlier(x: float, history: list[float]) -> bool:
    """True when x lies beyond 1.5 IQR from the quartiles. Needs a few observations."""
    if len(history) < MIN_IQR_SAMPLE:
        return False
    q1, _, q3 = statistics.quantiles(history, n=4, method="inclusive")
    spread = q3 - q1
    return x < q1 - IQR_MULTIPLIER * spread or x > q3 + IQR_MULTIPLIER * spread


def score_change(x: float, history: list[float]) -> Score:
    if not history:
        raise ValueError("history must not be empty")
    median = statistics.median(history)
    spread = max(mad(history), MIN_SCALE)
    z = MAD_CONSTANT * (x - median) / spread
    return Score(z=z, median=median, mad=spread, iqr_outlier=iqr_outlier(x, history),
                 sample_size=len(history))


def is_anomaly(score: Score, threshold: float) -> bool:
    """Both tests must agree. The z-score alone flags too many tiny groups."""
    return abs(score.z) >= threshold and score.iqr_outlier
