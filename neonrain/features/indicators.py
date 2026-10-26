"""The indicator family (TODO 2.3, its fourth and last): RSI, MACD and moving-average ratios, on the adjusted close.

Pure functions from the price frame (docs/HARNESS.md: `ticker`, `date`, the adjusted `close`, a total-return price) to
the harness's feature frame: `ticker`, `date`, then each feature and its stamp (HAR-12): `rsi_14`, `macd`, `macd_hist`,
`mar_5`, `mar_21`, `mar_63`. One row for each price row, in the order (ticker, date) ascending. The frame layout, the
calendar check (`OffCalendar`), the usable-close test and the strict gap rule are shared (`neonrain.features.common`).
All three indicators are in one file: they share one kind of window (a run of whole sessions ending at t) and one
helper for it, and the ablation (6.2) takes them as one family, "indicators". The indicators are kept because Ghost asked for them and because the ablation will say what they
are worth; the expectation is that the network learns most of them from the returns family, and a feature that
adds nothing is a finding there, not a reason to leave it out here.

**One kind of window.** Every value at *t* is a pure function of the closes of a fixed number of consecutive
sessions of the calendar ending at *t*, and of nothing else: no average reaches back over all of a ticker's history.
Wilder's RSI and the textbook MACD are exponential averages from the start of the series, so their value at *t*
depends on how long the series has run and on every gap in it, a thing the strict gap rule (NR-F-05, no window
crosses a missing session) cannot be applied to. Here a window is whole or the cell is null (null value, null stamp),
so a missing row, an unusable close, a gap of any length or a reused ticker's gap nulls the windows that cross it
and no others, and the first sessions of a ticker (its warm-up) have no value, exactly as in the other families.
A ticker is never merged, split or dropped. The same input always gives the same value, and the value at *t* does not
move when any close outside its window moves; both are tested. Nothing is filled.

**RSI** (RSI_PERIOD = 14). The textbook period, which Ghost asked for; it is not a horizon, and that is the point of
a standard indicator. The form is the finite-window one (Cutler's): over the last 14 daily changes of the close, G is
the sum of the gains and L the sum of the losses (as a positive number), and RSI = 100 G / (G + L), which is 100 minus
100 over 1 + G/L, the textbook value with simple averages (the 14 in both the average gain and the average loss
cancels). It reads the 15 closes *t*-14 to *t*, on 0 to 100 as in the textbook, 100 when nothing fell and 0 when
nothing rose. **A flat window** (G + L = 0, 15 equal closes: a price that did not move, as a halted or stale name's)
**gives null** (FLAT_RSI_IS_NULL): the ratio of 0 to 0 has no value, and 50, the neutral number, would be a reading
the window does not make; unmeasured is what it is, as a zero mean is in the volume family. The changes are of the
adjusted close, a total return, so a dividend is a change and not a break.

**MACD** (MACD_FAST = 12, MACD_SLOW = 26, MACD_SIGNAL = 9). The textbook settings. The line is EMA 12 less EMA 26 of
the close and the signal is EMA 9 of the line. An exponential average is taken over the last n closes only
(`ema_weights`): the weight of the close j sessions before *t* is proportional to (1-a)^j, a = 2/(n+1), and the n
weights are divided by their sum, so they add to 1. The textbook EMA puts the weight (1-a)^n on the sessions further
back than n (0.135 for n = 26); here that weight goes to the n sessions, and the shape within them is the textbook's.
The line then reads the 26 closes *t*-25 to *t*, the signal the 9 lines of *t*-8 to *t*, which read the 34 closes
*t*-33 to *t*: the textbook's own warm-up (it needs 26 closes for the slow average and 9 lines beyond the first),
and after it every value is local. The cost of the form against the textbook one is the weight the textbook gives
to the sessions beyond the window, and the benefit is the gap rule and a feature that does not depend on where a
sample begins (a frame built from a later start gives the same value at *t*), which a cache of the feature table (2.5)
that is rebuilt byte for byte wants.

**Which columns** (MACD_COLUMNS: the line and the histogram). `macd` is the line and `macd_hist` the line less the
signal. The signal alone is the line less the histogram, so a third column would hold nothing the two do not; the line
is the trend's distance and the histogram its recent change, two readings. Both are divided by the close at *t*
(SCALE_BY_CLOSE): a MACD is in price units, 0.5 of a 10-dollar stock is not 0.5 of a 500-dollar one, and the columns
could not be compared across tickers, which 2.4 does. Divided by the close the line is the distance between two
averages as a fraction of the price. The close at *t* is used and not the slow average, since it is already in the
window and adds no null of its own.

**Moving-average ratios** (MA_WINDOWS = 5, 21, 63). `mar_k` at *t* is the close at *t* over the mean of the closes of
the k sessions *t*-k+1 to *t* (t is inside its own mean, PRICE_IN_ITS_MEAN; the textbook simple moving average ends
at *t*). It is the other way round from the volume ratio, whose *t* stays out: a surge in volume is a rare, large
multiple and would be damped to at most k by its own divisor, while a price moves by a few percent, where *t* in
its mean damps the ratio by 1/k of a small number and the ratio keeps the question the indicator asks, "is the price
above its k-session average". A price on its mean reads 1, above reads over 1. The windows are the horizons but the 3
(a mean of three closes is the returns family's 3-session return again), as in the volatility and volume families,
and a test holds MA_WINDOWS to the horizons less 3. The ratio is plain, not logged and not less 1 (as the volume
ratio): 2.4 normalizes the shape.

**Point in time.** Each feature's stamp is *t*, the date of the latest close used (HAR-12: a day's close is known at
its own close). No later row is read.
"""
from datetime import date
from functools import reduce
from operator import add

