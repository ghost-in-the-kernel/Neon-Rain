"""The feature table (TODO 2.5): the four price families, each normalized within the universe, joined in one frame.

A pure function of the price frame, the calendar's sessions and the universe frame (docs/HARNESS.md). It computes the
four families (`returns`, `volatility`, `volume`, `indicators`), runs each through `normalize.normalize` (2.4) and puts
them side by side. The result is exactly the universe's cells, one row each (2.4's answer to whose cells a feature
frame has), sorted by (ticker, date), so its keys are the universe's keys and the harness's `check_stamps` and
`check_market` accept it as `Market.features`.

**The column order is fixed** (COLUMNS, held by a test against a literal list): `ticker`, `date`, then the families in
the order returns, volatility, volume ratios, indicators, each family's features in its own `feature_columns` order,
every feature followed by its `_stamp`. Types: `ticker` String, `date` Date, each feature Float64, each stamp Date.

**Point in time.** Each family's value at t reads prices up to t, and the rank reads the cross-section at t; each
column keeps the stamp `normalize` gives it (HAR-12). A later price moves no earlier row; a test changes them all.
Nothing is fitted over dates. No clock, no I/O.
"""
from datetime import date

import polars as pl

from neonrain.features import indicators, normalize, returns, volatility, volume

KEYS = normalize.KEYS
# Decision: TODO 2.5: the families join in this order, and the table's columns are the keys then each family's
# `feature_columns` (a feature, then its stamp), so the layout is one list and never depends on a join's whim.
FAMILIES = (
    (returns.returns, returns.feature_columns),
    (volatility.volatility, volatility.feature_columns),
    (volume.volume_ratios, volume.feature_columns),
    (indicators.indicators, indicators.feature_columns),
)


def columns() -> list[str]:
    """The table's columns in order: ticker, date, then each family's feature and stamp columns."""
    return [*KEYS, *(column for _, names in FAMILIES for column in names())]


def feature_table(prices: pl.DataFrame, sessions: list[date], members: pl.DataFrame) -> pl.DataFrame:
    """One row for each universe cell, sorted by (ticker, date), with `columns()` as its columns.

    `prices` is the harness's price frame with the adjusted columns (`prices.load`); `sessions` the calendar the
    families count on (a price date off it raises `OffCalendar`); `members` the universe frame. A feature is null
    where its family has no value, or fewer than `normalize.MIN_NAMES` names have one that day.
    """
    cells = members.select(KEYS).sort(KEYS)
    # Each normalized frame has exactly the universe's cells sorted by (ticker, date), so the frames sit side by side.
    ranked = [normalize.normalize(family(prices, sessions), members).drop(KEYS) for family, _ in FAMILIES]
    return pl.concat([cells, *ranked], how="horizontal").select(columns())
