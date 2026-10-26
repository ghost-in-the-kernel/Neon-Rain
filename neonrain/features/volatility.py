"""The volatility family (TODO 2.3, its second): the sample standard deviation of the daily log returns over the last k sessions.

Pure functions from the price frame (docs/HARNESS.md: `ticker`, `date`, the adjusted `close`, a total-return price) to
the harness's feature frame: `ticker`, `date`, then for each lookback k the feature `vol_k` and its stamp `vol_k_stamp`
(HAR-12). One row for each price row, in the order (ticker, date) ascending. The frame layout, the calendar check
(`OffCalendar`), the usable-close test and the strict gap rule are the returns family's, imported from it, not copied.

**Lookbacks** are counted in sessions of the calendar, as in the returns family: `vol_k` at *t* is taken over the k
daily returns of the sessions *t*-k+1 to *t*, which read the k+1 closes of *t*-k to *t*. They are 5, 21 and 63, the
horizons (neonrain.targets.HORIZONS) but the 3. Three returns leave two degrees of freedom: the estimate of a spread
from three numbers is mostly noise, and the 3-session return is already a feature of the returns family. A test holds
LOOKBACKS to the horizons less 3, so a change to the horizons is seen here.

**Estimator** (ESTIMATOR, DDOF). The daily return is the log return, ln(close_t / close_(t-1)) on the adjusted close: log
returns are symmetric in a gain and the loss that undoes it and add over sessions, and the adjusted close is a total
return, so a dividend is a return and not a jump. The spread is the sample standard deviation, divisor k-1 (DDOF = 1):
the mean of the k returns is estimated from the same returns, so the divisor k would understate the spread by a
factor that matters at k = 5 (sqrt(4/5), about 0.89) and not at 63. The mean is not taken as zero: over 5 to 63
sessions the mean return is not small beside the spread of a single stock, and a zero mean would make the feature
move with the return's level, which is the returns family's to carry.

**Not annualized** (ANNUALIZE). Annualizing multiplies every value by one constant, sqrt(252), which moves no rank and
no z-score taken within a day (TODO 2.4 normalizes each feature across the universe that day), and it would give the
three lookbacks one scale only if the daily returns were independent, which is a claim about the market this
module does not make. The feature is the daily scale, in units of a log return per session.

**Point in time.** `vol_k` at *t* reads the closes of *t* and of the k sessions before it; its stamp is *t*, the date
of the latest close used (HAR-12). No later row is read.

**Missing data is never filled.** A daily return needs a usable close on a session and on the session before it, and
the value at *t* needs all k daily returns, so all k+1 sessions from *t*-k to *t* need a usable close. A ticker's
first k sessions have none, and a missing row, an unusable close or a gap of any length inside the span nulls it:
the cell keeps its row, with a null value and a null stamp (HAR-12). A reused ticker is one ticker (NR-F-05); a window
across the reuse gap has no value, as in the returns family.
"""
from datetime import date

import polars as pl

from neonrain.features.returns import STAMP_SUFFIX, OffCalendar, positioned, usable

LOOKBACKS: tuple[int, ...] = (5, 21, 63)  # the horizons but the 3: three returns are two degrees of freedom
ESTIMATOR = "log"  # the daily return is ln(close_t / close_(t-1)) on the adjusted close
DDOF = 1  # the sample standard deviation: divisor k - 1
ANNUALIZE = False  # the daily scale: a constant factor moves no cross-sectional rank (2.4)

__all__ = ["ANNUALIZE", "DDOF", "ESTIMATOR", "LOOKBACKS", "OffCalendar", "STAMP_SUFFIX",
           "feature_columns", "name", "volatility"]


def name(lookback: int) -> str:
    """The feature's column name: vol_5, vol_21, vol_63."""
    return f"vol_{lookback}"


def feature_columns() -> list[str]:
    """The feature frame's columns after the keys, in order: each feature then its stamp."""
    return [column for k in LOOKBACKS for column in (name(k), name(k) + STAMP_SUFFIX)]


# Decision: NR-F-05 (no gap is crossed and no ticker is merged), HAR-12 (the stamp is the date of the latest close used)
def daily(rows: pl.DataFrame) -> pl.DataFrame:
    """The rows with `step`: the log return from the ticker's previous row, null unless that row is the previous session.

    `rows` are usable rows with `pos`, sorted by (ticker, pos).
    """
    previous = pl.col("pos").shift(1).over("ticker")
    step = pl.when(pl.col("pos") - previous == 1).then((pl.col("close") / pl.col("close").shift(1).over("ticker")).log())
    return rows.with_columns(step.alias("step"))


def of_lookback(rows: pl.DataFrame, lookback: int) -> pl.DataFrame:
    """ticker, date, then the feature and its stamp for one lookback, from `daily` rows.

    The spread of the last k steps of a ticker's rows; one null step among them (a gap, or the ticker's first row)
    gives null, since all k are required.
    """
    spread = pl.col("step").rolling_std(window_size=lookback, min_samples=lookback, ddof=DDOF).over("ticker")
    return rows.select(
        "ticker", "date",
        spread.alias(name(lookback)),
        pl.when(spread.is_not_null()).then(pl.col("date")).otherwise(None).alias(name(lookback) + STAMP_SUFFIX),
    )


def volatility(prices: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """The volatility family for every price row: ticker, date, then vol_k and vol_k_stamp for each k in LOOKBACKS.

    `prices` is the harness's price frame; `calendar` the trading dates, strictly ascending, which every price date
    must be on (OffCalendar otherwise). A row whose own close is unusable keeps its cell with null values.
    """
    framed = positioned(prices, calendar).sort("ticker", "pos")
    good = daily(framed.filter(usable()))
    frame = framed.select("ticker", "date")
    for lookback in LOOKBACKS:
        frame = frame.join(of_lookback(good, lookback), on=["ticker", "date"], how="left")
    return frame
