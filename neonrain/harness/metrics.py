"""The metrics of HAR-07: accuracy, balanced accuracy, IC, Sharpe and the deflated Sharpe ratio.

Each returns None where HAR-07 says the metric is undefined, never a number standing in for one. Pure functions.
"""
import math
from typing import NamedTuple

import numpy as np
import polars as pl
from scipy.stats import norm, rankdata

EULER_GAMMA = 0.5772156649
TRADING_DAYS = 252
MIN_TICKERS = 20


class IC(NamedTuple):
    """HAR-07's information coefficient: the mean over dates, its standard error and t, and what was dropped."""

    mean: float | None
    standard_error: float | None
    t: float | None
    dates: int
    dropped_thin: int  # dates with fewer than min_tickers tested tickers
    dropped_flat: int  # dates whose scores, or labels, are all equal


def labelled(frame: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """The predictions (score > 0.5) and labels of the rows that have a direction label (a tie has none)."""
    rows = frame.filter(pl.col("direction").is_not_null())
    return rows["score"].to_numpy() > 0.5, rows["direction"].to_numpy() == 1


def accuracy(frame: pl.DataFrame) -> float | None:
    """The fraction of labelled rows where (score > 0.5) == (direction == 1). Scores 0.9, 0.2, 0.5 against
    directions 1, 0, 1 give 2/3 (0.5 predicts 0)."""
    predicted, actual = labelled(frame)
    return float(np.mean(predicted == actual)) if len(actual) else None


def balanced_accuracy(frame: pl.DataFrame) -> float | None:
    """The mean of the two classes' recalls; None if either class has no rows."""
    predicted, actual = labelled(frame)
    if actual.all() or not actual.any():
        return None
    return float((np.mean(predicted[actual]) + np.mean(~predicted[~actual])) / 2)


def spearman(scores: np.ndarray, labels: np.ndarray) -> float | None:
    """The Pearson correlation of the two rankings, ties averaged; None if either side is all one value.
    [1, 2, 3] against [0.0, 0.5, 1.0] gives 1; against [1.0, 0.5, 0.0] gives −1."""
    if scores.max() == scores.min() or labels.max() == labels.min():
        return None
    return float(np.corrcoef(rankdata(scores), rankdata(labels))[0, 1])


# Decision: R-005 (a thin or flat date is dropped and counted, never filled)
def information_coefficient(frame: pl.DataFrame, min_tickers: int = MIN_TICKERS) -> IC:
    """HAR-07's IC over a frame of date, score and rank (q of HAR-02), one row per tested ticker per date."""
    found: list[float] = []
    thin = flat = 0
    for day in sorted(set(frame["date"].to_list())):
        rows = frame.filter(pl.col("date") == day)
        if rows.height < min_tickers:
            thin += 1
            continue
        value = spearman(rows["score"].to_numpy(), rows["rank"].to_numpy())
        if value is None:
            flat += 1
            continue
        found.append(value)
    if not found:
        return IC(None, None, None, 0, thin, flat)
    mean = float(np.mean(found))
    if len(found) < 2:
        return IC(mean, None, None, 1, thin, flat)
    error = float(np.std(found, ddof=1) / math.sqrt(len(found)))
    return IC(mean, error, mean / error if error > 0 else None, len(found), thin, flat)


def daily_sharpe(daily: np.ndarray) -> float | None:
    """mean / sd (divisor T − 1), not annualized; None with fewer than two days or no variation."""
    if len(daily) < 2:
        return None
    spread = float(np.std(daily, ddof=1))
    return float(np.mean(daily)) / spread if spread > 0 else None


def sharpe(daily: np.ndarray) -> float | None:
    """HAR-07's Sharpe: the daily Sharpe times √252, on the after-cost series."""
    value = daily_sharpe(daily)
    return value * math.sqrt(TRADING_DAYS) if value is not None else None


def moments(daily: np.ndarray) -> tuple[float, float]:
    """Skewness m₃/m₂^1.5 and kurtosis m₄/m₂² (not excess), moments with divisor T."""
    centred = daily - np.mean(daily)
    m2, m3, m4 = (float(np.mean(centred**k)) for k in (2, 3, 4))
    return m3 / m2**1.5, m4 / m2**2


def expected_maximum(trials: int, variance: float | None) -> float:
    """SR₀ of HAR-07: the Sharpe expected from the best of `trials` with none real; 0 for one trial."""
    if trials == 1:
        return 0.0
    if variance is None:
        raise ValueError(f"{trials} trials need the variance of their Sharpes")
    tail = (1 - EULER_GAMMA) * norm.ppf(1 - 1 / trials) + EULER_GAMMA * norm.ppf(1 - 1 / (trials * math.e))
    return math.sqrt(variance) * float(tail)


def dsr_from(observed: float, floor: float, skew: float, kurt: float, days: int) -> float | None:
    """Z[(SR − SR₀)·√(T − 1) / √(1 − skew·SR + (kurt − 1)/4·SR²)]; None if the square root's argument is not
    positive. For real data it never is negative (kurt − 1 ≥ skew², so it is at least (1 − skew·SR/2)²); the
    guard is for float error at that edge."""
    under = 1 - skew * observed + (kurt - 1) / 4 * observed**2
    if under <= 0:
        return None
    return float(norm.cdf((observed - floor) * math.sqrt(days - 1) / math.sqrt(under)))


# Decision: R-005 (every trial counted: the deflation grows with the number of things tried)
def deflated_sharpe(daily: np.ndarray, trials: int, variance: float | None) -> float | None:
    """HAR-07's DSR: the probability the true Sharpe exceeds zero given `trials` tried, whose non-annualized
    Sharpes have sample variance `variance`. None where the Sharpe, or the square root, is undefined."""
    if trials < 1:
        raise ValueError(f"trials is {trials}: at least 1 (HAR-09)")
    observed = daily_sharpe(daily)
    if observed is None:
        return None
    skew, kurt = moments(daily)
    return dsr_from(observed, expected_maximum(trials, variance), skew, kurt, len(daily))
