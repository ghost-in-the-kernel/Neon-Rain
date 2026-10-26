"""Cross-sectional normalization (TODO 2.4): each feature of a day becomes its rank among the universe names that day.

A pure function of a family's feature frame (`ticker`, `date`, then each feature and its `_stamp`, HAR-12) and the
universe frame (`ticker`, `date`, docs/HARNESS.md). It returns the same layout, so the harness's `check_stamps` and
`check_market` accept it and the four families go through it alike. R-009 makes this part of the network's input; the
purpose is that no feature carries the market level: on a bull day every `ret_21` is high, and after the rank the day's
level is gone and only the order of the names is left.

**The two contract questions J-056 left to 2.4, decided here** (docs/HARNESS.md is frozen, so the answers live here and
in docs/GLOSSARY.md):

1. *Whose cells does a feature frame have?* A family's frame has the **price frame's cells** (one for each price row:
   a family knows nothing of the universe). The normalized frame has the **universe's cells**: exactly one row for each
   (ticker, date) of the universe frame, sorted by (ticker, date). The harness trades and scores the universe's cells
   (HAR-02), and the universe is the cross-section: a cell of the normalized frame is a cell that is ranked against
   others.
2. *What does a cell outside the universe on a date get?* **No row.** A price row of a name that is not in the universe
   that day is left out of the output, and its value takes no part in any rank (it neither moves another name's rank
   nor counts in the date's `n`). A name is ranked against the other universe names of that same date and no others. The
   reverse case, a universe cell with no row in the feature frame, keeps its row with null values and null stamps.

**Rank, not a z-score, for every feature** (the named constants below). The families produce what a z-score handles
badly: volume ratios with exact zeros (`volr_k` is 0 on a zero-volume day) and long right tails (a volume ratio
of 40, a 63-session return of +900% on a small name), counts and ratios on different scales. A z-score keeps distances
but one outlier sets the divisor for the whole day, and it needs a winsorizing level (1%? 5%?) that is a threshold
nobody has a reason for yet. A rank has no parameter, is exactly invariant under any increasing transform of the
feature (the day's level and scale included), and bounds every value. What a rank discards is the size of a gap between
neighbours; if the ablation shows the network wants it, a winsorized z-score is a second function beside this one, a
decision for then (the rank and a z-score of the same feature would need two columns, and the layout has one).

**Scale.** CENTRE is the constant: the value is `(rank - 1) / (n - 1) - 0.5`, in [-0.5, +0.5], `n` the number of names
with a value that day. The scale of HAR-02's rank label is [0, 1] with the same formula less the centring; centred, the
cross-section's mean is exactly 0 each day (ties take the average rank, so the mean of the average ranks is (n+1)/2),
which is the "no market level" the plan asks for, stated as a property a test can check, and a network's first layer
sees inputs around 0. **Ties take the average rank** (HAR-02's rule too): tied names get the same value, so an
exact-zero volume ratio shared by many names is one value in the middle of the ties' ranks, never an order made up from
ticker names.

**Nulls** stay null and are left out of the day's cross-section: a name with no value of a feature that day neither
takes a rank nor shifts the others' (its `n` is not counted). A value that is not finite (nan or infinity; no family
makes one, the probes counted none) is treated as null, so one cannot become the top rank. Each feature is ranked on
its own set of names, so `n` differs between features on the same day.

**The fewest names.** MIN_NAMES is 20, HAR-02's `min_tickers` (neonrain.targets.MIN_TICKERS, held equal by a test;
features may not import the targets). A date with fewer than MIN_NAMES valued names for a feature gives that feature
null for every name: a rank among five names is a coin, and a rank among one divides by zero. The universe has about
1,000 names, so the guard only bites at a sample's edges (a feature's warm-up) and in tests.

**Point in time.** A normalized value at *t* reads the cross-section at *t* only: the families' values of that date, all
stamped *t* or earlier. Its stamp is the latest stamp among the valued cells of the cross-section it was ranked in
(HAR-12: the maximum timestamp of any input row used), which for the price families is *t*. It is null where the value
is null. A test changes every other date's rows, and every later price, and shows the values at *t* unmoved. Nothing
is fitted over dates, so there is no normalization statistic for HAR-04 to restrict to a training span.
"""
import polars as pl

from neonrain.features.common import STAMP_SUFFIX

KEYS = ("ticker", "date")
# Decision: TODO 2.4 / HAR-02: the fewest valued names a date needs for a feature to have a value; 20, as `min_tickers`.
MIN_NAMES = 20
# Decision: TODO 2.4: the rank runs from -0.5 to +0.5 so each day's cross-section has the mean 0 exactly.
CENTRE = 0.5


class NotAFeatureFrame(ValueError):
    """A frame that lacks `ticker`/`date`, has a feature without its stamp (or a stamp without its feature), or repeats a cell."""


def feature_names(frame: pl.DataFrame) -> list[str]:
    """The feature columns after the keys, in the frame's order; refuses a missing key, a missing or orphan stamp, a repeated cell."""
    for key in KEYS:
        if key not in frame.columns:
            raise NotAFeatureFrame(f"frame has no {key} column")
    if frame.select(KEYS).is_duplicated().any():
        raise NotAFeatureFrame("frame has more than one row for some (ticker, date)")
    others = [column for column in frame.columns if column not in KEYS]
    names = [column for column in others if not column.endswith(STAMP_SUFFIX)]
    for name in names:
        if name + STAMP_SUFFIX not in others:
            raise NotAFeatureFrame(f"feature {name!r} has no {name + STAMP_SUFFIX} column")
    for stamp in (column for column in others if column.endswith(STAMP_SUFFIX)):
        if stamp.removesuffix(STAMP_SUFFIX) not in names:
            raise NotAFeatureFrame(f"stamp column {stamp!r} has no feature")
    return names


# Decision: TODO 2.4: rank within the day's universe, centred, ties averaged, null below MIN_NAMES valued names.
def of_feature(name: str) -> list[pl.Expr]:
    """The expressions for one feature's normalized value and stamp, over rows already joined to the universe's cells."""
    stamp = name + STAMP_SUFFIX
    value = pl.when(pl.col(name).is_finite()).then(pl.col(name).cast(pl.Float64)).otherwise(None)
    names = value.is_not_null().sum().over("date")
    rank = value.rank("average").over("date")
    ranked = pl.when(names >= MIN_NAMES).then((rank - 1.0) / (names - 1.0) - CENTRE).otherwise(None)
    used = pl.when(ranked.is_not_null()).then(pl.col(stamp)).otherwise(None)
    latest = pl.when(ranked.is_not_null()).then(used.max().over("date")).otherwise(None)
    return [ranked.alias(name), latest.alias(stamp)]


def normalize(features: pl.DataFrame, universe: pl.DataFrame) -> pl.DataFrame:
    """The cross-sectional rank of every feature: one row for each universe cell, sorted by (ticker, date).

    Columns as the family's: `ticker`, `date`, then each feature (Float64, in [-0.5, 0.5]) and its stamp (the family's
    stamp type). A feature's value on a date is null when fewer than MIN_NAMES universe names have a value of it that day.
    Raises NotAFeatureFrame for a malformed feature frame or a universe frame with a repeated cell.
    """
    names = feature_names(features)
    cells = universe.select(KEYS)
    if cells.is_duplicated().any():
        raise NotAFeatureFrame("universe has more than one row for some (ticker, date)")
    joined = cells.join(features, on=list(KEYS), how="left")
    expressions = [expression for name in names for expression in of_feature(name)]
    return joined.select(*KEYS, *expressions).sort(*KEYS)
