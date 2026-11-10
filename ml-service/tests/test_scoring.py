import math

import pytest

from app.anomaly.scoring import (
    MIN_SCALE,
    Score,
    iqr_outlier,
    is_anomaly,
    log_change,
    mad,
    score_change,
)

HISTORY = [-0.02, -0.01, 0.0, 0.01, 0.02, 0.03, -0.03, 0.015, -0.015]


def test_log_change_is_symmetric() -> None:
    assert log_change(2.0, 1.0) == pytest.approx(-log_change(1.0, 2.0))
    assert log_change(1.0, 1.0) == 0.0


def test_log_change_rejects_non_positive_prices() -> None:
    with pytest.raises(ValueError, match="positive"):
        log_change(0, 1)


def test_mad_matches_hand_calculation() -> None:
    # median 3; absolute deviations 2 1 0 1 2 -> median 1
    assert mad([1, 2, 3, 4, 5]) == 1


def test_score_matches_hand_calculation() -> None:
    history = [1.0, 2.0, 3.0, 4.0, 5.0]
    score = score_change(8.0, history)
    # 0.6745 * (8 - 3) / 1
    assert score.z == pytest.approx(3.3725)
    assert score.median == 3.0
    assert score.mad == 1.0


def test_typical_change_scores_near_zero() -> None:
    assert abs(score_change(0.005, HISTORY).z) < 1


def test_large_jump_is_flagged_in_both_directions() -> None:
    up = score_change(math.log(3), HISTORY)
    down = score_change(math.log(1 / 3), HISTORY)
    assert up.z > 3.5 and down.z < -3.5
    assert is_anomaly(up, 3.5) and is_anomaly(down, 3.5)


def test_scale_never_falls_below_the_floor() -> None:
    flat = [0.01] * 10  # MAD is exactly zero
    score = score_change(0.02, flat)
    assert score.mad == MIN_SCALE
    assert math.isfinite(score.z)


def test_extreme_history_values_do_not_hide_an_outlier() -> None:
    # A mean and standard deviation would be dragged up by the 5.0; median and MAD are not.
    history = [*HISTORY, 5.0]
    assert score_change(math.log(3), history).z > 3.5


def test_iqr_fence() -> None:
    assert iqr_outlier(1.0, HISTORY)
    assert not iqr_outlier(0.01, HISTORY)
    assert not iqr_outlier(1.0, [0.0, 0.1])  # too few observations to judge


def test_both_tests_must_agree() -> None:
    high_z_only = Score(z=4.0, median=0, mad=0.01, iqr_outlier=False, sample_size=20)
    iqr_only = Score(z=1.0, median=0, mad=0.01, iqr_outlier=True, sample_size=20)
    assert not is_anomaly(high_z_only, 3.5)
    assert not is_anomaly(iqr_only, 3.5)


def test_empty_history_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        score_change(0.1, [])
