"""The volume ratio family (TODO 2.3, its third): the volume at t over the mean volume of the k sessions before t.

Pure functions from the price frame (docs/HARNESS.md: `ticker`, `date`, and the split-adjusted `volume` that
`neonrain.universe.prices` gives) to the harness's feature frame: `ticker`, `date`, then for each lookback k the
feature `volr_k` and its stamp `volr_k_stamp` (HAR-12). One row for each price row, in the order (ticker, date)
ascending. The frame layout, the calendar check (`OffCalendar`) and the strict gap rule are shared
(`neonrain.features.common`), as in the other families.

**Which volume** (VOLUME). The split-adjusted `volume`, never `raw_volume`. A split of ratio r multiplies the shares
traded by r from its day on with nothing else changed: in the raw count a 2-for-1 split makes the day after it look
like a volume of twice the mean of the sessions before, a surge that never happened, and it does so in every ratio
whose window crosses the split. WIKI's adjusted volume is restated on the latest share basis, so the sessions on
both sides of a split are counted in the same shares and the ratio stays a ratio of like quantities. (A split WIKI
did not record, NR-F-07's decayed end, is in neither column; nothing here can repair it.) The adjustment's cost is that a feature built from
the frame today is not the one built after a later split restates the history; that is the frame's property, not this
module's, and the same holds for the close.

**The ratio** (PRIOR_INCLUDES_T). `volr_k` at *t* is volume_t divided by the mean of the volumes of the k sessions
*t*-k to *t*-1. *t* is not inside its own prior mean: a surge at *t* inside its own prior mean would raise the divisor
by 1/k of the surge, so the ratio would top out at k whatever the surge (the whole window's volume on one day gives k) and would be flatter exactly where the feature is meant to be loud. With *t* outside, a day of
usual volume reads 1, twice the usual reads 2, no trading reads 0, and the scale does not depend on k. It is a mean
and not a median (MEAN): the mean is the volume the market actually put through in k sessions, it is not zeroed by the
many no-trade days of a thin name, and a surge inside the window is information (it lowers
today's ratio for k sessions after the surge, which is what "high against the recent past" means). A median would
call a ticker that trades every second day a ticker of zero usual volume.

**Lookbacks** are counted in sessions of the calendar and are 5, 21 and 63: the horizons (neonrain.targets.HORIZONS)
but the 3, as in the volatility family. A mean of three sessions of volume is mostly the noise of three days, and the
volume at *t* over it would be dominated by its own divisor's noise. A test holds LOOKBACKS to the horizons less 3.
The ratio looks back k sessions before *t*, so it reads k+1 sessions of volume, *t*-k to *t*.

**Zero and missing volume.** A usable volume is present, finite and not negative; zero is usable, because a day
without a trade is a day (the last row of a ticker that leaves has zero volume 2.6% of the time, NR-F-06, and a thin
name has zero days). Zero volume at *t* gives the ratio 0.0, a value: nothing traded against a usual amount. A zero
mean over the k sessions before *t* gives null (ZERO_PRIOR_IS_NULL): the ratio's unit, the usual amount, does not
exist, and infinity (volume_t over 0) or a ratio of 0/0 would be a number no later step can use; a ticker with no
volume for k sessions followed by a first trade is not "infinitely loud" but unmeasured. A null, nan, infinite or
negative volume anywhere in the k+1 sessions, a missing row, or a gap of any length inside the span, gives null; the
cell keeps its row, with a null value and a null stamp (HAR-12). A ticker is never merged, split or dropped (NR-F-05):
a reused ticker is one ticker and a window across the reuse gap has no value. Nothing is filled.

**No logarithm** (LOG). The ratio is not logged. It is skewed (zero to some tens), but a logarithm would turn the
exact zeros of a no-trade day into minus infinity or ask for a floor, an invented constant, and it would be a
second decision about what the data holds. TODO 2.4 normalizes every feature within the universe each day, by rank
or z-score, and that is where the shape of a distribution is dealt with, for all families the same way (a rank needs no
log; a z-score may take one then). The feature stays the plain ratio, where 1 is the usual volume and the value reads
at sight.

**Point in time.** `volr_k` at *t* reads the volumes of *t* and of the k sessions before it; its stamp is *t*, the date
of the latest volume used (HAR-12: a day's volume is known at its own close). No later row is read.
"""
from datetime import date

import polars as pl

from neonrain.features.common import STAMP_SUFFIX, OffCalendar, positioned

LOOKBACKS: tuple[int, ...] = (5, 21, 63)  # the horizons but the 3: a mean of three days is mostly noise
VOLUME = "volume"  # the split-adjusted column, not raw_volume: a split must not look like a surge
PRIOR_INCLUDES_T = False  # the prior mean is the k sessions before t; t is outside it
MEAN = True  # the prior mean, not the median
ZERO_PRIOR_IS_NULL = True  # a zero prior mean gives null, never infinity
LOG = False  # the plain ratio; 2.4 normalizes

__all__ = ["PRIOR_INCLUDES_T", "LOG", "LOOKBACKS", "MEAN", "STAMP_SUFFIX", "VOLUME", "ZERO_PRIOR_IS_NULL",
           "OffCalendar", "feature_columns", "name", "volume_ratios"]


def name(lookback: int) -> str:
    """The feature's column name: volr_5, volr_21, volr_63."""
    return f"volr_{lookback}"


def feature_columns() -> list[str]:
    """The feature frame's columns after the keys, in order: each feature then its stamp."""
    return [column for k in LOOKBACKS for column in (name(k), name(k) + STAMP_SUFFIX)]


def usable() -> pl.Expr:
    """Whether a volume can be counted: present, finite and not negative. Zero is a day without a trade."""
    return pl.col(VOLUME).is_not_null() & pl.col(VOLUME).is_finite() & (pl.col(VOLUME) >= 0)


# Decision: NR-F-05 (no gap is crossed and no ticker is merged), HAR-12 (the stamp is the date of the latest volume used)
def of_lookback(rows: pl.DataFrame, lookback: int) -> pl.DataFrame:
    """ticker, date, then the feature and its stamp for one lookback, from usable rows with `pos`, sorted by (ticker, pos).

    The row k rows earlier of the same ticker is exactly k sessions earlier only when no session between has gone
    missing, so a `pos` difference of k is a window with every session present; any other row has no value, and
    neither has one whose prior mean is zero.
    """
    prior = pl.col(VOLUME).shift(1).rolling_mean(window_size=lookback, min_samples=lookback).over("ticker")
    whole = (pl.col("pos") - pl.col("pos").shift(lookback).over("ticker")) == lookback
    measured = whole & (prior > 0)
    return rows.select(
        "ticker", "date",
        pl.when(measured).then(pl.col(VOLUME) / prior).otherwise(None).alias(name(lookback)),
        pl.when(measured).then(pl.col("date")).otherwise(None).alias(name(lookback) + STAMP_SUFFIX),
    )


def volume_ratios(prices: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """The volume ratio family for every price row: ticker, date, then volr_k and volr_k_stamp for each k in LOOKBACKS.

    `prices` is the harness's price frame with the adjusted `volume`; `calendar` the trading dates, strictly
    ascending, which every price date must be on (OffCalendar otherwise). A row whose own volume is unusable keeps
    its cell with null values.
    """
    framed = positioned(prices, calendar, VOLUME).sort("ticker", "pos")
    good = framed.filter(usable())
    frame = framed.select("ticker", "date")
    for lookback in LOOKBACKS:
        frame = frame.join(of_lookback(good, lookback), on=["ticker", "date"], how="left")
    return frame
