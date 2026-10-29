"""The 12-1 momentum baseline (R-007 b, TODO 3.1 b): a ticker's score is the rank of its 12-1 momentum that day.

**12-1 momentum** (docs/GLOSSARY.md) at a universe cell (ticker, *t*) is the adjusted close at the session `SKIP`
(21) before *t* over the adjusted close at the session `LOOKBACK` (252) before *t*, minus 1: a total return over the
231 sessions from *t*-252 to *t*-21, the most recent 21 sessions left out. Sessions are those of the calendar, never
calendar days. Like the returns family (TODO 2.3) it never fills: the value needs a usable close (present, finite,
above zero) on every one of the 232 sessions from *t*-252 to *t*-21, so a window that crosses a gap (a session with no
row or no usable close) has none, and neither has a ticker's first 252 sessions. The skipped sessions *t*-20 to *t*
are not read at all, so a gap there takes nothing away. A ticker is never merged, split or dropped (NR-F-05).

`LOOKBACK` and `SKIP` are the definition of the name "momentum" (the published 12-1), never knobs: a different
window is a different baseline name, or a run with hyperparameters in its config hash (HAR-01). One configuration,
run once, is a trial, not a search (HAR-09).

**The score** is what the harness reads (HAR-07: a score above 0.5 predicts an excess return above 0): the momentum's
rank fraction among the universe cells that have a value that day, `(rank - 1) / (n - 1)` with ties at their average
rank, so the median ticker scores 0.5, the lowest 0 and the highest 1, and a higher score is a predicted higher
excess return. A day with one such cell scores it 0.5. A cell with no value has no score row (a score frame holds
no null, `runner.scored_market`), and no row means no label is scored there.

**The stamp** (HAR-12) is the date of the latest close used: the session *t*-21, never after *t*.

`baselines` may not import `features` (docs/modules.json), so the window is counted here, by the rule of
`neonrain.features.returns`. The prices are the verified frame's adjusted `close`; the caller passes the whole frame,
not one cut at the universe's first date, since the window reaches 252 sessions back. Pure (HAR-11).
"""
from datetime import date

import polars as pl

NAME = "momentum"
LOOKBACK = 252  # sessions back to the start of the window
SKIP = 21  # the most recent sessions left out
SPAN = LOOKBACK - SKIP  # sessions between the window's two closes


def window_returns(prices: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """ticker, pos (the closing session's place on the calendar), date, value: the total return over `SPAN` sessions
    ending at that session, for each usable close whose window has every session present; refuses a date off the
    calendar."""
    places = pl.DataFrame({"date": calendar, "pos": range(len(calendar))}, schema={"date": pl.Date, "pos": pl.Int64})
    rows = prices.select("ticker", "date", "close").join(places, on="date", how="left")
    off = rows.filter(pl.col("pos").is_null())
    if off.height:
        raise ValueError(f"price row ({off['ticker'][0]}, {off['date'][0]}) is off the calendar")
    good = rows.filter(pl.col("close").is_not_null() & pl.col("close").is_finite() & (pl.col("close") > 0))
    good = good.sort("ticker", "pos")
    whole = (pl.col("pos") - pl.col("pos").shift(SPAN).over("ticker")) == SPAN
    value = pl.when(whole).then(pl.col("close") / pl.col("close").shift(SPAN).over("ticker") - 1.0).otherwise(None)
    return good.select("ticker", "pos", "date", value.alias("value")).filter(pl.col("value").is_not_null())


# Decision: HAR-07 (a score above 0.5 predicts an up label, so the day's rank fraction puts the median at 0.5)
def scores(prices: pl.DataFrame, universe: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """The score frame of the 12-1 momentum baseline: columns ticker, date, score (Float64), stamp (Date), one row for
    each universe cell that has a momentum, in the universe's own row order."""
    places = pl.DataFrame({"date": calendar, "pos": range(len(calendar))}, schema={"date": pl.Date, "pos": pl.Int64})
    cells = universe.join(places, on="date", maintain_order="left").with_columns(before=pl.col("pos") - SKIP)
    known = window_returns(prices, calendar).rename({"pos": "before", "date": "stamp"})
    held = cells.join(known, on=["ticker", "before"], maintain_order="left")
    rank = pl.col("value").rank("average").over("date") - 1.0
    width = pl.len().over("date") - 1.0
    score = pl.when(width == 0).then(0.5).otherwise(rank / width)
    return held.select("ticker", "date", score.alias("score"), "stamp")