import polars as pl

from neonrain.features.common import STAMP_SUFFIX, OffCalendar, positioned, usable

RSI_PERIOD = 14  # the textbook's, not a horizon
MACD_FAST = 12  # the textbook's
MACD_SLOW = 26  # the textbook's
MACD_SIGNAL = 9  # the textbook's
MA_WINDOWS: tuple[int, ...] = (5, 21, 63)  # the horizons but the 3: a mean of three closes is the 3-session return again
FLAT_RSI_IS_NULL = True  # no gains and no losses: 0 over 0 has no value, and 50 would be invented
SCALE_BY_CLOSE = True  # MACD columns divided by the close at t, to compare across tickers
PRICE_IN_ITS_MEAN = True  # the moving average ends at t, t inside it
MACD_COLUMNS: tuple[str, ...] = ("macd", "macd_hist")  # the line and the histogram; the signal is their difference
CLOSE = "close"  # the adjusted close, a total-return price

__all__ = ["CLOSE", "FLAT_RSI_IS_NULL", "MACD_COLUMNS", "MACD_FAST", "MACD_SIGNAL", "MACD_SLOW", "MA_WINDOWS",
           "OffCalendar", "PRICE_IN_ITS_MEAN", "RSI_PERIOD", "SCALE_BY_CLOSE", "STAMP_SUFFIX", "ema_weights",
           "feature_columns", "indicators", "ratio_name", "rsi_name"]


def rsi_name() -> str:
    """The RSI's column name: rsi_14."""
    return f"rsi_{RSI_PERIOD}"


def ratio_name(window: int) -> str:
    """A moving-average ratio's column name: mar_5, mar_21, mar_63."""
    return f"mar_{window}"


def feature_columns() -> list[str]:
    """The feature frame's columns after the keys, in order: each feature then its stamp (RSI, MACD, the ratios)."""
    names = [rsi_name(), *MACD_COLUMNS, *(ratio_name(w) for w in MA_WINDOWS)]
    return [column for feature in names for column in (feature, feature + STAMP_SUFFIX)]


def ema_weights(span: int) -> list[float]:
    """The weights of an exponential average of `span` sessions over the last `span` closes, newest first, adding to 1.

    The close j sessions before t has the weight proportional to (1-a)^j with a = 2 / (span+1), the textbook's; the
    weights past the span are cut and the rest divided by their sum. For span 2 they are 3/4 and 1/4, for span 3
    4/7, 2/7 and 1/7.
    """
    alpha = 2 / (span + 1)
    raw = [alpha * (1 - alpha) ** j for j in range(span)]
    return [w / sum(raw) for w in raw]


def weighted(column: pl.Expr, weights: list[float]) -> pl.Expr:
    """The sum of weights[j] times `column` j rows earlier; null when any of those rows is not there.

    Rows are sorted by (ticker, pos), so the row j earlier is j sessions earlier only inside a whole window: the
    caller masks every use with `whole`. (`sum_horizontal` would skip a null as zero, so the terms are added.)
    """
    return reduce(add, (w * column.shift(j) for j, w in enumerate(weights)))


def whole(count: int) -> pl.Expr:
    """Whether the `count` rows ending at this one are `count` consecutive sessions of one ticker.

    A `pos` difference of count-1 over count-1 rows of the same ticker: nothing missing between, and none from
    another ticker (the shift is taken within the ticker, so it is null when the ticker has too few rows).
    """
    return (pl.col("pos") - pl.col("pos").shift(count - 1).over("ticker")) == count - 1


