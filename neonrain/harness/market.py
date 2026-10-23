"""What the harness is given (docs/HARNESS.md): the Market type, the layouts of its frames, and HAR-12's stamp check.

The real-data loader of phase 2 and the synthetic market (HAR-10) both build a Market from here, so neither imports
the other. `check_market` refuses a frame that does not have the documented layout; `check_stamps` refuses a feature
whose provenance stamp says it used data from after its cell's date, naming the feature and the cell (HAR-12).
Pure functions of their arguments: no clock, no network (HAR-11).
"""
from datetime import date, time, timedelta
from typing import NamedTuple

import polars as pl

STAMP_SUFFIX = "_stamp"
KEYS: dict[str, pl.DataType | type[pl.DataType]] = {"ticker": pl.String, "date": pl.Date}
PRICE_COLUMNS: dict[str, pl.DataType | type[pl.DataType]] = {**KEYS, "close": pl.Float64}


class Market(NamedTuple):
    """What the harness is given (docs/HARNESS.md): prices, the universe, features, the calendar."""

    prices: pl.DataFrame  # ticker, date, close (adjusted), and whatever else the features need
    universe: pl.DataFrame  # ticker, date: eligible that day
    features: pl.DataFrame  # ticker, date, then each feature and its stamp (HAR-12): edge, edge_stamp
    calendar: list[date]  # the trading dates, strictly ascending


class LayoutRefused(ValueError):
    """A frame or calendar that does not have the layout docs/HARNESS.md gives."""


class StampRefused(ValueError):
    """A feature whose stamp says it used data from after its cell's date (HAR-12); the message names both."""


def check_keys(name: str, frame: pl.DataFrame) -> None:
    """Refuse a frame without ticker (String) and date (Date) columns, with a null key, or with a key twice."""
    for column, dtype in KEYS.items():
        if column not in frame.columns:
            raise LayoutRefused(f"{name} frame has no {column} column")
        if frame.schema[column] != dtype:
            raise LayoutRefused(f"{name} frame's {column} column is {frame.schema[column]}, expected {dtype}")
    if frame["ticker"].null_count() or frame["date"].null_count():
        raise LayoutRefused(f"{name} frame has a null ticker or date")
    repeated = frame.select(list(KEYS)).filter(frame.select(list(KEYS)).is_duplicated()).unique().sort(list(KEYS))
    if repeated.height:
        ticker, day = repeated.row(0)
        raise LayoutRefused(f"{name} frame has more than one row for ({ticker}, {day})")


def check_calendar(calendar: list[date]) -> None:
    """Refuse an empty calendar, or one whose dates are not strictly ascending."""
    if not calendar:
        raise LayoutRefused("calendar is empty")
    for before, after in zip(calendar, calendar[1:]):
        if after <= before:
            raise LayoutRefused(f"calendar is not strictly ascending: {after} follows {before}")


def check_on_calendar(name: str, frame: pl.DataFrame, calendar: list[date]) -> None:
    """Refuse a frame holding a date the calendar lacks (all horizons count on the calendar, HAR-02)."""
    off = frame.filter(~pl.col("date").is_in(pl.Series(calendar).implode())).sort("ticker", "date")
    if off.height:
        raise LayoutRefused(f"{name} frame has a row ({off['ticker'][0]}, {off['date'][0]}) off the calendar")


def check_prices(prices: pl.DataFrame) -> None:
    """Keys, then a Float64 close; other columns are allowed."""
    check_keys("price", prices)
    if "close" not in prices.columns:
        raise LayoutRefused("price frame has no close column")
    if prices.schema["close"] != pl.Float64:
        raise LayoutRefused(f"price frame's close column is {prices.schema['close']}, expected {pl.Float64}")


def check_universe(universe: pl.DataFrame) -> None:
    """Keys and nothing else."""
    check_keys("universe", universe)
    if universe.columns != list(KEYS):
        raise LayoutRefused(f"universe frame has columns {universe.columns}, expected {list(KEYS)}")


