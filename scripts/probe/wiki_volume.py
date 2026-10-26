"""Counts from the volume ratio family on the real sample (TODO 2.3); only counts are printed, no volume or ratio (R-006).

    PYTHONPATH=. python scripts/probe/wiki_volume.py <neon-rain-data clone>

Loads `<clone>/wiki/prices` as `wiki_prices.py` does, builds the volume ratio family on the calendar of 1998 to 2017,
runs the harness's stamp check on the frame, and prints for each lookback the cells with a value and the cells without,
and how many of those are a null because the prior mean is zero. Also counts the rows where the raw and the adjusted
volume differ (a split in force), the reason the adjusted volume is the one used.
"""
import sys
from pathlib import Path

import polars as pl

from neonrain.features import volume
from neonrain.harness import market
from neonrain.universe import calendar, prices

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    """Print the counts; 0 on success, 1 on a refusal, 2 on misuse."""
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    sessions = calendar.sessions(1998, 2017)
    try:
        loaded = prices.load(Path(argv[0]) / "wiki" / "prices", (ROOT / "data" / "MANIFEST.md").read_text(), sessions)
        frame = volume.volume_ratios(loaded.prices, sessions)
        market.check_stamps(frame)
    except Exception as refusal:  # noqa: BLE001 - a verification refusal, a layout fault or a stamp refusal
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    print(f"cells: {frame.height}; tickers: {frame['ticker'].n_unique()}; stamps pass the harness's check")
    own = loaded.prices
    differ = own.filter(pl.col("volume").is_not_null() & ((pl.col("volume") - pl.col("raw_volume")).abs() > 0.5)).height
    zero = own.filter(pl.col("volume") == 0).height
    unusable = own.filter(~volume.usable()).height
    print(f"rows: {own.height}; adjusted volume differs from raw {differ}; zero volume {zero}; unusable volume {unusable}")
    for lookback in volume.LOOKBACKS:
        column = volume.name(lookback)
        valued = frame[column].is_not_null().sum()
        infinite = frame.filter(pl.col(column).is_infinite()).height
        zeros = frame.filter(pl.col(column) == 0).height
        print(f"{column}: with a value {valued}; without {frame.height - valued}; infinite {infinite}; exactly zero {zeros}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
