"""The aggregate numbers behind NR-F-03 to NR-F-08 (docs/FINDINGS.md): counts, shares and dates of the WIKI export.

Reads the yearly parquet in the data clone (the sample) and the unzipped export CSV (the feed past the sample); prints
tables and writes nothing. No price, no ticker and no row is printed: only counts, shares and dates (R-006).

    PYTHONPATH=. python scripts/probe/wiki_findings.py DATA_CLONE/wiki/prices EXPORT.csv
"""
import sys
from datetime import date
from pathlib import Path

import polars as pl

from neonrain.universe import calendar as nyse

END = date(2017, 12, 29)
GAP_DAYS = 180
JUMP = 4.0


def load_sample(folder: Path) -> pl.DataFrame:
    """The sample's yearly files as one frame sorted by ticker then date."""
    return pl.concat([pl.read_parquet(path) for path in sorted(folder.glob("[12]*.parquet"))]).sort("ticker", "date")


def leavers_by_year(sample: pl.DataFrame) -> pl.DataFrame:
    """Per year: tickers trading, tickers whose last row is that year (before END), tickers whose first row is that year."""
    spans = sample.group_by("ticker").agg(first=pl.col("date").min(), last=pl.col("date").max())
    rows = []
    for year in range(1998, 2018):
        trading = sample.filter(pl.col("date").dt.year() == year)["ticker"].n_unique()
        left = spans.filter((pl.col("last").dt.year() == year) & (pl.col("last") < END)).height
        rows.append((year, trading, left, round(100 * left / trading, 2), spans.filter(pl.col("first").dt.year() == year).height))
    return pl.DataFrame(rows, schema=["year", "trading", "left", "percent_left", "first_rows"], orient="row")


def jumps(sample: pl.DataFrame) -> pl.DataFrame:
    """Each row with the days since the ticker's previous row and the adjusted-close ratio to it."""
    prev = pl.col("date").shift(1).over("ticker")
    ratio = pl.col("adj_close") / pl.col("adj_close").shift(1).over("ticker")
    return sample.select("ticker", gap=(pl.col("date") - prev).dt.total_days(), ratio=ratio).drop_nulls("gap")


def reuse(sample: pl.DataFrame) -> None:
    """Print the gap and discontinuity counts (events and tickers) that make a ticker a candidate for reuse."""
    rows = jumps(sample)
    gaps = rows.filter(pl.col("gap") >= GAP_DAYS)
    across = gaps.filter((pl.col("ratio") >= 2) | (pl.col("ratio") <= 0.5))
    near = rows.filter(pl.col("gap") < GAP_DAYS)
    big = near.filter((pl.col("ratio") >= JUMP) | (pl.col("ratio") <= 1 / JUMP))
    print("gap >=", GAP_DAYS, "days: events", gaps.height, "tickers", gaps["ticker"].n_unique())
    print("  of which the adjusted close moved 2x or more across it: tickers", across["ticker"].n_unique())
    print("one-row jump of", JUMP, "x or more (gap under", GAP_DAYS, "days): events", big.height, "tickers", big["ticker"].n_unique())
    print("candidates (either):", pl.concat([gaps["ticker"], big["ticker"]]).n_unique(), "of", sample["ticker"].n_unique())


def delisting(sample: pl.DataFrame) -> None:
    """Print how the last row of a leaving ticker differs from rows in general (is a delisting marked at all)."""
    prev = pl.col("close").shift(1).over("ticker")
    rows = sample.with_columns(flat=pl.col("close") == prev, last=pl.col("date") == pl.col("date").max().over("ticker"))
    last = rows.filter(pl.col("last") & (pl.col("date") < END))
    for name, part in (("last rows of leavers", last), ("all rows", rows)):
        print(name, part.height, "zero volume %", round(100 * (part["volume"] == 0).mean(), 2), "flat close %", round(100 * part["flat"].mean(), 2),
              "close under 1 %", round(100 * (part["close"] < 1).mean(), 2), "dividend %", round(100 * (part["ex-dividend"] > 0).mean(), 2))
    print("columns:", sample.columns)


def calendar_gaps(sample: pl.DataFrame) -> None:
    """Print the WIKI dates that are no session, the rows on them, and the sessions with no prices."""
    sessions = {day for day in nyse.sessions(1998, 2017) if day <= END}
    dates = set(sample["date"].unique().to_list())
    stray = sample.filter(~pl.col("date").is_in(sorted(sessions)))
    print("sessions", len(sessions), "dates with prices", len(dates), "not sessions", len(dates - sessions), "rows on them", stray.height,
          "weekend dates", sum(day.weekday() > 4 for day in dates - sessions), "most rows on one", stray.group_by("date").len()["len"].max())
    print("sessions without prices:", len(sessions - dates), sorted(sessions - dates))


def decay(csv: Path) -> None:
    """Print, by month from 2016 on, the tickers trading, the dividend rows and the split rows of the export."""
    lazy = pl.scan_csv(csv, schema_overrides={"date": pl.Date, "ticker": pl.String}, try_parse_dates=True)
    month = pl.col("date").dt.strftime("%Y-%m").alias("month")
    table = lazy.filter(pl.col("date") >= date(2016, 1, 1)).group_by(month).agg(
        tickers=pl.col("ticker").n_unique(), rows=pl.len(), dividends=(pl.col("ex-dividend") > 0).sum(),
        splits=(pl.col("split_ratio") != 1).sum()).sort("month").collect()
    with pl.Config(tbl_rows=40):
        print(table)
    days = lazy.filter(pl.col("date") >= date(2017, 10, 25)).group_by("date").agg(
        rows=pl.len(), dividends=(pl.col("ex-dividend") > 0).sum()).sort("date").collect()
    with pl.Config(tbl_rows=100):
        print(days)


def main(argv: list[str]) -> int:
    """Print every table; 2 on misuse."""
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    sample = load_sample(Path(argv[0]))
    print("sample rows", sample.height, "tickers", sample["ticker"].n_unique(), "dates", sample["date"].n_unique())
    with pl.Config(tbl_rows=40):
        print(leavers_by_year(sample))
    reuse(sample)
    delisting(sample)
    calendar_gaps(sample)
    decay(Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