def stamp_columns(features: pl.DataFrame) -> dict[str, str]:
    """Each feature's name to its stamp column's name; refuses a feature without a stamp, or a stamp without a feature.

    For columns ticker, date, edge, edge_stamp: {"edge": "edge_stamp"}.
    """
    check_keys("feature", features)
    others = [c for c in features.columns if c not in KEYS]
    stamps = {c for c in others if c.endswith(STAMP_SUFFIX)}
    names = [c for c in others if c not in stamps]
    for name in names:
        if not features.schema[name].is_numeric():
            raise LayoutRefused(f"feature {name!r} is {features.schema[name]}, expected a number")
        if name + STAMP_SUFFIX not in stamps:
            raise LayoutRefused(f"feature {name!r} has no {name + STAMP_SUFFIX} column")
    orphans = sorted(stamps - {name + STAMP_SUFFIX for name in names})
    if orphans:
        raise LayoutRefused(f"stamp column {orphans[0]!r} has no feature {orphans[0][: -len(STAMP_SUFFIX)]!r}")
    return {name: name + STAMP_SUFFIX for name in sorted(names)}


def cut_offset(cutoff: time | None) -> timedelta:
    """The cut's distance after 00:00 on the cell's date: time(16, 30) is 16 h 30 min; refuses none or a zone."""
    if cutoff is None:
        raise LayoutRefused("a news feature (a Datetime stamp) needs the run's news cutoff time, and none was given")
    if cutoff.tzinfo is not None:
        raise LayoutRefused("the news cutoff time must have no time zone: stamps and cuts are UTC")
    return timedelta(hours=cutoff.hour, minutes=cutoff.minute, seconds=cutoff.second, microseconds=cutoff.microsecond)


def too_late(name: str, stamp: str, features: pl.DataFrame, cutoff: time | None) -> pl.DataFrame:
    """The rows of the feature whose stamp breaks HAR-12, sorted by (ticker, date), with a `reason` column.

    A Date stamp is a trading date, refused when after the cell's date; a Datetime stamp is a publish time, refused
    at or after the cell's date at `cutoff`; a stamp that is null where the feature has a value is refused.
    """
    dtype = features.schema[stamp]
    nothing = pl.col(stamp).is_null() & pl.col(name).is_not_null()
    if dtype == pl.Date:
        late, why = pl.col(stamp) > pl.col("date"), "stamp {} is after the cell's date"
    elif isinstance(dtype, pl.Datetime) and dtype.time_zone is None:
        cut = pl.col("date").cast(dtype) + cut_offset(cutoff)
        late, why = pl.col(stamp) >= cut, "stamp {} is at or after the news cut"
    else:
        raise LayoutRefused(f"stamp column {stamp!r} is {dtype}, expected Date or Datetime without a time zone")
    bad = features.filter(late | nothing).sort("ticker", "date")
    text = pl.when(pl.col(stamp).is_null()).then(pl.lit("value has no stamp"))
    return bad.with_columns(text.otherwise(pl.format(why, pl.col(stamp))).alias("reason"))


# Decision: HAR-12 (the stamp is the primary leak defence; a leaking feature is refused by construction)
def check_stamps(features: pl.DataFrame, cutoff: time | None = None) -> None:
    """Refuse the first feature (by name) with a stamp that breaks HAR-12, naming the feature and its first cell.

    `cutoff` is the time of day, UTC, at which a news feature's cut falls on a cell's date; it is needed only when
    some stamp is a Datetime. The message reads: feature 'edge' refused at cell (T003, 2000-01-05): stamp
    2000-01-06 is after the cell's date (and 2 more cells).
    """
    for name, stamp in stamp_columns(features).items():
        bad = too_late(name, stamp, features, cutoff)
        if bad.height:
            first = bad.row(0, named=True)
            more = f" (and {bad.height - 1} more cells)" if bad.height > 1 else ""
            raise StampRefused(
                f"feature {name!r} refused at cell ({first['ticker']}, {first['date']}): {first['reason']}{more}"
            )


def check_market(market: Market, cutoff: time | None = None) -> None:
    """Refuse a Market whose calendar, frames or stamps break docs/HARNESS.md, in that order."""
    check_calendar(market.calendar)
    check_prices(market.prices)
    check_universe(market.universe)
    check_stamps(market.features, cutoff)
    for name, frame in (("price", market.prices), ("universe", market.universe), ("feature", market.features)):
        check_on_calendar(name, frame, market.calendar)

