"""Who is in the universe, from a price frame (TODO 2.1 b): each ticker's span, and the 1,000 largest names per date.

Pure functions of a polars price frame (the harness's layout, docs/HARNESS.md: `ticker` String, `date` Date, plus the
raw `close` and `volume` for the dollar volume); no I/O, no clock. Delisted names stay in: a ticker is in the
universe on every date it ranks, and its last row is its last date.

**Known at t** (HAR-12): the close of t is known at t, so the universe on date t is ranked on closes and volumes
of the 63 sessions ending at t, t included. That is the rule a price feature stamped t already lives by, so the
universe frame and the feature frame agree on what a date's information is. Nothing after t is read: the rolling
window looks back only, and `test_membership.py` changes every row after t and shows the universe at t unmoved.
"""
from datetime import date

import polars as pl

# Decision: TODO 2.1 (b): the universe is the 1,000 names with the largest trailing median dollar volume.
UNIVERSE_SIZE = 1000
# Decision: TODO 2.1 (b): the trailing window is 63 sessions of the calendar (about three months), the 3-month horizon.
WINDOW_SESSIONS = 63
# Unsure: the plan says "trailing 63-session median" and not how many of the 63 a name must have traded; asked here
# for all of them, so a name enters 63 sessions after its first row and a gap inside the window keeps it out.
MIN_OBSERVED = WINDOW_SESSIONS


def spans(prices: pl.DataFrame) -> pl.DataFrame:
    """Each ticker's first and last date in the frame: columns `ticker`, `first`, `last`, ascending by ticker."""
    return prices.group_by("ticker").agg(first=pl.col("date").min(), last=pl.col("date").max()).sort("ticker")


def median_dollar_volume(prices: pl.DataFrame, sessions: list[date]) -> pl.DataFrame:
    """Columns `ticker`, `date`, `median_dv`: raw close times volume, median over the 63 sessions ending at `date`.

    One row per price row that is on `sessions`, has a dollar volume, and has MIN_OBSERVED of them in its window;
    a row on a date that is no session is not counted. The window is counted in sessions of the calendar, not in rows.
    """
    seen = set(prices["date"].unique().to_list())
    traded = [day for day in sessions if day in seen]
    calendar = pl.DataFrame({"date": traded, "session": range(len(traded))}, schema={"date": pl.Date, "session": pl.Int64})
    rows = prices.join(calendar, on="date").with_columns(dv=pl.col("close") * pl.col("volume")).drop_nulls("dv")
    window = f"{WINDOW_SESSIONS}i"
    rolled = rows.sort("ticker", "session").with_columns(
        median_dv=pl.col("dv").rolling_median_by("session", window_size=window, min_samples=MIN_OBSERVED).over("ticker")
    )
    return rolled.drop_nulls("median_dv").select("ticker", "date", "median_dv")


def universe(prices: pl.DataFrame, sessions: list[date]) -> pl.DataFrame:
    """The harness's universe frame: columns `ticker`, `date`, one row per eligible name per date.

    Takes raw prices only (J-079): callers build a universe with `prices.universe`, which hands this `for_membership(prices)`.

    On each date, the UNIVERSE_SIZE names with the largest median dollar volume (ties to the earlier ticker), among
    names with a price row that day; fewer when fewer qualify. The first 62 sessions of the frame's names have no
    full window, so the frame starts 63 sessions after the first price row.
    """
    ranked = median_dollar_volume(prices, sessions).sort(["date", "median_dv", "ticker"], descending=[False, True, False])
    return ranked.group_by("date", maintain_order=True).head(UNIVERSE_SIZE).select("ticker", "date").sort("date", "ticker")
