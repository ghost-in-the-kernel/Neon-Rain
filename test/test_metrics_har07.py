"""HAR-07's metrics by hand (R-015d): each number below can be checked in a spreadsheet."""
import math
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest
from scipy import stats

from neonrain.harness import metrics

DAYS = [date(2000, 1, 3) + timedelta(days=d) for d in range(4)]


def directions(scores: list[float], labels: list[int | None]) -> pl.DataFrame:
    return pl.DataFrame({"score": scores, "direction": labels}, schema={"score": pl.Float64, "direction": pl.Int8})


def test_accuracy_by_hand() -> None:
    # Labelled rows: 0.9→1 right, 0.2→0 right, 0.5→1 wrong (0.5 predicts 0); the tie (None) is left out. 2/3.
    frame = directions([0.9, 0.2, 0.5, 0.7], [1, 0, 1, None])
    assert metrics.accuracy(frame) == pytest.approx(2 / 3)


def test_balanced_accuracy_by_hand() -> None:
    # Class 1: rows 0.9 (right) and 0.5 (wrong): recall 1/2. Class 0: row 0.2 (right): recall 1. Mean 3/4.
    assert metrics.balanced_accuracy(directions([0.9, 0.2, 0.5, 0.7], [1, 0, 1, None])) == pytest.approx(0.75)
    # Unbalanced classes: accuracy 3/4 flatters a model that always says 1; balanced accuracy says 1/2.
    always = directions([0.9, 0.9, 0.9, 0.9], [1, 1, 1, 0])
    assert metrics.accuracy(always) == 0.75 and metrics.balanced_accuracy(always) == 0.5


def test_undefined_accuracies_are_none() -> None:
    assert metrics.balanced_accuracy(directions([0.9, 0.1], [1, 1])) is None
    assert metrics.balanced_accuracy(directions([0.9, 0.1], [0, 0])) is None
    assert metrics.accuracy(directions([0.9], [None])) is None
    assert metrics.balanced_accuracy(directions([0.9], [None])) is None


def test_spearman_by_hand() -> None:
    assert metrics.spearman(np.array([1.0, 2.0, 3.0]), np.array([0.0, 0.5, 1.0])) == pytest.approx(1.0)
    assert metrics.spearman(np.array([1.0, 2.0, 3.0]), np.array([1.0, 0.5, 0.0])) == pytest.approx(-1.0)
    # Ties averaged: ranks [1.5, 1.5, 3, 4] against [1, 2, 3, 4]; r = 4.5 / √(4.5 · 5) = 3/√10.
    assert metrics.spearman(np.array([1.0, 1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0, 4.0])) == pytest.approx(3 / math.sqrt(10))
    assert metrics.spearman(np.array([2.0, 2.0]), np.array([1.0, 2.0])) is None
    assert metrics.spearman(np.array([1.0, 2.0]), np.array([0.5, 0.5])) is None


def ic_frame(days: list[tuple[list[float], list[float]]]) -> pl.DataFrame:
    rows = [(DAYS[d], s, q) for d, (scores, ranks) in enumerate(days) for s, q in zip(scores, ranks)]
    return pl.DataFrame(rows, schema={"date": pl.Date, "score": pl.Float64, "rank": pl.Float64}, orient="row")


def test_information_coefficient_by_hand() -> None:
    # Day 0: r = 1. Day 1: r = 3/√10 ≈ 0.9487. Day 2: flat scores, dropped. Day 3: two tickers, thin (min 3).
    frame = ic_frame([([1, 2, 3, 4], [0, 1 / 3, 2 / 3, 1]), ([1, 1, 2, 3], [0, 1 / 3, 2 / 3, 1]),
                      ([5, 5, 5, 5], [0, 1 / 3, 2 / 3, 1]), ([1, 2], [0, 1])])
    found = metrics.information_coefficient(frame, min_tickers=3)
    values = [1.0, 3 / math.sqrt(10)]
    error = abs(values[0] - values[1]) / math.sqrt(2) / math.sqrt(2)  # sd with divisor n − 1 = 1, over √2
    assert found.mean == pytest.approx(sum(values) / 2) and found.standard_error == pytest.approx(error)
    assert found.t == pytest.approx(found.mean / error)
    assert (found.dates, found.dropped_thin, found.dropped_flat) == (2, 1, 1)


def test_every_dropped_date_is_counted_and_a_dropped_date_stops_nothing() -> None:
    # Days 0 and 1 thin (two tickers), day 2 flat labels, day 3 flat scores, then two good days.
    days = [date(2000, 1, 3) + timedelta(days=d) for d in range(6)]
    data = [([1, 2], [0, 1]), ([1, 2], [0, 1]), ([1, 2, 3], [0.5, 0.5, 0.5]), ([4, 4, 4], [0, 0.5, 1]),
            ([1, 2, 3], [0, 0.5, 1]), ([3, 2, 1], [0, 0.5, 1])]
    rows = [(days[d], s, q) for d, (scores, ranks) in enumerate(data) for s, q in zip(scores, ranks)]
    frame = pl.DataFrame(rows, schema={"date": pl.Date, "score": pl.Float64, "rank": pl.Float64}, orient="row")
    found = metrics.information_coefficient(frame, min_tickers=3)
    assert (found.mean, found.dates, found.dropped_thin, found.dropped_flat) == (0.0, 2, 2, 2)