# Decision: NR-F-05 (no gap is crossed and no ticker is merged), HAR-12 (the stamp is the date of the latest close used)
def of_rsi(rows: pl.DataFrame, period: int) -> pl.DataFrame:
    """ticker, date, then the RSI and its stamp, from usable rows with `pos`, sorted by (ticker, pos).

    G and L are the sums of the gains and of the losses over the last `period` daily changes (`period`+1 whole
    sessions); a window with no change at all gives null (FLAT_RSI_IS_NULL), not a division by zero.
    """
    change = pl.col(CLOSE).diff()
    gain = reduce(add, (change.clip(lower_bound=0).shift(j) for j in range(period)))
    loss = reduce(add, ((-change).clip(lower_bound=0).shift(j) for j in range(period)))
    measured = whole(period + 1) & ((gain + loss) > 0)
    return rows.select(
        "ticker", "date",
        pl.when(measured).then(100 * gain / (gain + loss)).otherwise(None).alias(rsi_name()),
        pl.when(measured).then(pl.col("date")).otherwise(None).alias(rsi_name() + STAMP_SUFFIX),
    )


# Decision: NR-F-05 (no gap is crossed and no ticker is merged), HAR-12 (the stamp is the date of the latest close used)
def of_macd(rows: pl.DataFrame, fast: int, slow: int, signal: int) -> pl.DataFrame:
    """ticker, date, then `macd` and `macd_hist`, each with its stamp, from usable rows with `pos`, sorted by (ticker, pos).

    The line (EMA `fast` less EMA `slow` of the close, each over its own span) reads `slow` whole sessions; the
    signal (EMA `signal` of the line) and so the histogram read `slow`+`signal`-1. Both are divided by the close.
    `fast` is not above `slow`, so the fast window lies inside the slow one.
    """
    line = weighted(pl.col(CLOSE), ema_weights(fast)) - weighted(pl.col(CLOSE), ema_weights(slow))
    lined = rows.with_columns(line.alias("line"))
    hist = pl.col("line") - weighted(pl.col("line"), ema_weights(signal))
    line_ok = whole(slow)
    hist_ok = whole(slow + signal - 1)
    return lined.select(
        "ticker", "date",
        pl.when(line_ok).then(pl.col("line") / pl.col(CLOSE)).otherwise(None).alias(MACD_COLUMNS[0]),
        pl.when(line_ok).then(pl.col("date")).otherwise(None).alias(MACD_COLUMNS[0] + STAMP_SUFFIX),
        pl.when(hist_ok).then(hist / pl.col(CLOSE)).otherwise(None).alias(MACD_COLUMNS[1]),
        pl.when(hist_ok).then(pl.col("date")).otherwise(None).alias(MACD_COLUMNS[1] + STAMP_SUFFIX),
    )


# Decision: NR-F-05 (no gap is crossed and no ticker is merged), HAR-12 (the stamp is the date of the latest close used)
def of_ratio(rows: pl.DataFrame, window: int) -> pl.DataFrame:
    """ticker, date, then the moving-average ratio and its stamp for one window, from usable rows with `pos`.

    The close at t over the mean of the `window` closes ending at t (t inside its own mean).
    """
    mean = pl.col(CLOSE).rolling_mean(window_size=window, min_samples=window).over("ticker")
    return rows.select(
        "ticker", "date",
        pl.when(whole(window)).then(pl.col(CLOSE) / mean).otherwise(None).alias(ratio_name(window)),
        pl.when(whole(window)).then(pl.col("date")).otherwise(None).alias(ratio_name(window) + STAMP_SUFFIX),
    )


def indicators(prices: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """The indicator family for every price row: ticker, date, then each feature and its stamp (`feature_columns`).

    `prices` is the harness's price frame with the adjusted `close`; `calendar` the trading dates, strictly
    ascending, which every price date must be on (OffCalendar otherwise). A row whose own close is unusable keeps
    its cell with null values.
    """
    framed = positioned(prices, calendar, CLOSE).sort("ticker", "pos")
    good = framed.filter(usable(CLOSE))
    frame = framed.select("ticker", "date")
    parts = [of_rsi(good, RSI_PERIOD), of_macd(good, MACD_FAST, MACD_SLOW, MACD_SIGNAL),
             *(of_ratio(good, window) for window in MA_WINDOWS)]
    for part in parts:
        frame = frame.join(part, on=["ticker", "date"], how="left")
    return frame
