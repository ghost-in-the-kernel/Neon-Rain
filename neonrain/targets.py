"""The labels (R-004, HAR-02): for each horizon, direction and rank of the excess return over the universe median.

Pure: frames in, frames out; no clock, no network, no state. The harness reads these; nothing here reads the harness.
"""
from datetime import date
from typing import NamedTuple

import polars as pl

HORIZONS: tuple[int, ...] = (3, 5, 21, 63)
MIN_TICKERS = 20


class Labels(NamedTuple):
    """One horizon's labels and the three counts HAR-02 requires beside every result."""

    frame: pl.DataFrame  # ticker, date, horizon, forward, excess, direction (null on a tie), rank
    dropped_missing: int  # cells with no price at t or at t+h
    dropped_ties: int  # cells whose excess is exactly 0: no direction label, rank kept
    dropped_thin_dates: int  # dates with fewer than min_tickers priced, eligible tickers


def cells(prices: pl.DataFrame, universe: pl.DataFrame, calendar: list[date], horizon: int) -> pl.DataFrame:
    """Each eligible (ticker, date) with an h-th trading date after it, and its closes at t and t+h (null if none).

    On a five-date calendar with horizon 3, only the first two dates make cells.
    """
    ahead = pl.DataFrame(
        {"date": calendar[:-horizon], "until": calendar[horizon:]},
        schema={"date": pl.Date, "until": pl.Date},
    )
    at_t = prices.select("ticker", "date", pl.col("close").alias("close_t"))
    at_h = prices.select("ticker", pl.col("date").alias("until"), pl.col("close").alias("close_h"))
    frame = universe.join(ahead, on="date")
    frame = frame.join(at_t, on=["ticker", "date"], how="left")
    return frame.join(at_h, on=["ticker", "until"], how="left")


def input_problems(prices: pl.DataFrame, universe: pl.DataFrame, calendar: list[date]) -> list[str]:
    """What makes the inputs unusable: a (ticker, date) twice in prices or universe, a calendar not strictly rising."""
    found = [f"{name} has a (ticker, date) twice" for name, frame in (("prices", prices), ("universe", universe))
             if frame.select("ticker", "date").is_duplicated().any()]
    if any(later <= earlier for earlier, later in zip(calendar, calendar[1:])):
        found.append("the calendar is not strictly increasing")
    return found


# Decision: R-004 (excess over the median of the eligible, priced tickers; direction and rank)
def labels(
    prices: pl.DataFrame, universe: pl.DataFrame, calendar: list[date], horizon: int, min_tickers: int = MIN_TICKERS
) -> Labels:
    """HAR-02 for one horizon. Three tickers returning +30%, 0% and −30% on a date get excess +0.3, 0, −0.3,
    direction 1, none (a tie) and 0, and rank 1, 0.5 and 0."""
    problems = input_problems(prices, universe, calendar)
    if min_tickers < 2:
        problems.append(f"min_tickers is {min_tickers}: a rank needs at least two tickers on a date")
    if problems:
        raise ValueError("; ".join(problems))
    frame = cells(prices, universe, calendar, horizon)
    priced = frame.filter(pl.col("close_t").is_not_null() & pl.col("close_h").is_not_null())
    missing = frame.height - priced.height
    priced = priced.with_columns(
        (pl.col("close_h") / pl.col("close_t") - 1.0).alias("forward"), pl.len().over("date").alias("n")
    )
    thin = priced.filter(pl.col("n") < min_tickers)["date"].n_unique()
    kept = priced.filter(pl.col("n") >= min_tickers)
    kept = kept.with_columns((pl.col("forward") - pl.col("forward").median().over("date")).alias("excess"))
    kept = kept.with_columns(
        pl.when(pl.col("excess") > 0).then(1).when(pl.col("excess") < 0).then(0).otherwise(None)
        .cast(pl.Int8).alias("direction"),
        ((pl.col("excess").rank("average").over("date") - 1.0) / (pl.col("n") - 1)).alias("rank"),
    )
    ties = kept.filter(pl.col("excess") == 0.0).height
    columns = ["ticker", "date", pl.lit(horizon).alias("horizon"), "forward", "excess", "direction", "rank"]
    return Labels(kept.select(columns).sort("date", "ticker"), missing, ties, thin)
