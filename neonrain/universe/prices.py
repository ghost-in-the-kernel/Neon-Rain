"""The daily price frame from WIKI's yearly parquet (TODO 2.2): verified, mapped to the harness's layout, reported.

`load` reads the files only through `verified.read_verified` (the index against the manifest row, each year against
its index line, nothing read on a mismatch), then builds the harness's price frame (docs/HARNESS.md: `ticker`
String, `date` Date, `close` Float64, other columns allowed) from the export's columns:

| Frame column | The export's column | Why |
| --- | --- | --- |
| `ticker`, `date` | `ticker`, `date` | the keys |
| `open`, `high`, `low`, `close`, `volume` | `adj_open`, `adj_high`, `adj_low`, `adj_close`, `adj_volume` | split- and dividend-adjusted, so a return is a total return (the harness's `close`) |
| `raw_close`, `raw_volume` | `close`, `volume` | as traded, for the dollar volume of membership (a name's size on the day it traded) |
| `ex_dividend`, `split_ratio` | `ex-dividend`, `split_ratio` | the corporate actions, kept for the features |

The export's raw `open`, `high` and `low` are not kept. `for_membership` renames raw back to `close` and `volume`,
the columns `membership` reads.

**Rows the harness would refuse are never dropped silently** (NR-F-08). `check_market` refuses a price row whose date
is not on the calendar, so `load` leaves such a row out of the frame and hands it back in `Loaded.off_calendar`
(ticker, date); a session between the first and the last price date with no row for any ticker is handed back in
`Loaded.empty_sessions`. A ticker is never merged, split or dropped here (NR-F-05): a reused ticker, or one with
an unrecorded split, stays one ticker with the rows the export gives it. Pure apart from reading files.
"""
import io
from datetime import date
from pathlib import Path
from typing import NamedTuple

import polars as pl

from neonrain.universe import verified

DATASET = "wiki-prices"  # the manifest row whose hash is the index's
EXPORT: dict[str, pl.DataType | type[pl.DataType]] = {
    "ticker": pl.String, "date": pl.Date, "open": pl.Float64, "high": pl.Float64, "low": pl.Float64,
    "close": pl.Float64, "volume": pl.Float64, "ex-dividend": pl.Float64, "split_ratio": pl.Float64,
    "adj_open": pl.Float64, "adj_high": pl.Float64, "adj_low": pl.Float64, "adj_close": pl.Float64,
    "adj_volume": pl.Float64,
}
# Decision: TODO 2.2: the adjusted columns are the frame's open to volume; the raw close and volume ride beside them.
FRAME: dict[str, str] = {
    "ticker": "ticker", "date": "date",
    "open": "adj_open", "high": "adj_high", "low": "adj_low", "close": "adj_close", "volume": "adj_volume",
    "raw_close": "close", "raw_volume": "volume", "ex_dividend": "ex-dividend", "split_ratio": "split_ratio",
}


class Loaded(NamedTuple):
    """The price frame and what was left out of it: nothing is dropped without being here."""

    prices: pl.DataFrame  # ticker, date, open, high, low, close, volume, raw_close, raw_volume, ex_dividend, split_ratio
    off_calendar: pl.DataFrame  # ticker, date: rows on a date that is no session (NR-F-08), not in `prices`
    empty_sessions: list[date]  # sessions from the first to the last price date with no row for any ticker (NR-F-08)


def parse_year(year: str, data: bytes) -> pl.DataFrame:
    """One verified file as a frame; refuses columns or types that are not the export's, and a row outside its year."""
    frame = pl.read_parquet(io.BytesIO(data))
    if dict(frame.schema) != EXPORT:
        raise verified.Unverified(f"{year}.parquet has the columns {dict(frame.schema)}, expected {EXPORT}")
    stray = frame.filter(pl.col("date").dt.year().cast(pl.String) != year)
    if stray.height:
        raise verified.Unverified(f"{year}.parquet holds a row dated {stray['date'][0]}, outside {year}")
    return frame


def frame_of(export: pl.DataFrame) -> pl.DataFrame:
    """The harness's layout from export rows: FRAME's columns, sorted by ticker then date."""
    return export.select([pl.col(source).alias(name) for name, source in FRAME.items()]).sort("ticker", "date")


def load(folder: Path, manifest: str, sessions: list[date], years: list[int] | None = None) -> Loaded:
    """The price frame of `years` (all the index lists, if None) on the calendar `sessions`, and what was left out.

    Refuses, reading nothing, whatever `verified.read_verified` refuses. A row on a date not in `sessions` goes to
    `off_calendar`; a session between the first and last price date that has no row goes to `empty_sessions`.
    """
    keys = None if years is None else [str(year) for year in years]
    files = verified.read_verified(folder, manifest, DATASET, keys)
    frames = [parse_year(year, data) for year, data in sorted(files.items())]
    prices = frame_of(pl.concat(frames)) if frames else frame_of(pl.DataFrame(schema=EXPORT))
    on_calendar = prices["date"].is_in(sessions)
    seen = set(prices["date"].unique().to_list())
    first, last = (min(seen), max(seen)) if seen else (None, None)
    empty = [day for day in sessions if first is not None and first <= day <= last and day not in seen]
    off = prices.filter(~on_calendar).select("ticker", "date")
    return Loaded(prices.filter(on_calendar), off, empty)


def for_membership(prices: pl.DataFrame) -> pl.DataFrame:
    """The frame `membership` reads: ticker, date, and the raw close and volume under the names `close` and `volume`."""
    return prices.select("ticker", "date", close=pl.col("raw_close"), volume=pl.col("raw_volume"))
