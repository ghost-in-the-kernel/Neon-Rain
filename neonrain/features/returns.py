"""The returns family (TODO 2.3): the adjusted close over its close k sessions earlier, minus 1, for k in LOOKBACKS.

Pure functions from the price frame (docs/HARNESS.md: `ticker`, `date`, the adjusted `close`, a total-return price) to
the harness's feature frame: `ticker`, `date`, then for each lookback k the feature `ret_k` and its stamp `ret_k_stamp`
(HAR-12). One row for each price row, in the order (ticker, date) ascending.

**Lookbacks** are counted in sessions of the calendar, never in calendar days. They are the four horizons, 3, 5, 21 and
63 (neonrain.targets.HORIZONS): the network looks back as far as it must look ahead, and nothing shorter or longer is
a second guess about what the data holds. A one-session return is left to the volatility family (a later task).

**Point in time.** `ret_k` at *t* reads the closes of *t* and of the session *k* before it, so its stamp is *t*, the
date of the latest close used (HAR-12: a close is known at its own date). No later row is read.

**Missing data is never filled.** The value at *t* needs a usable close (present, finite, above zero) on every one of
the k+1 sessions from *t*-k to *t*. A ticker's first k sessions have none; a window that reaches before its first
price, or has a session with no row or no usable close anywhere in it, has none, and neither has a window that
crosses a gap: a missing row may be a halt or an unrecorded split, and a return across it would claim a price move
the data does not show. The cell keeps its row, with a null value and a null stamp (HAR-12: the stamp may be null
where the value is). A ticker is never merged, split or dropped (NR-F-05): a reused ticker is one ticker, and a gap
of any length inside it nulls the windows that cross it, so a window that reaches back over a reuse has no value
(a reuse gap is 180 days or more, longer than the 63 sessions of the longest lookback, so no window both ends in
and crosses it).
"""
from datetime import date

import polars as pl

LOOKBACKS: tuple[int, ...] = (3, 5, 21, 63)  # the four horizons, in sessions of the calendar
STAMP_SUFFIX = "_stamp"  # the harness's (neonrain.harness.market.STAMP_SUFFIX); features may not import the harness


class OffCalendar(ValueError):
    """A price row on a date that is not on the calendar: its place in the sessions is unknown."""


def name(lookback: int) -> str:
    """The feature's column name: ret_3, ret_5, ret_21, ret_63."""
    return f"ret_{lookback}"


def feature_columns() -> list[str]:
    """The feature frame's columns after the keys, in order: each feature then its stamp."""
    return [column for k in LOOKBACKS for column in (name(k), name(k) + STAMP_SUFFIX)]


def usable(close: str = "close") -> pl.Expr:
    """Whether a close can be divided by: present, finite and above zero."""
    return pl.col(close).is_not_null() & pl.col(close).is_finite() & (pl.col(close) > 0)


def positioned(prices: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """The price rows with `pos`, the index of the row's date on the calendar; refuses a date the calendar lacks."""
    places = pl.DataFrame({"date": calendar, "pos": range(len(calendar))}, schema={"date": pl.Date, "pos": pl.Int64})
    framed = prices.select("ticker", "date", "close").join(places, on="date", how="left")
    off = framed.filter(pl.col("pos").is_null()).sort("ticker", "date")
    if off.height:
        raise OffCalendar(f"price row ({off['ticker'][0]}, {off['date'][0]}) is off the calendar")
    return framed


# Decision: NR-F-05 (no gap is crossed and no ticker is merged), HAR-12 (the stamp is the date of the latest close used)
def of_lookback(rows: pl.DataFrame, lookback: int) -> pl.DataFrame:
    """ticker, date, then the feature and its stamp for one lookback, from usable rows with `pos`, sorted by (ticker, pos).

    The row k rows earlier of the same ticker is exactly k sessions earlier only when no session between has gone
    missing, so a `pos` difference of k is a window with every session present; any other row has no value.
    """
    base = pl.col("close").shift(lookback).over("ticker")
    whole = (pl.col("pos") - pl.col("pos").shift(lookback).over("ticker")) == lookback
    value = pl.when(whole).then(pl.col("close") / base - 1.0).otherwise(None)
    return rows.select(
        "ticker", "date",
        value.alias(name(lookback)),
        pl.when(whole).then(pl.col("date")).otherwise(None).alias(name(lookback) + STAMP_SUFFIX),
    )


def returns(prices: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """The returns family for every price row: ticker, date, then ret_k and ret_k_stamp for each k in LOOKBACKS.

    `prices` is the harness's price frame; `calendar` the trading dates, strictly ascending, which every price date
    must be on (OffCalendar otherwise). A row whose own close is unusable keeps its cell with null values.
    """
    framed = positioned(prices, calendar).sort("ticker", "pos")
    good = framed.filter(usable())
    frame = framed.select("ticker", "date")
    for lookback in LOOKBACKS:
        frame = frame.join(of_lookback(good, lookback), on=["ticker", "date"], how="left")
    return frame