def test_information_coefficient_edges() -> None:
    one = metrics.information_coefficient(ic_frame([([1, 2, 3], [0, 0.5, 1])]), min_tickers=3)
    assert one == metrics.IC(1.0, None, None, 1, 0, 0)
    same = metrics.information_coefficient(ic_frame([([1, 2, 3], [0, 0.5, 1]), ([4, 5, 6], [0, 0.5, 1])]), 3)
    assert same.mean == 1.0 and same.standard_error == 0.0 and same.t is None and same.dates == 2
    none = metrics.information_coefficient(ic_frame([([1, 2], [0, 1])]))
    assert none == metrics.IC(None, None, None, 0, 1, 0)
    assert metrics.MIN_TICKERS == 20


def test_sharpe_by_hand() -> None:
    # [0.01, 0.02, 0.03, 0.04]: mean 0.025, sd (divisor 3) √(0.0005/3) ≈ 0.012910; daily 1.9365, × √252.
    daily = np.array([0.01, 0.02, 0.03, 0.04])
    assert metrics.daily_sharpe(daily) == pytest.approx(0.025 / math.sqrt(0.0005 / 3))
    assert metrics.sharpe(daily) == pytest.approx(0.025 / math.sqrt(0.0005 / 3) * math.sqrt(252))
    assert metrics.sharpe(np.array([0.01])) is None and metrics.sharpe(np.array([0.01, 0.01])) is None
    # Two days are enough: [0.01, 0.03], mean 0.02, sd √0.0002.
    assert metrics.daily_sharpe(np.array([0.01, 0.03])) == pytest.approx(0.02 / math.sqrt(0.0002))
    assert metrics.TRADING_DAYS == 252


def test_moments_by_hand_and_against_scipy() -> None:
    # [1, 2, 3, 10]: mean 4, deviations −3, −2, −1, 6; m2 = 12.5, m3 = 45, m4 = 348.5.
    skew, kurt = metrics.moments(np.array([1.0, 2.0, 3.0, 10.0]))
    assert skew == pytest.approx(45 / 12.5**1.5) and kurt == pytest.approx(348.5 / 12.5**2)
    sample = np.random.default_rng(0).standard_t(5, 500)
    assert metrics.moments(sample) == pytest.approx((stats.skew(sample), stats.kurtosis(sample, fisher=False)))


def test_expected_maximum_is_near_the_true_expected_maximum_of_normals() -> None:
    # HAR-07's SR₀ approximates E[max of N standard normals] × √V: about 1.5388 for 10, 2.5076 for 100.
    assert metrics.expected_maximum(1, None) == 0.0
    assert metrics.expected_maximum(10, 1.0) == pytest.approx(1.5388, abs=0.05)
    assert metrics.expected_maximum(100, 1.0) == pytest.approx(2.5076, abs=0.05)
    assert metrics.expected_maximum(100, 0.04) == pytest.approx(0.2 * metrics.expected_maximum(100, 1.0))
    with pytest.raises(ValueError, match="10 trials need the variance"):
        metrics.expected_maximum(10, None)


def test_dsr_from_by_hand() -> None:
    # SR 0.1, SR₀ 0, normal shape (skew 0, kurt 3), T = 101: Z[0.1 · 10 / √(1 + 0.5 · 0.01)].
    assert metrics.dsr_from(0.1, 0.0, 0.0, 3.0, 101) == pytest.approx(stats.norm.cdf(1.0 / math.sqrt(1.005)))
    assert metrics.dsr_from(0.1, 0.1, 0.0, 3.0, 101) == pytest.approx(0.5)
    # Under the root 1 − 0.2 + 0.005 = 0.805: below 1, still defined.
    assert metrics.dsr_from(0.1, 0.0, 2.0, 3.0, 101) == pytest.approx(stats.norm.cdf(1.0 / math.sqrt(0.805)))
    assert metrics.dsr_from(1.0, 0.0, 2.0, 1.0, 101) is None  # 1 − 2 + 0 < 0
    assert metrics.dsr_from(1.0, 0.0, 2.0, 5.0, 101) is None  # 1 − 2 + 1 = 0


def test_deflated_sharpe_falls_as_more_is_tried() -> None:
    daily = np.random.default_rng(1).normal(0.001, 0.01, 750)
    one = metrics.deflated_sharpe(daily, 1, None)
    many = metrics.deflated_sharpe(daily, 100, 0.0025)
    assert one is not None and many is not None and 0 < many < one < 1
    skew, kurt = metrics.moments(daily)
    observed = daily.mean() / daily.std(ddof=1)
    assert one == pytest.approx(stats.norm.cdf(observed * math.sqrt(749) / math.sqrt(1 - skew * observed + (kurt - 1) / 4 * observed**2)))


def test_deflated_sharpe_edges() -> None:
    assert metrics.deflated_sharpe(np.array([0.01, 0.01, 0.01]), 1, None) is None
    with pytest.raises(ValueError, match="trials is 0"):
        metrics.deflated_sharpe(np.array([0.01, 0.02]), 0, None)
