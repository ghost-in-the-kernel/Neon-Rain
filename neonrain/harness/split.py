"""The grid of R-005 × R-014: walk-forward folds with purge and embargo (HAR-03, HAR-04), and ticker groups (HAR-05).

Every position is an index into the calendar, so "the h-th trading date after t" is position + h. No shuffling,
ever (HAR-03): rows are only ever selected by their date's position and their ticker's group.
"""
import hashlib
from datetime import date
from typing import NamedTuple

import polars as pl

from neonrain.targets import HORIZONS

LONGEST = max(HORIZONS)  # the longest horizon of R-004
EMBARGO = LONGEST
STEP = 126
MIN_TRAIN = 756
GROUPS = 5


class Fold(NamedTuple):
    """One fold's spans as calendar positions, each end exclusive: train [a, b), embargo [b, b+E), test [b+E, c)."""

    number: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int


# Decision: R-005 (one embargo of at least the longest horizon, the same folds for every horizon)
def folds(days: int, embargo: int = EMBARGO, step: int = STEP, min_train: int = MIN_TRAIN,
          window: int | None = None) -> list[Fold]:
    """The folds on a calendar of `days` dates. With the defaults the first is train [0, 819), embargo
    [819, 882), test [882, 1008): 819 − 63 = 756 dates survive purging at 63 days."""
    if embargo < LONGEST:
        raise ValueError(f"embargo is {embargo}: at least {LONGEST}, the longest horizon (HAR-03)")
    if step < 1:
        raise ValueError(f"step is {step}: at least 1")
    if window is not None and window - LONGEST < min_train:
        raise ValueError(f"window is {window}: at least {min_train + LONGEST} to keep {min_train} after purging")
    ends = range(min_train + LONGEST, days - embargo - step + 1, step)
    starts = [0 if window is None else max(0, end - window) for end in ends]
    return [Fold(n, start, end, end + embargo, end + embargo + step) for n, (start, end) in enumerate(zip(starts, ends))]


def positions(calendar: list[date]) -> pl.DataFrame:
    """Each date's position: [2000-01-03, 2000-01-04] gives rows (2000-01-03, 0), (2000-01-04, 1)."""
    return pl.DataFrame({"date": calendar, "position": range(len(calendar))},
                        schema={"date": pl.Date, "position": pl.Int64})


def training(rows: pl.DataFrame, fold: Fold, calendar: list[date], horizon: int) -> pl.DataFrame:
    """The fold's training rows after purging (HAR-03): dated in [a, b), and their label window ends before b,
    so the row at position t stays only if t + horizon < b."""
    at = rows.join(positions(calendar), on="date")
    kept = at.filter((pl.col("position") >= fold.train_start) & (pl.col("position") + horizon < fold.train_end))
    return kept.drop("position")


def testing(rows: pl.DataFrame, fold: Fold, calendar: list[date]) -> pl.DataFrame:
    """The fold's test rows, never purged: dated in [b + E, c)."""
    at = rows.join(positions(calendar), on="date")
    kept = at.filter((pl.col("position") >= fold.test_start) & (pl.col("position") < fold.test_end))
    return kept.drop("position")


# Decision: R-014 (a fixed, seeded hash of the ticker; a ticker keeps its group for the whole run)
def group_of(ticker: str, k: int, seed: int) -> int:
    """HAR-05's group: int(sha256(f"{seed}:{ticker}"), 16) % k."""
    return int(hashlib.sha256(f"{seed}:{ticker}".encode()).hexdigest(), 16) % k


def ticker_groups(tickers: list[str], k: int = GROUPS, seed: int = 0) -> dict[str, int]:
    """Every ticker's group; refused when a group is left empty, since its grid cells would test nothing."""
    groups = {ticker: group_of(ticker, k, seed) for ticker in sorted(set(tickers))}
    empty = sorted(set(range(k)) - set(groups.values()))
    if empty:
        raise ValueError(f"groups {empty} of {k} are empty for {len(groups)} tickers with seed {seed}")
    return groups


def cell(rows: pl.DataFrame, fold: Fold, calendar: list[date], horizon: int, groups: dict[str, int],
         held_out: int) -> tuple[pl.DataFrame, pl.DataFrame]:
    """One cell of the grid (HAR-05): train on the fold's purged training rows of the other groups, test on its
    test rows of the held-out group. A ticker with no group, or training on fewer than two tickers, is refused."""
    unmapped = sorted(set(rows["ticker"].unique().to_list()) - set(groups))
    if unmapped:
        raise ValueError(f"tickers with no group: {unmapped[:5]}")
    others = [ticker for ticker, group in groups.items() if group != held_out]
    held = [ticker for ticker, group in groups.items() if group == held_out]
    train = training(rows, fold, calendar, horizon).filter(pl.col("ticker").is_in(others))
    test = testing(rows, fold, calendar).filter(pl.col("ticker").is_in(held))
    if train["ticker"].n_unique() < 2:
        raise ValueError(f"fold {fold.number}, group {held_out}: training has fewer than two tickers (R-014)")
    return train, test
