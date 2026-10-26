"""What the price-derived feature families share (TODO 2.3): the stamp suffix, the calendar refusal, the position of a row.

Moved here from `returns.py` at the third family (volume ratios), which the second (volatility) had asked for. The
families import these names from here; `returns` and `volatility` still export them under the names they had.
Features may not import the harness (MOD-02's mirror: the referee and the players stay apart), so `STAMP_SUFFIX` is
copied from `neonrain.harness.market` and a test holds the two equal.
"""
from datetime import date

import polars as pl

STAMP_SUFFIX = "_stamp"  # the harness's (neonrain.harness.market.STAMP_SUFFIX); features may not import the harness


class OffCalendar(ValueError):
    """A price row on a date that is not on the calendar: its place in the sessions is unknown."""


def usable(close: str = "close") -> pl.Expr:
    """Whether a close can be divided by: present, finite and above zero."""
    return pl.col(close).is_not_null() & pl.col(close).is_finite() & (pl.col(close) > 0)


def positioned(prices: pl.DataFrame, calendar: list[date], column: str = "close") -> pl.DataFrame:
    """ticker, date, `column` and `pos`, the index of the row's date on the calendar; refuses a date the calendar lacks."""
    places = pl.DataFrame({"date": calendar, "pos": range(len(calendar))}, schema={"date": pl.Date, "pos": pl.Int64})
    framed = prices.select("ticker", "date", column).join(places, on="date", how="left")
    off = framed.filter(pl.col("pos").is_null()).sort("ticker", "date")
    if off.height:
        raise OffCalendar(f"price row ({off['ticker'][0]}, {off['date'][0]}) is off the calendar")
    return framed
